import os
import sys
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends, Header, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
from supabase import create_client, Client

from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone import Pinecone, ServerlessSpec
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pickle
import pickle as pkl
import uuid
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import json as json_module
import requests
import io
from urllib.parse import urlencode
import jwt
import time
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from entity_extraction import extract_entities_for_document

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
PROCESSED_CHUNKS_DIR = Path(__file__).parent.parent / "data" / "processed_chunks"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
PINECONE_INDEX_NAME = "personal-database"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

def extract_metadata_from_text(text):
    """Extract metadata header from text if present"""
    metadata = {}
    content = text
    
    if text.startswith('=== METADATA ==='):
        try:
            end_metadata = text.index('=== END METADATA ===')
            metadata_json = text[16:end_metadata].strip()
            metadata = json.loads(metadata_json)
            content = text[end_metadata + 20:].strip()
        except (ValueError, json.JSONDecodeError):
            # If parsing fails, use original text
            pass
    
    return metadata, content

# OAuth2 scopes for different Google services
GOOGLE_SCOPES = {
    'calendar': ['https://www.googleapis.com/auth/calendar.readonly'],
    'gmail': ['https://www.googleapis.com/auth/gmail.readonly'],
    'google_drive': ['https://www.googleapis.com/auth/drive.readonly']
}
TOKEN_FILE = CREDENTIALS_DIR / "token.pickle"

# OAuth state storage (in production, use Redis or database)
oauth_states = {}

app = FastAPI(title="Personal Database API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]

class DocumentResponse(BaseModel):
    message: str
    document_count: int

class RelationshipQueryRequest(BaseModel):
    entity_id: Optional[str] = None
    topic: Optional[str] = None
    source: Optional[str] = None
    question: Optional[str] = None
    user_id: Optional[str] = None

class RelationshipQueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    filters_applied: dict

class ChatMessage(BaseModel):
    role: str
    content: str
    sources: Optional[List[dict]] = None

class SaveChatRequest(BaseModel):
    user_id: str
    session_id: str
    messages: List[ChatMessage]

class GetChatRequest(BaseModel):
    user_id: str
    session_id: str

class CreateUserDatabaseRequest(BaseModel):
    user_id: str
    apple_calendar_email: Optional[str] = None
    apple_calendar_password: Optional[str] = None

class UploadDocumentsRequest(BaseModel):
    user_id: str
    permissions: dict
    setup_step: Optional[int] = None
    apple_calendar_email: Optional[str] = None
    apple_calendar_password: Optional[str] = None

class AppleMusicRequest(BaseModel):
    user_id: str
    music_user_token: Optional[str] = None
    key_id: Optional[str] = None
    team_id: Optional[str] = None
    private_key: Optional[str] = None

class GoogleSearchHistoryRequest(BaseModel):
    user_id: str
    json_path: str

# Global variables for Pinecone and LLM
pinecone_index = None
embedding_model = None
reranker = None
llm = None
supabase: Optional[Client] = None

def initialize_services():
    """Initialize Pinecone, LLM, and Supabase"""
    global pinecone_index, embedding_model, reranker, llm, supabase
    
    if not os.getenv("PINECONE_API_KEY"):
        print("Warning: PINECONE_API_KEY not found")
        return
    
    try:
        # Initialize Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        # Check if index exists, create if it doesn't
        existing_indexes = [index.name for index in pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing_indexes:
            print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            # Wait for index to be ready
            import time
            while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                time.sleep(1)
            print(f"Pinecone index '{PINECONE_INDEX_NAME}' created successfully")
        
        pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        
        # Initialize embedding model
        embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # Initialize cross-encoder for reranking
        reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        print("Cross-encoder reranker initialized successfully")

        # Initialize OpenRouter LLM
        try:
            llm = ChatOpenAI(
                model="openrouter/free",
                temperature=0.2,
                openai_api_key=os.getenv("OPEN_ROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1"
            )
            print("OpenRouter LLM initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize OpenRouter LLM: {e}")
            print("Make sure OPEN_ROUTER_API_KEY is set in .env file")
        
        print("Services initialized successfully")
    except Exception as e:
        print(f"Error initializing services: {e}")
    
    # Initialize Supabase
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ADMIN_KEY")
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            print("Supabase initialized successfully")
        else:
            print("Warning: SUPABASE_URL or SUPABASE_ADMIN_KEY not found")
    except Exception as e:
        print(f"Error initializing Supabase: {e}")

# Initialize on startup
@app.on_event("startup")
def startup_event():
    initialize_services()

@app.get("/")
async def root():
    return {"message": "Personal Database API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "pinecone_connected": pinecone_index is not None,
        "embedding_model_loaded": embedding_model is not None,
        "openrouter_loaded": llm is not None,
        "supabase_connected": supabase is not None
    }

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the document database with a question"""
    if not embedding_model:
        raise HTTPException(
            status_code=503,
            detail="Services not initialized. Please check configuration."
        )

    # Get user-specific Pinecone index if user_id provided
    index_to_use = pinecone_index
    if request.user_id and supabase:
        try:
            user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
            if user_settings.data:
                pinecone_index_name = user_settings.data[0].get("pinecone_index")
                if pinecone_index_name:
                    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                    index_to_use = pc.Index(pinecone_index_name)
        except Exception as e:
            print(f"Error getting user index: {e}")

    if not index_to_use:
        raise HTTPException(
            status_code=503,
            detail="Vector database not available. Please complete setup first."
        )

    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(request.question).tolist()

        # Search Pinecone with higher top_k for better retrieval
        results = index_to_use.query(
            vector=query_embedding,
            top_k=10,
            include_metadata=True
        )

        # Filter by score (relevance threshold) - lowered to 0.5 to avoid filtering too aggressively
        filtered_matches = [match for match in results['matches'] if match.get('score', 0) >= 0.5]

        # If no matches pass the filter, use the top matches anyway
        if not filtered_matches:
            filtered_matches = results['matches'][:5]

        # Rerank using cross-encoder if available
        if reranker and len(filtered_matches) > 1:
            pairs = [[request.question, match.get('metadata', {}).get('text', '')] for match in filtered_matches]
            scores = reranker.predict(pairs)
            for match, score in zip(filtered_matches, scores):
                match['rerank_score'] = score
            filtered_matches.sort(key=lambda x: x['rerank_score'], reverse=True)

        # Take top 5 results after filtering/reranking
        top_matches = filtered_matches[:5]

        # Extract sources with enhanced metadata
        sources = []
        context_parts = []
        for match in top_matches:
            metadata = match.get('metadata', {})
            content = metadata.get('text', '')
            if content:
                source_info = {
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": {
                        "filename": metadata.get('filename', 'Unknown'),
                        "source_type": metadata.get('source_type', 'document'),
                        "date": metadata.get('date', 'Unknown'),
                        "relevance_score": float(match.get('score', 0)),
                        "rerank_score": float(match.get('rerank_score', 0)) if match.get('rerank_score') is not None else None
                    }
                }
                sources.append(source_info)
                context_parts.append(content)

        # Context window management - truncate if too long
        max_context_length = 4000
        context = "\n\n".join(context_parts)
        if len(context) > max_context_length:
            # Truncate by keeping most relevant chunks first
            truncated_context = []
            current_length = 0
            for part in context_parts:
                if current_length + len(part) <= max_context_length:
                    truncated_context.append(part)
                    current_length += len(part)
                else:
                    break
            context = "\n\n".join(truncated_context)

        # Generate answer using LLM with improved prompt
        if llm and context_parts:
            prompt = f"""You are a precise, factual assistant that answers questions based ONLY on the provided context.

IMPORTANT: All information in the context below is from the user's personal perspective. When interpreting events, actions, communications, or any data, assume it reflects the user's own experiences, activities, and information. For example:
- "sent an email" means the user sent it
- "meeting with X" means the user attended the meeting
- "purchased Y" means the user made the purchase
- Any references to "I", "my", or personal activities refer to the user

INSTRUCTIONS:
- Answer the question using the given context
- Interpret all context as the user's personal information and experiences
- If the answer is not in the context, state "I don't have enough information to answer this"
- Be specific and cite relevant details
- Do not make up or infer information beyond what's provided
- Keep answers concise and well-structured

CONTEXT (from {len(context_parts)} sources):
{context}

QUESTION: {request.question}

ANSWER:"""

            answer = llm.invoke(prompt).content
        else:
            if not llm:
                print(f"[QUERY] LLM not initialized")
            if not context_parts:
                print(f"[QUERY] No context parts found. Matches: {len(results.get('matches', []))}, Filtered: {len(filtered_matches)}")
            answer = "No LLM configured or no relevant documents found. Here are the relevant document excerpts:\n\n" + "\n\n".join(context_parts)

        return QueryResponse(answer=answer, sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query-relationships", response_model=RelationshipQueryResponse)
async def query_by_relationships(request: RelationshipQueryRequest):
    """Query documents by relationships (entity, topic, source) with optional semantic search"""
    if not embedding_model:
        raise HTTPException(
            status_code=503,
            detail="Services not initialized. Please check configuration."
        )
    
    # Get user-specific Pinecone index if user_id provided
    index_to_use = pinecone_index
    if request.user_id and supabase:
        try:
            user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
            if user_settings.data:
                pinecone_index_name = user_settings.data[0].get("pinecone_index")
                if pinecone_index_name:
                    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                    index_to_use = pc.Index(pinecone_index_name)
        except Exception as e:
            print(f"Error getting user index: {e}")
    
    if not index_to_use:
        raise HTTPException(
            status_code=503,
            detail="Vector database not available. Please complete setup first."
        )
    
    try:
        # Build metadata filter
        filter_dict = {}
        filters_applied = {}
        
        if request.entity_id:
            filter_dict['entity_ids'] = {'$in': [request.entity_id]}
            filters_applied['entity_id'] = request.entity_id
        
        if request.topic:
            filter_dict['topics'] = {'$in': [request.topic]}
            filters_applied['topic'] = request.topic
        
        if request.source:
            filter_dict['source'] = request.source
            filters_applied['source'] = request.source
        
        # If no filters provided, return error
        if not filter_dict and not request.question:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least one filter (entity_id, topic, source) or a question"
            )
        
        # Search with or without semantic query
        if request.question:
            query_embedding = embedding_model.encode(request.question).tolist()
            results = index_to_use.query(
                vector=query_embedding,
                top_k=10,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
        else:
            # Metadata-only search (no vector)
            results = index_to_use.query(
                vector=[0] * 384,  # Dummy vector for metadata-only search
                top_k=20,
                include_metadata=True,
                filter=filter_dict
            )
        
        # Extract sources
        sources = []
        context_parts = []
        for match in results['matches']:
            metadata = match.get('metadata', {})
            content = metadata.get('text', '')
            if content:
                sources.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": metadata
                })
                context_parts.append(content)
        
        # Generate answer using LLM if question provided
        if request.question and llm and context_parts:
            context = "\n\n".join(context_parts)
            prompt = f"""You are a helpful assistant that answers questions based on the provided context.

IMPORTANT: All information in the context below is from the user's personal perspective. When interpreting events, actions, communications, or any data, assume it reflects the user's own experiences, activities, and information. For example:
- "sent an email" means the user sent it
- "meeting with X" means the user attended the meeting
- "purchased Y" means the user made the purchase
- Any references to "I", "my", or personal activities refer to the user

Use the following pieces of context to answer the question at the end. If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {request.question}

Answer:"""
            
            answer = llm.invoke(prompt).content
        elif context_parts:
            answer = f"Found {len(sources)} related documents based on filters: {filters_applied}"
        else:
            answer = f"No documents found matching filters: {filters_applied}"
        
        return RelationshipQueryResponse(
            answer=answer,
            sources=sources,
            filters_applied=filters_applied
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=DocumentResponse)
async def ingest_document(file: UploadFile = File(...)):
    """Upload and ingest a document into the database"""
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="PINECONE_API_KEY not found in environment variables"
        )
    
    try:
        # Save uploaded file
        file_path = RAW_DOCS_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load and process the document
        if file.filename.endswith('.pdf'):
            loader = PyPDFLoader(str(file_path))
        else:
            loader = TextLoader(str(file_path))
        
        documents = loader.load()
        
        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        
        # Create embeddings and upsert to Pinecone
        if not embedding_model:
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not pinecone_index:
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            existing_indexes = [index.name for index in pc.list_indexes()]
            if PINECONE_INDEX_NAME not in existing_indexes:
                pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                import time
                while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                    time.sleep(1)
            pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        
        # Create embeddings and upsert
        vectors = []
        for chunk in chunks:
            text = chunk.page_content
            
            # Extract metadata from text if present
            extracted_metadata, clean_text = extract_metadata_from_text(text)
            
            # Extract entities for relationship tracking
            entity_data = extract_entities_for_document(clean_text, extracted_metadata)
            
            # Build metadata dict
            metadata = {
                'text': clean_text,
                'source': str(file.filename),
                'chunk_source': chunk.metadata.get('source', '')
            }
            
            # Add extracted metadata if available
            if extracted_metadata:
                metadata.update(extracted_metadata)
            
            # Add entity extraction data
            if entity_data.get('entity_ids'):
                metadata['entity_ids'] = entity_data['entity_ids']
            if entity_data.get('topics'):
                metadata['topics'] = entity_data['topics']
            if entity_data.get('time_context'):
                metadata['time_context'] = entity_data['time_context']
            
            embedding = embedding_model.encode(clean_text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            pinecone_index.upsert(vectors=batch)
        
        # Save chunks to disk
        chunks_path = PROCESSED_CHUNKS_DIR / f"{file.filename}_chunks.pkl"
        with open(chunks_path, 'wb') as f:
            pickle.dump(chunks, f)
        
        return DocumentResponse(
            message=f"Successfully ingested {file.filename}",
            document_count=len(documents)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all documents in the raw_docs directory"""
    try:
        documents = []
        for file_path in RAW_DOCS_DIR.rglob("*"):
            if file_path.is_file():
                documents.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "path": str(file_path)
                })
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_google_credentials():
    """Get or refresh OAuth2 credentials"""
    creds = None
    
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pkl.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_file = CREDENTIALS_DIR / "client_secret.json"
            if not client_secrets_file.exists():
                raise FileNotFoundError(
                    "OAuth credentials not found. Please download client_secret.json from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_file), GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pkl.dump(creds, token)
    
    return creds

def fetch_and_ingest_google_docs():
    """Fetch Google Docs and ingest them into the database"""
    try:
        creds = get_google_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        # List Google Docs
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.document'",
            fields="files(id, name, modifiedTime)",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        if not files:
            return {"message": "No Google Docs found", "count": 0}
        
        # Download and save each document
        downloaded_files = []
        for doc in files:
            try:
                request = drive_service.files().export_media(
                    fileId=doc['id'],
                    mimeType='text/plain'
                )
                
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8')
                
                safe_name = "".join(c for c in doc['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                output_path = RAW_DOCS_DIR / f"{safe_name}.txt"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                downloaded_files.append(output_path)
            except Exception as e:
                print(f"Error downloading {doc['name']}: {e}")
        
        # Ingest all downloaded files into Pinecone
        global pinecone_index, embedding_model
        
        if not embedding_model:
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not pinecone_index:
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            existing_indexes = [index.name for index in pc.list_indexes()]
            if PINECONE_INDEX_NAME not in existing_indexes:
                pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                import time
                while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                    time.sleep(1)
            pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        
        all_chunks = []
        for file_path in downloaded_files:
            loader = TextLoader(str(file_path))
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)
            all_chunks.extend(chunks)
        
        # Create embeddings and upsert to Pinecone
        vectors = []
        for chunk in all_chunks:
            text = chunk.page_content
            
            # Extract metadata from text if present
            extracted_metadata, clean_text = extract_metadata_from_text(text)
            
            # Extract entities for relationship tracking
            entity_data = extract_entities_for_document(clean_text, extracted_metadata)
            
            # Build metadata dict
            metadata = {
                'text': clean_text,
                'source': chunk.metadata.get('source', ''),
                'type': 'google_doc'
            }
            
            # Add extracted metadata if available
            if extracted_metadata:
                metadata.update(extracted_metadata)
            
            # Add entity extraction data
            if entity_data.get('entity_ids'):
                metadata['entity_ids'] = entity_data['entity_ids']
            if entity_data.get('topics'):
                metadata['topics'] = entity_data['topics']
            if entity_data.get('time_context'):
                metadata['time_context'] = entity_data['time_context']
            
            embedding = embedding_model.encode(clean_text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            pinecone_index.upsert(vectors=batch)
        
        return {"message": f"Successfully ingested {len(downloaded_files)} Google Docs", "count": len(downloaded_files)}
    
    except Exception as e:
        raise Exception(f"Error fetching Google Docs: {str(e)}")

@app.post("/ingest-google-docs", response_model=DocumentResponse)
async def ingest_google_docs(background_tasks: BackgroundTasks):
    """Fetch and ingest all Google Docs from authenticated account"""
    try:
        # Check if credentials exist
        if not (CREDENTIALS_DIR / "client_secret.json").exists():
            raise HTTPException(
                status_code=400,
                detail="Google OAuth credentials not found. Please add client_secret.json to the credentials directory."
            )
        
        # Run ingestion in background
        result = await asyncio.get_event_loop().run_in_executor(None, fetch_and_ingest_google_docs)
        
        return DocumentResponse(
            message=result["message"],
            document_count=result["count"]
        )
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat-history/save")
async def save_chat_history(request: SaveChatRequest):
    """Save chat history to Supabase"""
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        # Delete existing chat history for this user and session
        supabase.table("chat_history").delete().eq("user_id", request.user_id).eq("session_id", request.session_id).execute()

        # Insert new chat messages with session_id
        for message in request.messages:
            supabase.table("chat_history").insert({
                "user_id": request.user_id,
                "session_id": request.session_id,
                "role": message.role,
                "content": message.content,
                "sources": message.sources
            }).execute()

        return {"message": "Chat history saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat-history/load")
async def load_chat_history(request: GetChatRequest):
    """Load chat history from Supabase"""
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        response = supabase.table("chat_history").select("*").eq("user_id", request.user_id).eq("session_id", request.session_id).order("created_at").execute()

        messages = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "sources": msg.get("sources")
            }
            for msg in response.data
        ]

        return {"messages": messages}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{user_id}")
async def get_sessions(user_id: str):
    """Get all sessions for a user with message counts"""
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        # Use SQL aggregation to get sessions with message counts
        response = supabase.rpc("get_user_sessions", {"user_uuid": user_id}).execute()
        
        if response.data:
            return {"sessions": response.data}
        else:
            # Fallback: fetch all messages and group manually if RPC doesn't exist
            all_messages = supabase.table("chat_history").select("session_id, created_at, content").eq("user_id", user_id).not_.is_("session_id", "null").order("created_at", ascending=False).execute()
            
            session_map = {}
            for msg in all_messages.data:
                session_id = msg.get("session_id")
                if not session_id:
                    continue
                
                if session_id not in session_map:
                    session_map[session_id] = {
                        "session_id": session_id,
                        "created_at": msg.get("created_at"),
                        "message_count": 0,
                        "last_message": msg.get("content", "")[:100] if msg.get("content") else ""
                    }
                session_map[session_id]["message_count"] += 1
            
            sessions = sorted(session_map.values(), key=lambda x: x.get("created_at", ""), reverse=True)
            return {"sessions": sessions}
    
    except Exception as e:
        # Fallback to manual grouping if RPC fails
        try:
            all_messages = supabase.table("chat_history").select("session_id, created_at, content").eq("user_id", user_id).not_.is_("session_id", "null").order("created_at", ascending=False).execute()
            
            session_map = {}
            for msg in all_messages.data:
                session_id = msg.get("session_id")
                if not session_id:
                    continue
                
                if session_id not in session_map:
                    session_map[session_id] = {
                        "session_id": session_id,
                        "created_at": msg.get("created_at"),
                        "message_count": 0,
                        "last_message": msg.get("content", "")[:100] if msg.get("content") else ""
                    }
                session_map[session_id]["message_count"] += 1
            
            sessions = sorted(session_map.values(), key=lambda x: x.get("created_at", ""), reverse=True)
            return {"sessions": sessions}
        except Exception as fallback_error:
            raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")

@app.post("/create-user-database")
async def create_user_database(request: CreateUserDatabaseRequest):
    """Create a user-specific vector database in Pinecone"""
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="PINECONE_API_KEY not found"
        )
    
    try:
        # Check if user already has a database created
        if supabase:
            existing = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
            if existing.data and existing.data[0].get("setup_step", 1) >= 2:
                raise HTTPException(
                    status_code=400,
                    detail="Database already created for this user"
                )
        
        # Use shared Pinecone API key from environment
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        # Create user-specific index name
        index_name = f"personal-db-{request.user_id[:8]}"
        
        # Check if index already exists
        existing_indexes = [index.name for index in pc.list_indexes()]
        if index_name not in existing_indexes:
            pc.create_index(
                name=index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        # Save user settings to Supabase with setup step
        if supabase:
            # Insert new settings
            supabase.table("user_settings").insert({
                "user_id": request.user_id,
                "pinecone_index": index_name,
                "setup_step": 2,
                "uploaded_data_sources": {}  # Track which data sources have been uploaded
            }).execute()
        
        return {"message": "Database created successfully", "index_name": index_name}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user-settings/{user_id}")
async def get_user_settings(user_id: str):
    """Get user settings including setup progress"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")
    
    try:
        user_settings = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        
        if not user_settings.data:
            return {"setup_step": 1, "permissions": {}, "pinecone_index": None}
        
        settings = user_settings.data[0]
        return {
            "setup_step": settings.get("setup_step", 1),
            "permissions": settings.get("permissions", {}),
            "pinecone_index": settings.get("pinecone_index")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-permissions")
async def save_permissions(request: UploadDocumentsRequest):
    """Save user permissions without uploading documents"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")

    try:
        update_data = {
            "permissions": request.permissions,
        }

        # Only update setup_step if provided
        if request.setup_step is not None:
            update_data["setup_step"] = request.setup_step

        supabase.table("user_settings").update(update_data).eq("user_id", request.user_id).execute()

        return {"message": "Permissions saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_calendar_data(user_id: str, creds):
    """Fetch calendar data using the fetch_calendar.py script"""
    try:
        print(f"[CALENDAR FETCH] Starting calendar data fetch for user {user_id}")
        
        # Import and use the fetch_calendar script
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from fetch_calendar import fetch_google_calendar_events
        
        # Fetch calendar events using the script with provided credentials
        events_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: fetch_google_calendar_events(credentials=creds)
        )
        
        print(f"[CALENDAR FETCH] Total events fetched: {len(events_data)}")
        return events_data
    except Exception as e:
        print(f"[CALENDAR FETCH] Fatal error in fetch_calendar_data: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching calendar data: {str(e)}")

async def fetch_gmail_data(user_id: str, creds):
    """Fetch Gmail data using the fetch_emails.py script"""
    try:
        print(f"[GMAIL FETCH] Starting Gmail data fetch for user {user_id}")
        
        # Import and use the fetch_emails script
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from fetch_emails import fetch_gmail_emails
        
        # Fetch emails using the script with provided credentials
        emails_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: fetch_gmail_emails(max_results=100, credentials=creds)
        )
        
        print(f"[GMAIL FETCH] Total emails fetched: {len(emails_data)}")
        return emails_data
    except Exception as e:
        print(f"[GMAIL FETCH] Fatal error in fetch_gmail_data: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Gmail data: {str(e)}")

async def fetch_google_drive_data(user_id: str, creds):
    """Fetch Google Drive files using the fetch_drive_files.py script"""
    try:
        print(f"[DRIVE FETCH] Starting Google Drive fetch for user {user_id}")
        
        # Import and use the fetch_drive_files script
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from fetch_drive_files import fetch_drive_files
        
        # Fetch drive files using the script with provided credentials
        drive_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: fetch_drive_files(credentials=creds)
        )
        
        print(f"[DRIVE FETCH] Total files fetched: {len(drive_data)}")
        return drive_data
    except Exception as e:
        print(f"[DRIVE FETCH] Fatal error in fetch_google_drive_data: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Google Drive data: {str(e)}")

async def process_and_ingest_data(user_id: str, service: str, data, pinecone_index_name: str):
    """Process fetched data and ingest into Pinecone"""
    print(f"[INGEST] Starting process_and_ingest_data for user {user_id}, service {service}")
    print(f"[INGEST] Data items received: {len(data)}")
    global pinecone_index, embedding_model

    if not embedding_model:
        print(f"[INGEST] Initializing embedding model...")
        embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # Get user's Pinecone index
    print(f"[INGEST] Connecting to Pinecone index: {pinecone_index_name}")
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_to_use = pc.Index(pinecone_index_name)

    vectors = []

    if service == 'google_calendar':
        print(f"[INGEST] Processing {len(data)} calendar events")
        for i, item in enumerate(data):
            summary = item.get('summary', 'No Title')
            start = item.get('start', {})
            end = item.get('end', {})
            location = item.get('location', '')
            description = item.get('description', '')

            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {item['calendar']}\n"
            text += f"Start: {start.get('dateTime', start.get('date', 'Unknown'))}\n"
            text += f"End: {end.get('dateTime', end.get('date', 'Unknown'))}\n"
            if location:
                text += f"Location: {location}\n"
            if description:
                text += f"Description: {description}\n"

            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_calendar',
                    'type': 'calendar_event',
                    'calendar': item['calendar'],
                    'event_title': summary
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} calendar events")
    
    elif service == 'gmail':
        print(f"[INGEST] Processing {len(data)} Gmail messages")
        for i, message in enumerate(data):
            payload = message.get('payload', {})
            headers = payload.get('headers', [])

            subject = ''
            sender = ''
            date = ''
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
                elif header['name'] == 'Date':
                    date = header['value']

            # Get body
            body = ''
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            import base64
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
            elif 'body' in payload and 'data' in payload['body']:
                import base64
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

            text = f"Email Subject: {subject}\n"
            text += f"From: {sender}\n"
            text += f"Date: {date}\n"
            text += f"\n{body}"

            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'gmail',
                    'type': 'email',
                    'subject': subject,
                    'sender': sender
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} Gmail messages")

    elif service == 'google_drive':
        print(f"[INGEST] Processing {len(data)} Google Drive files")
        for i, file in enumerate(data):
            content = file['content']
            # Truncate content if too long
            if isinstance(content, str) and len(content) > 2000:
                content = content[:2000] + "... (truncated)"
            
            # Truncate title if too long
            title = file['name']
            if len(title) > 100:
                title = title[:100] + "..."
            
            text = f"File: {title}\n"
            text += f"Type: {file['mimeType']}\n"
            text += f"\n{content}"

            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_drive',
                    'type': 'file',
                    'title': title,
                    'mime_type': file['mimeType'],
                    'modified_date': file.get('modifiedTime', '')[:50] if file.get('modifiedTime') else ''
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} Drive files")
    
    elif service == 'apple_notes':
        print(f"[INGEST] Processing {len(data)} Apple Notes")
        for i, note in enumerate(data):
            name = note.get('name', 'Untitled')
            body = note.get('body', '')
            created = note.get('created', '')
            modified = note.get('modified', '')
            
            # Truncate body if too long
            if len(body) > 3000:
                body = body[:3000] + "... (truncated)"
            
            text = f"Note: {name}\n"
            if created:
                text += f"Created: {created}\n"
            if modified:
                text += f"Modified: {modified}\n"
            text += f"\n{body}"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_notes',
                    'type': 'note',
                    'note_name': name,
                    'created_date': created[:50] if created else '',
                    'modified_date': modified[:50] if modified else ''
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} notes")
    
    elif service == 'apple_calendar':
        print(f"[INGEST] Processing {len(data)} Apple Calendar events")
        for i, event in enumerate(data):
            calendar = event.get('calendar', 'Unknown')
            summary = event.get('summary', 'No Title')
            location = event.get('location', '')
            notes = event.get('notes', '')
            start_date = event.get('start_date', '')
            end_date = event.get('end_date', '')
            
            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {calendar}\n"
            text += f"Start: {start_date}\n"
            text += f"End: {end_date}\n"
            if location:
                text += f"Location: {location}\n"
            if notes:
                text += f"Notes: {notes}\n"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_calendar',
                    'type': 'calendar_event',
                    'calendar': calendar,
                    'event_title': summary,
                    'start_date': start_date[:50] if start_date else '',
                    'end_date': end_date[:50] if end_date else ''
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} calendar events")
    
    elif service == 'apple_music':
        print(f"[INGEST] Processing Apple Music data")
        # Process songs
        songs = data.get('results', {}).get('songs', {}).get('data', [])
        for i, song in enumerate(songs):
            attributes = song.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            artist = attributes.get('artistName', 'Unknown')
            album = attributes.get('albumName', 'Unknown')
            genre = attributes.get('genreNames', [])
            duration = attributes.get('durationInMillis', 0) / 1000
            
            text = f"Song: {name}\n"
            text += f"Artist: {artist}\n"
            text += f"Album: {album}\n"
            text += f"Duration: {duration:.1f} seconds\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'song',
                    'song_name': name,
                    'artist': artist,
                    'album': album
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(songs)} songs")
        
        # Process albums
        albums = data.get('results', {}).get('albums', {}).get('data', [])
        for i, album in enumerate(albums):
            attributes = album.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            artist = attributes.get('artistName', 'Unknown')
            genre = attributes.get('genreNames', [])
            release_date = attributes.get('releaseDate', 'Unknown')
            
            text = f"Album: {name}\n"
            text += f"Artist: {artist}\n"
            text += f"Release Date: {release_date}\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'album',
                    'album_name': name,
                    'artist': artist
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(albums)} albums")
        
        # Process artists
        artists = data.get('results', {}).get('artists', {}).get('data', [])
        for i, artist_data in enumerate(artists):
            attributes = artist_data.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            genre = attributes.get('genreNames', [])
            
            text = f"Artist: {name}\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'artist',
                    'artist_name': name
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(artists)} artists")
    
    # Upsert one at a time to avoid batch size issues
    print(f"[INGEST] Upserting {len(vectors)} vectors to Pinecone one at a time")
    success_count = 0
    for i, vector in enumerate(vectors):
        print(f"[INGEST] Upserting vector {i+1}/{len(vectors)}")
        try:
            index_to_use.upsert(vectors=[vector])
            success_count += 1
        except Exception as e:
            print(f"[INGEST] Error upserting vector {i+1}: {e}")
            continue
    
    print(f"[INGEST] Successfully upserted {success_count}/{len(vectors)} vectors")
    return success_count

@app.post("/fetch-apple-notes")
async def fetch_apple_notes():
    """Fetch Apple Notes using AppleScript (macOS only)"""
    try:
        import subprocess
        import json
        
        # Use a JSON-based approach to avoid delimiter issues
        # We'll export each note separately and build JSON in Python
        applescript_count = '''
        tell application "Notes"
            set allNotes to every note
            return count of allNotes
        end tell
        '''
        
        count_result = subprocess.run(
            ['osascript', '-e', applescript_count],
            capture_output=True,
            text=True,
            check=True
        )
        
        note_count = int(count_result.stdout.strip())
        print(f"Found {note_count} notes")
        
        # Limit to 50 notes for performance
        note_count = min(note_count, 50)
        
        notes_data = []
        for i in range(1, note_count + 1):
            # Get note by index (1-based in AppleScript)
            applescript = f'''
            tell application "Notes"
                set allNotes to every note
                set currentNote to item {i} of allNotes
                set noteName to name of currentNote
                set noteBody to body of currentNote
                set noteCreation to creation date of currentNote as string
                set noteModification to modification date of currentNote as string
                
                return noteName & "\\n---SEPARATOR---\\n" & noteBody & "\\n---SEPARATOR---\\n" & noteCreation & "\\n---SEPARATOR---\\n" & noteModification
            end tell
            '''
            
            try:
                result = subprocess.run(
                    ['osascript', '-e', applescript],
                    capture_output=True,
                    text=True,
                    check=True
                )
                output = result.stdout.strip()
                parts = output.split('---SEPARATOR---')
                
                if len(parts) >= 4:
                    name = parts[0].strip()
                    body = parts[1].strip()
                    created = parts[2].strip()
                    modified = parts[3].strip()
                    
                    # Skip empty names
                    if name:
                        notes_data.append({
                            'name': name,
                            'body': body,
                            'created': created,
                            'modified': modified
                        })
                        print(f"Exported note {i}/{note_count}: {name[:30]}...")
            except Exception as e:
                print(f"Error exporting note {i}: {e}")
                continue
        
        return {
            "message": f"Successfully fetched {len(notes_data)} Apple Notes",
            "notes": notes_data
        }
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error running AppleScript: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fetch-apple-calendar")
async def fetch_apple_calendar(request: Optional[UploadDocumentsRequest] = None):
    """Fetch Apple Calendar events using CalDAV (preferred) or AppleScript (fallback)"""
    try:
        # Try CalDAV first if credentials are provided
        if request and hasattr(request, 'apple_calendar_email') and hasattr(request, 'apple_calendar_password'):
            try:
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).parent.parent / "scripts"))
                
                # Import the CalDAV-based fetch function
                from fetch_apple_calendar import connect_to_icloud, list_calendars, get_events
                
                email = request.apple_calendar_email
                app_password = request.apple_calendar_password
                
                print(f"[APPLE CALENDAR] Using CalDAV to fetch events for {email}")
                
                # Connect to iCloud
                principal = connect_to_icloud(email, app_password)
                if not principal:
                    raise Exception("Failed to connect to iCloud via CalDAV")
                
                # List calendars
                calendar_names, calendars = list_calendars(principal)
                if not calendars:
                    return {"events": []}
                
                # Get events from last 30 days
                from datetime import datetime, timedelta
                start_date = datetime.now() - timedelta(days=30)
                end_date = datetime.now()
                
                all_events = []
                for calendar_name, calendar in zip(calendar_names, calendars):
                    events = get_events(calendar, start_date, end_date)
                    for event in events:
                        all_events.append({
                            'summary': event.get('summary', 'No Title'),
                            'location': event.get('location', ''),
                            'notes': event.get('notes', ''),
                            'start_date': event.get('start_date', ''),
                            'end_date': event.get('end_date', ''),
                            'calendar': calendar_name
                        })
                
                print(f"[APPLE CALENDAR] Fetched {len(all_events)} events via CalDAV")
                return {"events": all_events}
                
            except Exception as e:
                print(f"[APPLE CALENDAR] CalDAV failed, falling back to AppleScript: {e}")
        
        # Fallback to AppleScript (macOS only)
        import subprocess
        from datetime import datetime, timedelta
        
        print(f"[APPLE CALENDAR] Using AppleScript fallback")
        
        # List calendars
        applescript_list = '''
        tell application "Calendar"
            set allCalendars to every calendar
            set calendarNames to {}
            
            repeat with currentCalendar in allCalendars
                set end of calendarNames to name of currentCalendar
            end repeat
            
            return calendarNames
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', applescript_list],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        calendar_names = [name.strip().strip('"') for name in result.stdout.split(',')]
        print(f"Found {len(calendar_names)} calendars")
        
        # Get events from last 30 days
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        all_events = []
        print(f"Processing {len(calendar_names)} calendars from {start_str} to {end_str}")
        
        for idx, calendar_name in enumerate(calendar_names):
            print(f"[{idx+1}/{len(calendar_names)}] Processing calendar: {calendar_name}")
            applescript = f'''
            tell application "Calendar"
                set targetCalendar to calendar "{calendar_name}"
                set allEvents to every event of targetCalendar
                
                set eventList to {{}}
                
                repeat with currentEvent in allEvents
                    set eventStart to start date of currentEvent
                    set eventEnd to end date of currentEvent
                    
                    -- Check if event is within date range
                    if (eventStart ≥ date "{start_str}") and (eventStart ≤ date "{end_str}") then
                        set eventSummary to summary of currentEvent
                        set eventLocation to location of currentEvent
                        set eventNotes to notes of currentEvent
                        set eventStartDate to start date of currentEvent as string
                        set eventEndDate to end date of currentEvent as string
                        
                        set eventRecord to eventSummary & "|||" & eventLocation & "|||" & eventNotes & "|||" & eventStartDate & "|||" & eventEndDate
                        set end of eventList to eventRecord
                    end if
                end repeat
                
                return eventList as string
            end tell
            '''
            
            try:
                print(f"[{idx+1}/{len(calendar_names)}] Executing AppleScript for {calendar_name}...")
                result = subprocess.run(
                    ['osascript', '-e', applescript],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30  # Add timeout to prevent hanging
                )
                print(f"[{idx+1}/{len(calendar_names)}] AppleScript completed for {calendar_name}")
                
                output = result.stdout.strip()
                print(f"[{idx+1}/{len(calendar_names)}] Output length: {len(output)} characters")
                
                if output:
                    event_strings = output.split('|||')
                    print(f"[{idx+1}/{len(calendar_names)}] Found {len(event_strings) // 5} events in {calendar_name}")
                    # Each event has 5 parts: summary, location, notes, start_date, end_date
                    for i in range(0, len(event_strings), 5):
                        if i + 4 < len(event_strings):
                            all_events.append({
                                'calendar': calendar_name,
                                'summary': event_strings[i],
                                'location': event_strings[i + 1],
                                'notes': event_strings[i + 2],
                                'start_date': event_strings[i + 3],
                                'end_date': event_strings[i + 4]
                            })
                    print(f"[{idx+1}/{len(calendar_names)}] Fetched {len(event_strings) // 5} events from {calendar_name}")
                else:
                    print(f"[{idx+1}/{len(calendar_names)}] No events found in {calendar_name}")
            except subprocess.TimeoutExpired:
                print(f"[{idx+1}/{len(calendar_names)}] TIMEOUT fetching events from {calendar_name} (30s)")
                continue
            except Exception as e:
                print(f"[{idx+1}/{len(calendar_names)}] ERROR fetching events from {calendar_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Total events fetched across all calendars: {len(all_events)}")
        
        return {
            "message": f"Successfully fetched {len(all_events)} Apple Calendar events",
            "events": all_events
        }
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error running AppleScript: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-apple-notes")
async def ingest_apple_notes(request: CreateUserDatabaseRequest):
    """Fetch and ingest Apple Notes into the database"""
    try:
        print(f"[APPLE NOTES INGEST] Starting ingestion for user {request.user_id}")
        
        # Get user's Pinecone index
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[APPLE NOTES INGEST] Using Pinecone index: {pinecone_index_name}")
        
        # Fetch notes
        print(f"[APPLE NOTES INGEST] Fetching notes...")
        notes_response = await fetch_apple_notes()
        notes_data = notes_response["notes"]
        print(f"[APPLE NOTES INGEST] Fetched {len(notes_data)} notes")
        
        # Process and ingest
        global embedding_model
        if not embedding_model:
            print(f"[APPLE NOTES INGEST] Initializing embedding model...")
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not os.getenv("PINECONE_API_KEY"):
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found in environment variables")
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        print(f"[APPLE NOTES INGEST] Connected to Pinecone index")
        
        vectors = []
        for note in notes_data:
            # Truncate note body to avoid exceeding Pinecone's 40KB metadata limit
            body_text = note['body']
            if len(body_text) > 1000:
                body_text = body_text[:1000] + "... (truncated)"
            
            # Truncate title if too long
            title = note['name']
            if len(title) > 100:
                title = title[:100] + "..."
            
            text = f"Note: {title}\n\n{body_text}"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_notes',
                    'type': 'note',
                    'title': title,
                    'created_date': note['created'][:50] if note['created'] else '',
                    'modified_date': note['modified'][:50] if note['modified'] else ''
                }
            })
        
        print(f"[APPLE NOTES INGEST] Created {len(vectors)} vectors")
        
        # Upsert one at a time to avoid batch size issues
        for i, vector in enumerate(vectors):
            print(f"[APPLE NOTES INGEST] Upserting vector {i+1}/{len(vectors)}")
            try:
                index_to_use.upsert(vectors=[vector])
            except Exception as e:
                print(f"[APPLE NOTES INGEST] Error upserting vector {i+1}: {e}")
                continue
        
        print(f"[APPLE NOTES INGEST] Successfully ingested {len(notes_data)} notes")
        
        return {
            "message": f"Successfully ingested {len(notes_data)} Apple Notes",
            "count": len(notes_data)
        }
    
    except Exception as e:
        print(f"[APPLE NOTES INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-apple-calendar")
async def ingest_apple_calendar(request: CreateUserDatabaseRequest):
    """Fetch and ingest Apple Calendar events into the database"""
    try:
        print(f"[APPLE CALENDAR INGEST] Starting ingestion for user {request.user_id}")
        
        # Get user's Pinecone index
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[APPLE CALENDAR INGEST] Using Pinecone index: {pinecone_index_name}")
        
        # Fetch calendar events with CalDAV credentials if provided
        print(f"[APPLE CALENDAR INGEST] Fetching calendar events...")
        
        # Create a temporary request object with CalDAV credentials
        temp_request = UploadDocumentsRequest(
            user_id=request.user_id,
            permissions={},
            apple_calendar_email=request.apple_calendar_email,
            apple_calendar_password=request.apple_calendar_password
        )
        
        calendar_response = await fetch_apple_calendar(temp_request)
        events_data = calendar_response["events"]
        print(f"[APPLE CALENDAR INGEST] Fetched {len(events_data)} events")
        
        # Process and ingest
        global embedding_model
        if not embedding_model:
            print(f"[APPLE CALENDAR INGEST] Initializing embedding model...")
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not os.getenv("PINECONE_API_KEY"):
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found in environment variables")
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        print(f"[APPLE CALENDAR INGEST] Connected to Pinecone index")
        
        vectors = []
        for event in events_data:
            # Truncate notes if too long
            notes = event.get('notes', '')
            if len(notes) > 1000:
                notes = notes[:1000] + "... (truncated)"
            
            # Truncate summary if too long
            summary = event.get('summary', 'No Title')
            if len(summary) > 100:
                summary = summary[:100] + "..."
            
            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {event['calendar']}\n"
            text += f"Start: {event['start_date']}\n"
            text += f"End: {event['end_date']}\n"
            
            if event.get('location'):
                text += f"Location: {event['location']}\n"
            
            if notes:
                text += f"\nNotes:\n{notes}\n"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_calendar',
                    'type': 'calendar_event',
                    'calendar': event['calendar'],
                    'event_title': summary,
                    'start_date': event['start_date'][:50] if event.get('start_date') else '',
                    'end_date': event['end_date'][:50] if event.get('end_date') else ''
                }
            })
        
        print(f"[APPLE CALENDAR INGEST] Created {len(vectors)} vectors")
        
        # Upsert one at a time to avoid batch size issues
        for i, vector in enumerate(vectors):
            print(f"[APPLE CALENDAR INGEST] Upserting vector {i+1}/{len(vectors)}")
            try:
                index_to_use.upsert(vectors=[vector])
            except Exception as e:
                print(f"[APPLE CALENDAR INGEST] Error upserting vector {i+1}: {e}")
                continue
        
        print(f"[APPLE CALENDAR INGEST] Successfully ingested {len(events_data)} events")
        
        return {
            "message": f"Successfully ingested {len(events_data)} Apple Calendar events",
            "count": len(events_data)
        }
    
    except Exception as e:
        print(f"[APPLE CALENDAR INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_user_library_with_token(music_user_token: str):
    """Fetch user's Apple Music library using Music User Token"""
    try:
        import requests

        # Apple Music API endpoint for user's library
        base_url = 'https://api.music.apple.com/v1/me/library'

        headers = {
            'Authorization': f'Bearer {music_user_token}',
            'Music-User-Token': music_user_token,
            'Content-Type': 'application/json'
        }

        # Fetch songs from user's library
        songs_url = f'{base_url}/songs'
        songs_response = requests.get(songs_url, headers=headers, params={'limit': 100})

        # Fetch albums from user's library
        albums_url = f'{base_url}/albums'
        albums_response = requests.get(albums_url, headers=headers, params={'limit': 50})

        # Fetch artists from user's library
        artists_url = f'{base_url}/artists'
        artists_response = requests.get(artists_url, headers=headers, params={'limit': 50})

        # Combine results
        music_data = {
            'results': {
                'songs': songs_response.json() if songs_response.status_code == 200 else {},
                'albums': albums_response.json() if albums_response.status_code == 200 else {},
                'artists': artists_response.json() if artists_response.status_code == 200 else {}
            }
        }

        return music_data
    except Exception as e:
        print(f"[APPLE MUSIC] Error fetching user library with token: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.post("/ingest-apple-music")
async def ingest_apple_music(request: AppleMusicRequest):
    """Fetch and ingest Apple Music data into the database using Music User Token"""
    try:
        print(f"[APPLE MUSIC INGEST] Starting ingestion for user {request.user_id}")

        # Get user's Pinecone index
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[APPLE MUSIC INGEST] Using Pinecone index: {pinecone_index_name}")

        # Use Music User Token from request (from Apple ID authentication)
        music_user_token = request.music_user_token

        if not music_user_token:
            # Fallback to developer credentials if no user token provided
            key_id = request.key_id or os.getenv("APPLE_MUSIC_KEY_ID")
            team_id = request.team_id or os.getenv("APPLE_MUSIC_TEAM_ID")
            private_key = request.private_key or os.getenv("APPLE_MUSIC_PRIVATE_KEY_PATH")

            if not all([key_id, team_id, private_key]):
                raise HTTPException(
                    status_code=400,
                    detail="Apple Music credentials not provided. Please provide music_user_token or key_id, team_id, and private_key."
                )

            # Import the fetch_apple_music script
            import sys
            from pathlib import Path
            import tempfile
            scripts_path = Path(__file__).parent.parent / "scripts"
            sys.path.append(str(scripts_path))

            from fetch_apple_music import generate_developer_token, fetch_user_library, format_song, format_album, format_artist

            # If private_key is a file path, read from file. Otherwise, treat as the key content
            if request.private_key and len(request.private_key) > 100 and '\n' in request.private_key:
                # It's the actual key content, save to temp file
                print(f"[APPLE MUSIC INGEST] Using provided private key content")
                with tempfile.NamedTemporaryFile(mode='w', suffix='.p8', delete=False) as f:
                    f.write(request.private_key)
                    private_key_path = f.name
            else:
                # It's a file path
                private_key_path = private_key

            # Generate developer token
            print(f"[APPLE MUSIC INGEST] Generating developer token...")
            token = generate_developer_token(key_id, team_id, private_key_path)

            if not token:
                raise HTTPException(status_code=500, detail="Failed to generate Apple Music developer token")

            print(f"[APPLE MUSIC INGEST] Developer token generated successfully")

            # Fetch music data using developer token (catalog search)
            print(f"[APPLE MUSIC INGEST] Fetching music data...")
            music_data = fetch_user_library(token, storefront='us')
        else:
            # Use Music User Token to fetch user's library
            print(f"[APPLE MUSIC INGEST] Using Music User Token to fetch user library")
            music_data = await fetch_user_library_with_token(music_user_token)

        if not music_data:
            raise HTTPException(status_code=500, detail="Failed to fetch Apple Music data")

        print(f"[APPLE MUSIC INGEST] Music data fetched successfully")

        # Process and ingest
        global embedding_model
        if not embedding_model:
            print(f"[APPLE MUSIC INGEST] Initializing embedding model...")
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        if not os.getenv("PINECONE_API_KEY"):
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found in environment variables")

        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        print(f"[APPLE MUSIC INGEST] Connected to Pinecone index")

        vectors = []
        total_items = 0

        # Process songs
        songs = music_data.get('results', {}).get('songs', {}).get('data', [])
        for song in songs:
            text = format_song(song)
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'song',
                    'data_type': 'song'
                }
            })
            total_items += 1

        # Process albums
        albums = music_data.get('results', {}).get('albums', {}).get('data', [])
        for album in albums:
            text = format_album(album)
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'album',
                    'data_type': 'album'
                }
            })
            total_items += 1

        # Process artists
        artists = music_data.get('results', {}).get('artists', {}).get('data', [])
        for artist in artists:
            text = format_artist(artist)
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'artist',
                    'data_type': 'artist'
                }
            })
            total_items += 1

        print(f"[APPLE MUSIC INGEST] Created {len(vectors)} vectors from {total_items} music items")

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            print(f"[APPLE MUSIC INGEST] Upserting batch {i//batch_size + 1}/{(len(vectors) + batch_size - 1)//batch_size}")
            try:
                index_to_use.upsert(vectors=batch)
            except Exception as e:
                print(f"[APPLE MUSIC INGEST] Error upserting batch: {e}")
                continue

        print(f"[APPLE MUSIC INGEST] Successfully ingested {total_items} Apple Music items")

        return {
            "message": f"Successfully ingested {total_items} Apple Music items (songs, albums, artists)",
            "count": total_items
        }

    except Exception as e:
        print(f"[APPLE MUSIC INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-messages")
async def upload_messages(file: UploadFile = File(...), user_id: str = Form(...)):
    """Upload and process mobile message export file"""
    print(f"[MESSAGE UPLOAD] Starting message upload for user {user_id}")
    print(f"[MESSAGE UPLOAD] File: {file.filename}, Type: {file.content_type}")

    try:
        # Create message_exports directory if it doesn't exist
        message_exports_dir = RAW_DOCS_DIR / "message_exports"
        message_exports_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        file_path = message_exports_dir / file.filename
        print(f"[MESSAGE UPLOAD] Saving file to {file_path}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the message file using parse_messages script
        print(f"[MESSAGE UPLOAD] Processing message file...")
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from parse_messages import parse_messages

        # Call parse_messages with the uploaded file
        parse_messages(input_file=file_path)

        print(f"[MESSAGE UPLOAD] Message processing complete")

        return {
            "message": f"Successfully uploaded and processed {file.filename}",
            "file": file.filename
        }

    except Exception as e:
        print(f"[MESSAGE UPLOAD] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-android-sms")
async def upload_android_sms(user_id: str = Body(...), messages: List[dict] = Body(...)):
    """Receive and process SMS messages from Android device"""
    print(f"[ANDROID SMS] Starting SMS upload for user {user_id}")
    print(f"[ANDROID SMS] Received {len(messages)} messages")

    try:
        # Create message_exports directory if it doesn't exist
        message_exports_dir = RAW_DOCS_DIR / "message_exports"
        message_exports_dir.mkdir(parents=True, exist_ok=True)

        # Save messages as JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = message_exports_dir / f"android_sms_{timestamp}.json"

        with open(file_path, "w") as f:
            json.dump(messages, f, indent=2)

        print(f"[ANDROID SMS] Saved messages to {file_path}")

        # Process the messages using parse_messages script
        print(f"[ANDROID SMS] Processing messages...")
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from parse_messages import parse_messages

        # Call parse_messages with the JSON file
        parse_messages(input_file=file_path)

        print(f"[ANDROID SMS] Message processing complete")

        return {
            "message": f"Successfully processed {len(messages)} SMS messages",
            "count": len(messages)
        }

    except Exception as e:
        print(f"[ANDROID SMS] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-documents")
async def upload_documents(request: UploadDocumentsRequest, background_tasks: BackgroundTasks):
    """Upload documents based on user permissions"""
    print(f"[UPLOAD] Starting document upload for user {request.user_id}")
    print(f"[UPLOAD] Permissions: {request.permissions}")
    try:
        # Get user's Pinecone index
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        print(f"[UPLOAD] Fetching user settings...")
        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            print(f"[UPLOAD] ERROR: User database not found")
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[UPLOAD] Using Pinecone index: {pinecone_index_name}")

        # Get existing permissions and uploaded data sources
        existing_permissions = user_settings.data[0].get("permissions", {})
        uploaded_data_sources = user_settings.data[0].get("uploaded_data_sources", {})
        print(f"[UPLOAD] Existing permissions: {existing_permissions}")
        print(f"[UPLOAD] Uploaded data sources: {uploaded_data_sources}")

        # Determine which permissions need data uploaded
        # A permission needs upload if it's True and hasn't been uploaded yet
        permissions_to_upload = {}
        for key, value in request.permissions.items():
            if value and not uploaded_data_sources.get(key):
                permissions_to_upload[key] = value
                print(f"[UPLOAD] Permission needs upload: {key} = {value} (uploaded: {uploaded_data_sources.get(key)})")

        if not permissions_to_upload:
            print(f"[UPLOAD] No new data to upload. All enabled permissions already uploaded.")
            # Still save the permissions to ensure they're up to date
            supabase.table("user_settings").update({
                "permissions": request.permissions,
                "setup_step": 3
            }).eq("user_id", request.user_id).execute()
            return {"message": "No new data to upload", "results": {}}

        print(f"[UPLOAD] Permissions to upload data for: {permissions_to_upload}")

        # Save permissions to Supabase
        print(f"[UPLOAD] Saving permissions to Supabase...")
        supabase.table("user_settings").update({
            "permissions": request.permissions,
            "setup_step": 3
        }).eq("user_id", request.user_id).execute()

        # Fetch data based on permissions that need upload
        results = {}

        if permissions_to_upload.get("appleCalendar"):
            print(f"[UPLOAD] Processing appleCalendar permission (NEW)...")
            try:
                calendar_response = await fetch_apple_calendar()
                events_data = calendar_response["events"]
                count = await process_and_ingest_data(request.user_id, 'apple_calendar', events_data, pinecone_index_name)
                results['appleCalendar'] = count
                print(f"[UPLOAD] Apple Calendar processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching apple calendar: {e}")
                import traceback
                traceback.print_exc()
                results['appleCalendar'] = 0
        elif request.permissions.get("appleCalendar"):
            print(f"[UPLOAD] Skipping appleCalendar (data already uploaded)")

        if permissions_to_upload.get("calendar"):
            print(f"[UPLOAD] Processing Google Calendar permission (NEW)...")
            try:
                # Check if OAuth token exists before attempting to fetch
                if not has_oauth_token(request.user_id, 'calendar'):
                    print(f"[UPLOAD] No OAuth token found for Google Calendar, skipping. User needs to authorize via /auth/calendar endpoint.")
                    results['calendar'] = 0
                else:
                    creds = get_user_credentials(request.user_id, 'calendar')
                    calendar_data = await fetch_calendar_data(request.user_id, creds)
                    count = await process_and_ingest_data(request.user_id, 'google_calendar', calendar_data, pinecone_index_name)
                    results['calendar'] = count
                    print(f"[UPLOAD] Google Calendar processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching google calendar: {e}")
                import traceback
                traceback.print_exc()
                results['calendar'] = 0
        elif request.permissions.get("calendar"):
            print(f"[UPLOAD] Skipping calendar (data already uploaded)")

        if permissions_to_upload.get("email"):
            print(f"[UPLOAD] Processing email permission (NEW)...")
            try:
                # Check if OAuth token exists before attempting to fetch
                if not has_oauth_token(request.user_id, 'gmail'):
                    print(f"[UPLOAD] No OAuth token found for Gmail, skipping. User needs to authorize via /auth/gmail endpoint.")
                    results['email'] = 0
                else:
                    creds = get_user_credentials(request.user_id, 'gmail')
                    gmail_data = await fetch_gmail_data(request.user_id, creds)
                    count = await process_and_ingest_data(request.user_id, 'gmail', gmail_data, pinecone_index_name)
                    results['email'] = count
                    print(f"[UPLOAD] Gmail processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching gmail: {e}")
                import traceback
                traceback.print_exc()
                results['email'] = 0
        elif request.permissions.get("email"):
            print(f"[UPLOAD] Skipping email (data already uploaded)")

        if permissions_to_upload.get("googleDrive"):
            print(f"[UPLOAD] Processing googleDrive permission (NEW)...")
            try:
                # Check if OAuth token exists before attempting to fetch
                if not has_oauth_token(request.user_id, 'google_drive'):
                    print(f"[UPLOAD] No OAuth token found for Google Drive, skipping. User needs to authorize via /auth/google_drive endpoint.")
                    results['googleDrive'] = 0
                else:
                    creds = get_user_credentials(request.user_id, 'google_drive')
                    drive_data = await fetch_google_drive_data(request.user_id, creds)
                    count = await process_and_ingest_data(request.user_id, 'google_drive', drive_data, pinecone_index_name)
                    results['googleDrive'] = count
                    print(f"[UPLOAD] Google Drive processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching google drive: {e}")
                import traceback
                traceback.print_exc()
                results['googleDrive'] = 0
        elif request.permissions.get("googleDrive"):
            print(f"[UPLOAD] Skipping googleDrive (data already uploaded)")

        if permissions_to_upload.get("notes"):
            print(f"[UPLOAD] Processing notes permission (NEW)...")
            try:
                notes_response = await fetch_apple_notes()
                notes_data = notes_response["notes"]
                count = await process_and_ingest_data(request.user_id, 'apple_notes', notes_data, pinecone_index_name)
                results['notes'] = count
                print(f"[UPLOAD] Apple Notes processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching apple notes: {e}")
                import traceback
                traceback.print_exc()
                results['notes'] = 0
        elif request.permissions.get("notes"):
            print(f"[UPLOAD] Skipping notes (data already uploaded)")

        if permissions_to_upload.get("appleMusic"):
            print(f"[UPLOAD] Processing appleMusic permission (NEW)...")
            try:
                # Apple Music requires developer credentials (key_id, team_id, private_key_path)
                # These would need to be stored in user settings or environment variables
                # For now, we'll check if they're available in environment
                key_id = os.getenv("APPLE_MUSIC_KEY_ID")
                team_id = os.getenv("APPLE_MUSIC_TEAM_ID")
                private_key_path = os.getenv("APPLE_MUSIC_PRIVATE_KEY_PATH")
                
                if key_id and team_id and private_key_path:
                    music_data = await fetch_apple_music_data(key_id, team_id, private_key_path)
                    count = await process_and_ingest_data(request.user_id, 'apple_music', music_data, pinecone_index_name)
                    results['appleMusic'] = count
                    print(f"[UPLOAD] Apple Music processing complete: {count} documents")
                else:
                    print(f"[UPLOAD] Apple Music credentials not found in environment, skipping")
                    results['appleMusic'] = 0
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching apple music: {e}")
                import traceback
                traceback.print_exc()
                results['appleMusic'] = 0
        elif request.permissions.get("appleMusic"):
            print(f"[UPLOAD] Skipping appleMusic (data already uploaded)")

        # Update uploaded_data_sources to mark successfully uploaded data sources
        successfully_uploaded = {}
        for key, count in results.items():
            if count > 0:
                successfully_uploaded[key] = True

        if successfully_uploaded:
            print(f"[UPLOAD] Marking data sources as uploaded: {successfully_uploaded}")
            # Merge with existing uploaded_data_sources
            updated_uploaded_data_sources = {**uploaded_data_sources, **successfully_uploaded}
            supabase.table("user_settings").update({
                "uploaded_data_sources": updated_uploaded_data_sources
            }).eq("user_id", request.user_id).execute()

        total_processed = sum(results.values())
        print(f"[UPLOAD] Total documents processed: {total_processed}")
        print(f"[UPLOAD] Results breakdown: {results}")

        # Mark setup as complete
        print(f"[UPLOAD] Marking setup as complete...")
        supabase.table("user_settings").update({
            "setup_step": 4  # 4 = complete
        }).eq("user_id", request.user_id).execute()

        return {
            "message": f"Successfully processed {total_processed} documents",
            "details": results
        }

    except Exception as e:
        print(f"[UPLOAD] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# OAuth Endpoints

@app.get("/auth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None, iss: str = None, scope: str = None):
    """Handle OAuth callback from Google"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    if state not in oauth_states:
        print(f"[OAUTH CALLBACK] Invalid state parameter: {state}")
        print(f"[OAUTH CALLBACK] Available states: {list(oauth_states.keys())}")
        
        # Check if this might be a duplicate callback - if tokens were just saved, return success
        # We can't check by user_id since we don't have it from the state, but we can check
        # if tokens were saved very recently (within last 30 seconds)
        if supabase and scope:
            returned_scopes = scope.split(' ') if scope else []
            scope_to_service = {
                'https://www.googleapis.com/auth/calendar.readonly': 'calendar',
                'https://www.googleapis.com/auth/gmail.readonly': 'gmail',
                'https://www.googleapis.com/auth/drive.readonly': 'google_drive'
            }
            
            # Check if any of the services in the scope have tokens created very recently
            from datetime import datetime, timedelta
            recent_threshold = datetime.utcnow() - timedelta(seconds=30)
            
            for returned_scope in returned_scopes:
                if returned_scope in scope_to_service:
                    service_to_check = scope_to_service[returned_scope]
                    # Look for tokens created in the last 30 seconds
                    existing_tokens = supabase.table("oauth_tokens").select("*").eq("service", service_to_check).gte("created_at", recent_threshold.isoformat()).execute()
                    if existing_tokens.data:
                        print(f"[OAUTH CALLBACK] Found recently created tokens for {service_to_check}, treating as duplicate callback")
                        return {"service": service_to_check, "success": True}
        
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter. The authorization may have expired or the server was restarted. Please try authorizing again."
        )

    state_data = oauth_states[state]
    user_id = state_data["user_id"]
    service = state_data["service"]
    
    print(f"[OAUTH CALLBACK] Received callback for service: {service}")
    print(f"[OAUTH CALLBACK] Received scopes: {scope}")
    
    try:
        # Manually exchange authorization code for tokens
        config = get_oauth_config()
        client_id = config['web']['client_id']
        client_secret = config['web']['client_secret']
        
        token_url = "https://oauth2.googleapis.com/token"
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': f'{base_url}/auth/callback',
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Parse returned scopes to determine which services were authorized
        returned_scopes = scope.split(' ') if scope else []
        print(f"[OAUTH CALLBACK] Parsed returned scopes: {returned_scopes}")
        
        # Only save token for the specific service that was requested (from state)
        # Don't save for all services in the returned scopes
        service_to_save = service
        print(f"[OAUTH CALLBACK] Saving token for service: {service_to_save}")
        
        # Google doesn't always return a refresh token on subsequent authorizations
        # Preserve existing refresh token if not provided in response
        refresh_token = token_json.get('refresh_token')
        if not refresh_token and supabase:
            # Try to get existing token to preserve refresh token
            existing_tokens = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", service_to_save).execute()
            if existing_tokens.data:
                existing_refresh_token = existing_tokens.data[0].get("refresh_token")
                if existing_refresh_token:
                    print(f"[OAUTH CALLBACK] Preserving existing refresh token for {service_to_save}")
                    refresh_token = existing_refresh_token
        
        # Create Credentials object from token response
        creds = Credentials(
            token=token_json['access_token'],
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=GOOGLE_SCOPES[service_to_save]
        )
        
        # Store credentials in Supabase
        if supabase:
            credentials_data = {
                "user_id": user_id,
                "service": service_to_save,
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
                "expiry": creds.expiry.isoformat() if creds.expiry else None
            }

            # Delete existing token for this user/service if it exists, then insert new one
            supabase.table("oauth_tokens").delete().eq("user_id", user_id).eq("service", service_to_save).execute()
            supabase.table("oauth_tokens").insert(credentials_data).execute()
        
        # Clean up state
        del oauth_states[state]

        # Redirect to mobile app deep link
        from fastapi.responses import RedirectResponse
        return {"service": service, "success": True}

    except Exception as e:
        return {"service": service, "success": False, "error": str(e)}

def get_oauth_config():
    """Load OAuth client configuration"""
    client_secrets_file = CREDENTIALS_DIR / "client_secret.json"
    if not client_secrets_file.exists():
        raise FileNotFoundError("Google OAuth credentials not found")
    
    with open(client_secrets_file, 'r') as f:
        return json_module.load(f)

@app.get("/auth/{service}")
async def authorize_google_service(service: str, user_id: str = Query(..., description="User ID")):
    """Initiate OAuth flow for a Google service"""
    # Prevent this route from matching 'callback' as a service
    if service == "callback":
        raise HTTPException(status_code=404, detail="Not found")
    
    if service not in GOOGLE_SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    try:
        config = get_oauth_config()
        client_id = config['web']['client_id']
        
        # Generate state parameter to prevent CSRF
        state = str(uuid.uuid4())
        oauth_states[state] = {
            "user_id": user_id,
            "service": service
        }
        
        # Manually construct authorization URL without PKCE
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        params = {
            'client_id': client_id,
            'redirect_uri': f'{base_url}/auth/callback',
            'scope': ' '.join(GOOGLE_SCOPES[service]),
            'response_type': 'code',
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'state': state
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        
        return {"authorization_url": auth_url, "state": state}
    
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/status/{user_id}")
async def get_auth_status(user_id: str):
    """Get authorization status for all services for a user"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")
    
    try:
        # Get all OAuth tokens for the user
        tokens = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).execute()
        
        # Get user settings which contains stored permissions
        user_settings = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        stored_permissions = {}
        if user_settings.data:
            stored_permissions = user_settings.data[0].get("permissions", {})
        
        status = {}
        for service in GOOGLE_SCOPES.keys():
            service_tokens = [t for t in tokens.data if t["service"] == service]
            status[service] = len(service_tokens) > 0
        
        # Add local permissions from stored settings
        status["notes"] = stored_permissions.get("notes", False)
        status["appleCalendar"] = stored_permissions.get("appleCalendar", False)
        status["spotify"] = stored_permissions.get("spotify", False)
        
        return {"status": status}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Spotify OAuth Endpoints

@app.get("/spotify/authorize")
async def authorize_spotify(user_id: str = Query(..., description="User ID")):
    """Initiate Spotify OAuth flow"""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", f"{base_url}/spotify/callback")
    
    if not client_id:
        raise HTTPException(status_code=500, detail="SPOTIFY_CLIENT_ID not configured")
    
    try:
        # Generate state parameter to prevent CSRF
        state = str(uuid.uuid4())
        oauth_states[state] = {
            "user_id": user_id,
            "service": "spotify"
        }
        
        # Spotify OAuth scopes
        scopes = [
            "user-read-private",
            "user-read-email",
            "user-library-read",
            "user-top-read",
            "user-read-playback-state",
            "user-read-recently-played",
            "playlist-read-private",
            "playlist-read-collaborative"
        ]
        
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'state': state
        }
        
        auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
        
        return {"authorization_url": auth_url, "state": state}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/spotify/callback")
async def spotify_callback(code: str = None, state: str = None, error: str = None):
    """Handle Spotify OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    state_data = oauth_states[state]
    user_id = state_data["user_id"]
    
    try:
        # Exchange authorization code for tokens
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", f"{base_url}/spotify/callback")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Spotify credentials not configured")
        
        token_url = "https://accounts.spotify.com/api/token"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Store tokens in Supabase
        if supabase:
            credentials_data = {
                "user_id": user_id,
                "service": "spotify",
                "token": token_json['access_token'],
                "refresh_token": token_json.get('refresh_token'),
                "token_uri": "https://accounts.spotify.com/api/token",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": token_json.get('scope', ''),
                "expiry": (datetime.now().timestamp() + token_json.get('expires_in', 3600))
            }
            
            # Delete existing token for this user/service if it exists, then insert new one
            supabase.table("oauth_tokens").delete().eq("user_id", user_id).eq("service", "spotify").execute()
            supabase.table("oauth_tokens").insert(credentials_data).execute()
            
            # Update user settings to mark Spotify as authorized
            user_settings = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
            if user_settings.data:
                current_permissions = user_settings.data[0].get("permissions", {})
                current_permissions["spotify"] = True
                
                supabase.table("user_settings").update({
                    "permissions": current_permissions
                }).eq("user_id", user_id).execute()
        
        # Clean up state
        del oauth_states[state]
        
        # Redirect to mobile app deep link
        from fastapi.responses import RedirectResponse
        return {"service": "spotify", "success": True}
    
    except Exception as e:
        return {"service": "spotify", "success": False, "error": str(e)}

def has_oauth_token(user_id: str, service: str) -> bool:
    """Check if OAuth token exists for a user and service"""
    print(f"[CREDS] Checking if OAuth token exists for user {user_id}, service {service}")
    if not supabase:
        return False

    try:
        token_data = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", service).execute()
        has_token = len(token_data.data) > 0
        print(f"[CREDS] OAuth token exists: {has_token}")
        return has_token
    except Exception as e:
        print(f"[CREDS] Error checking OAuth token: {e}")
        return False

def get_user_credentials(user_id: str, service: str):
    """Get OAuth credentials for a user and service from Supabase"""
    print(f"[CREDS] Getting credentials for user {user_id}, service {service}")
    if not supabase:
        raise Exception("Supabase not initialized")

    try:
        token_data = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", service).execute()

        if not token_data.data:
            print(f"[CREDS] ERROR: No OAuth token found for user {user_id} and service {service}")
            raise Exception(f"No OAuth token found for user {user_id} and service {service}")

        token = token_data.data[0]
        print(f"[CREDS] Found token for service {service}, expired: {token.get('expiry')}")

        # Create Credentials object
        creds = Credentials(
            token=token["token"],
            refresh_token=token["refresh_token"],
            token_uri=token["token_uri"],
            client_id=token["client_id"],
            client_secret=token["client_secret"],
            scopes=token["scopes"]
        )

        # Set expiry if available
        if token["expiry"]:
            from datetime import datetime
            creds.expiry = datetime.fromisoformat(token["expiry"])

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            print(f"[CREDS] Token expired, refreshing...")
            creds.refresh(Request())

            # Update token in Supabase
            supabase.table("oauth_tokens").update({
                "token": creds.token,
                "expiry": creds.expiry.isoformat() if creds.expiry else None
            }).eq("user_id", user_id).eq("service", service).execute()
            print(f"[CREDS] Token refreshed successfully")
        else:
            print(f"[CREDS] Token is valid, no refresh needed")

        return creds
    
    except Exception as e:
        raise Exception(f"Error getting credentials: {str(e)}")

def get_spotify_credentials(user_id: str):
    """Get Spotify OAuth credentials for a user from Supabase"""
    print(f"[SPOTIFY CREDS] Getting credentials for user {user_id}")
    if not supabase:
        raise Exception("Supabase not initialized")

    try:
        token_data = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", "spotify").execute()

        if not token_data.data:
            print(f"[SPOTIFY CREDS] ERROR: No Spotify token found for user {user_id}")
            raise Exception(f"No Spotify token found for user {user_id}")

        token = token_data.data[0]
        print(f"[SPOTIFY CREDS] Found Spotify token")

        # Check if token needs refresh
        expiry = token.get("expiry")
        if expiry:
            expiry_time = datetime.fromtimestamp(expiry)
            if datetime.now() >= expiry_time:
                print(f"[SPOTIFY CREDS] Token expired, refreshing...")
                # Refresh token
                refresh_token = token.get("refresh_token")
                client_id = token.get("client_id")
                client_secret = token.get("client_secret")
                
                token_url = "https://accounts.spotify.com/api/token"
                token_data_req = {
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': client_id,
                    'client_secret': client_secret
                }
                
                token_response = requests.post(token_url, data=token_data_req)
                token_response.raise_for_status()
                token_json = token_response.json()
                
                # Update token in Supabase
                new_expiry = datetime.now().timestamp() + token_json.get('expires_in', 3600)
                supabase.table("oauth_tokens").update({
                    "token": token_json['access_token'],
                    "expiry": new_expiry
                }).eq("user_id", user_id).eq("service", "spotify").execute()
                
                return token_json['access_token']
            else:
                print(f"[SPOTIFY CREDS] Token is valid")
                return token["token"]
        else:
            return token["token"]
    
    except Exception as e:
        raise Exception(f"Error getting Spotify credentials: {str(e)}")

async def fetch_spotify_data(user_id: str):
    """Fetch Spotify data using OAuth credentials"""
    try:
        print(f"[SPOTIFY FETCH] Starting Spotify data fetch for user {user_id}")
        
        # Get access token
        access_token = get_spotify_credentials(user_id)
        
        # Import the Spotify client from the fetch script
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from fetch_spotify import SpotifyClient, save_spotify_data
        
        # Create Spotify client (we already have the token, so we don't need to re-auth)
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", f"{base_url}/spotify/callback")
        
        client = SpotifyClient(client_id, client_secret, redirect_uri, access_token=access_token)
        
        # Fetch all data
        saved_files = []
        
        # Get user profile
        print("[SPOTIFY FETCH] Fetching user profile...")
        profile = client.get_user_profile()
        spotify_user_id = profile.get("id", "unknown")
        
        # Get top tracks
        print("[SPOTIFY FETCH] Fetching top tracks...")
        top_tracks = client.get_top_tracks(limit=50, time_range="medium_term")
        if top_tracks.get("items"):
            output_path = save_spotify_data(top_tracks, 'top_tracks', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved top tracks -> {output_path.name}")
        
        # Get top artists
        print("[SPOTIFY FETCH] Fetching top artists...")
        top_artists = client.get_top_artists(limit=50, time_range="medium_term")
        if top_artists.get("items"):
            output_path = save_spotify_data(top_artists, 'top_artists', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved top artists -> {output_path.name}")
        
        # Get saved tracks
        print("[SPOTIFY FETCH] Fetching saved tracks...")
        saved_tracks = client.get_saved_tracks(limit=50)
        if saved_tracks.get("items"):
            output_path = save_spotify_data(saved_tracks, 'saved_tracks', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved tracks -> {output_path.name}")
        
        # Get playlists
        print("[SPOTIFY FETCH] Fetching playlists...")
        playlists = client.get_playlists(limit=50)
        if playlists.get("items"):
            output_path = save_spotify_data(playlists, 'playlists', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved playlists -> {output_path.name}")
        
        # Get recently played
        print("[SPOTIFY FETCH] Fetching recently played...")
        recently_played = client.get_recently_played(limit=50)
        if recently_played.get("items"):
            output_path = save_spotify_data(recently_played, 'recently_played', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved recently played -> {output_path.name}")
        
        print(f"[SPOTIFY FETCH] Total files saved: {len(saved_files)}")
        return saved_files
        
    except Exception as e:
        print(f"[SPOTIFY FETCH] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Spotify data: {str(e)}")

class SpotifyRequest(BaseModel):
    user_id: str

@app.post("/ingest-spotify")
async def ingest_spotify(request: SpotifyRequest, background_tasks: BackgroundTasks):
    """Fetch and ingest Spotify data for a user"""
    try:
        print(f"[SPOTIFY INGEST] Starting Spotify ingestion for user {request.user_id}")
        
        # Fetch Spotify data
        saved_files = await fetch_spotify_data(request.user_id)
        
        if not saved_files:
            return DocumentResponse(
                message="No Spotify data was fetched",
                document_count=0
            )
        
        # Get user's Pinecone index
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
        
        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found")
        
        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        
        # Process and ingest the saved files
        print(f"[SPOTIFY INGEST] Processing {len(saved_files)} files...")
        total_documents = 0
        
        for file_path in saved_files:
            try:
                count = await process_and_ingest_data(request.user_id, 'spotify', [{"file_path": file_path}], pinecone_index_name)
                total_documents += count
                print(f"[SPOTIFY INGEST] Processed {file_path}: {count} documents")
            except Exception as e:
                print(f"[SPOTIFY INGEST] Error processing {file_path}: {e}")
        
        print(f"[SPOTIFY INGEST] Total documents ingested: {total_documents}")
        
        return DocumentResponse(
            message=f"Successfully ingested Spotify data",
            document_count=total_documents
        )
        
    except Exception as e:
        print(f"[SPOTIFY INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-google-search-history")
async def ingest_google_search_history(request: GoogleSearchHistoryRequest):
    """Ingest Google Search History from a Google Takeout JSON file"""
    try:
        print(f"[SEARCH HISTORY INGEST] Starting ingestion for user {request.user_id}")
        
        # Import and use the fetch_google_search_history script
        sys.path.append(str(Path(__file__).parent.parent / "scripts"))
        from fetch_google_search_history import fetch_search_history_from_json
        
        # Parse the JSON file
        json_path = Path(request.json_path)
        if not json_path.exists():
            raise HTTPException(status_code=400, detail=f"JSON file not found: {request.json_path}")
        
        search_entries = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: fetch_search_history_from_json(json_path)
        )
        
        print(f"[SEARCH HISTORY INGEST] Found {len(search_entries)} search entries")
        
        if not search_entries:
            return DocumentResponse(
                message="No search entries found in the JSON file",
                document_count=0
            )
        
        # Get user's Pinecone index
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
        
        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found")
        
        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        
        # Process and ingest the search entries
        print(f"[SEARCH HISTORY INGEST] Processing search entries...")
        global embedding_model
        
        if not embedding_model:
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        
        vectors = []
        for entry in search_entries:
            query = entry.get('query', '')
            timestamp = entry.get('timestamp')
            raw_time = entry.get('raw_time', '')
            
            if not query:
                continue
            
            # Format the search query as text
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else raw_time
            text = f"Google Search Query: {query}\nTimestamp: {timestamp_str}"
            
            embedding = embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_search_history',
                    'type': 'search_query',
                    'query': query[:200],
                    'timestamp': timestamp_str[:50] if timestamp_str else ''
                }
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            index_to_use.upsert(vectors=batch)
        
        print(f"[SEARCH HISTORY INGEST] Successfully ingested {len(vectors)} search queries")
        
        return DocumentResponse(
            message=f"Successfully ingested {len(vectors)} Google Search History entries",
            document_count=len(vectors)
        )
        
    except Exception as e:
        print(f"[SEARCH HISTORY INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class ResetDatabaseRequest(BaseModel):
    user_id: str

@app.post("/reset-user-database")
async def reset_user_database(request: ResetDatabaseRequest):
    """Delete user's Pinecone index, clear Supabase data, and recreate database"""
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found")
    
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")
    
    try:
        # Get user settings to find the Pinecone index name
        user_settings = supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
        
        if not user_settings.data:
            raise HTTPException(status_code=404, detail="User settings not found")
        
        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        
        # Delete Pinecone index if it exists
        if pinecone_index_name:
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            existing_indexes = [index.name for index in pc.list_indexes()]
            
            if pinecone_index_name in existing_indexes:
                print(f"[RESET] Deleting Pinecone index: {pinecone_index_name}")
                pc.delete_index(pinecone_index_name)
                import time
                # Wait for index deletion to complete
                while pinecone_index_name in [index.name for index in pc.list_indexes()]:
                    time.sleep(1)
                print(f"[RESET] Pinecone index deleted successfully")
        
        # Clear user data in Supabase using the reset function
        print(f"[RESET] Clearing user data in Supabase")
        
        # Call the reset_user_database function
        supabase.rpc("reset_user_database", {"target_user_id": request.user_id}).execute()
        
        print(f"[RESET] User data cleared successfully")
        
        # Create new Pinecone index
        print(f"[RESET] Creating new Pinecone index")
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        new_index_name = f"personal-db-{request.user_id[:8]}"
        
        pc.create_index(
            name=new_index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        
        # Wait for index to be ready
        while not pc.describe_index(new_index_name).status['ready']:
            time.sleep(1)
        
        print(f"[RESET] New Pinecone index created: {new_index_name}")
        
        # Update user settings with new index
        supabase.table("user_settings").update({
            "pinecone_index": new_index_name,
            "setup_step": 2
        }).eq("user_id", request.user_id).execute()
        
        return {"message": "Database reset successfully", "new_index_name": new_index_name}
    
    except Exception as e:
        print(f"[RESET] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def generate_apple_music_token(key_id: str, team_id: str, private_key_path: str):
    """Generate a JWT developer token for Apple Music API"""
    try:
        with open(private_key_path, 'r') as f:
            private_key = f.read()
        
        now = int(time.time())
        expiration = now + (6 * 30 * 24 * 60 * 60)
        
        payload = {
            'iss': team_id,
            'iat': now,
            'exp': expiration,
            'sub': 'user-music-library-read'
        }
        
        token = jwt.encode(payload, private_key, algorithm='ES256', headers={'kid': key_id})
        return token
    except Exception as e:
        print(f"[APPLE MUSIC] Error generating token: {e}")
        return None

async def fetch_apple_music_data(key_id: str, team_id: str, private_key_path: str, storefront: str = 'us'):
    """Fetch music data from Apple Music API"""
    try:
        print(f"[APPLE MUSIC] Generating developer token...")
        token = generate_apple_music_token(key_id, team_id, private_key_path)
        
        if not token:
            raise Exception("Failed to generate developer token")
        
        print(f"[APPLE MUSIC] Token generated successfully")
        
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        base_url = f'https://api.music.apple.com/v1/catalog/{storefront}'
        
        # Search for popular music as a sample (full library access requires user OAuth)
        search_url = f'{base_url}/search'
        params = {
            'term': 'popular',
            'types': 'songs,albums,artists',
            'limit': 20
        }
        
        print(f"[APPLE MUSIC] Fetching music data...")
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"[APPLE MUSIC] Data fetched successfully")
            return data
        else:
            print(f"[APPLE MUSIC] Error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")
    except Exception as e:
        print(f"[APPLE MUSIC] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Apple Music data: {str(e)}")

class AppleMusicRequest(BaseModel):
    key_id: str
    team_id: str
    private_key_path: str
    storefront: Optional[str] = 'us'

@app.post("/fetch-apple-music")
async def fetch_apple_music(request: AppleMusicRequest):
    """Fetch Apple Music data using developer credentials"""
    try:
        data = await fetch_apple_music_data(
            request.key_id,
            request.team_id,
            request.private_key_path,
            request.storefront
        )
        
        return {
            "message": "Successfully fetched Apple Music data",
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
