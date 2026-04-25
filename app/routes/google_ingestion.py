import os
import sys
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
import io
import pickle as pkl
import uuid
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import DocumentResponse, GoogleSearchHistoryRequest
from utils import RAW_DOCS_DIR, PROCESSED_CHUNKS_DIR, CREDENTIALS_DIR, PINECONE_INDEX_NAME, extract_metadata_from_text
import utils

sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
from entity_extraction import extract_entities_for_document

router = APIRouter()


@router.post("/ingest-google-docs", response_model=DocumentResponse)
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


@router.post("/ingest-google-search-history")
async def ingest_google_search_history_endpoint(request: GoogleSearchHistoryRequest):
    """Ingest Google Search History from a Google Takeout JSON file"""
    try:
        print(f"[SEARCH HISTORY INGEST] Starting ingestion for user {request.user_id}")
        
        # Import and use the fetch_google_search_history script
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
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
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
        
        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found")
        
        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        
        # Process and ingest the search entries
        print(f"[SEARCH HISTORY INGEST] Processing search entries...")
        
        if not utils.embedding_model:
            utils.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
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
            
            embedding = utils.embedding_model.encode(text).tolist()
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


def fetch_and_ingest_google_docs():
    """Fetch Google Docs and ingest them into the database"""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        
        creds = None
        token_file = CREDENTIALS_DIR / "token.pickle"
        
        if token_file.exists():
            with open(token_file, 'rb') as token:
                creds = pkl.load(token)
        
        if not creds or not creds.valid:
            from google.auth.transport.requests import Request
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                client_secrets_file = CREDENTIALS_DIR / "client_secret.json"
                if not client_secrets_file.exists():
                    raise FileNotFoundError("OAuth credentials not found")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secrets_file),
                    ['https://www.googleapis.com/auth/drive.readonly']
                )
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'wb') as token:
                pkl.dump(creds, token)
        
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
        if not utils.embedding_model:
            utils.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not utils.pinecone_index:
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
            utils.pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        
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
            
            embedding = utils.embedding_model.encode(clean_text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            utils.pinecone_index.upsert(vectors=batch)
        
        return {"message": f"Successfully ingested {len(downloaded_files)} Google Docs", "count": len(downloaded_files)}
    
    except Exception as e:
        raise Exception(f"Error fetching Google Docs: {str(e)}")
