import os
import sys
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
import shutil
import pickle
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import DocumentResponse
from utils import RAW_DOCS_DIR, PROCESSED_CHUNKS_DIR, PINECONE_INDEX_NAME, extract_metadata_from_text
import utils

sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
from entity_extraction import extract_entities_for_document

router = APIRouter()


@router.post("/ingest", response_model=DocumentResponse)
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


@router.get("/documents")
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
