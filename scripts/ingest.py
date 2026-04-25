import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import pickle
import uuid
from entity_extraction import extract_entities_for_document

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
PROCESSED_CHUNKS_DIR = Path(__file__).parent.parent / "data" / "processed_chunks"
EMBEDDINGS_DIR = Path(__file__).parent.parent / "embeddings"
PINECONE_INDEX_NAME = "personal-database"

# Create directories if they don't exist
PROCESSED_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

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

def load_documents():
    """Load documents from raw_docs directory"""
    documents = []
    
    # Load PDF files
    pdf_loader = DirectoryLoader(
        str(RAW_DOCS_DIR),
        glob="**/*.pdf",
        loader_cls=PyPDFLoader
    )
    documents.extend(pdf_loader.load())
    
    # Load text files
    text_loader = DirectoryLoader(
        str(RAW_DOCS_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader
    )
    documents.extend(text_loader.load())
    
    # Load markdown files
    md_loader = DirectoryLoader(
        str(RAW_DOCS_DIR),
        glob="**/*.md",
        loader_cls=TextLoader
    )
    documents.extend(md_loader.load())
    
    print(f"Loaded {len(documents)} documents from {RAW_DOCS_DIR}")
    return documents

def split_documents(documents, chunk_size=1000, chunk_overlap=200):
    """Split documents into chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")
    
    # Save chunks to disk
    chunks_path = PROCESSED_CHUNKS_DIR / "chunks.pkl"
    with open(chunks_path, 'wb') as f:
        pickle.dump(chunks, f)
    
    print(f"Saved chunks to {chunks_path}")
    return chunks

def create_embeddings(chunks):
    """Create embeddings and store in Pinecone"""
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    
    # Use sentence-transformers directly
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    # Initialize Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Check if index exists
    existing_indexes = [index.name for index in pc.list_indexes()]
    if PINECONE_INDEX_NAME in existing_indexes:
        # Check dimension
        index_info = pc.describe_index(PINECONE_INDEX_NAME)
        if index_info.dimension != 384:
            print(f"Existing index has dimension {index_info.dimension}, deleting and recreating...")
            pc.delete_index(PINECONE_INDEX_NAME)
            # Wait for deletion
            import time
            while PINECONE_INDEX_NAME in [index.name for index in pc.list_indexes()]:
                time.sleep(1)
            print(f"Creating new Pinecone index '{PINECONE_INDEX_NAME}'...")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=384,  # all-MiniLM-L6-v2 embedding dimension
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            # Wait for index to be ready
            while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                time.sleep(1)
    else:
        print(f"Creating new Pinecone index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=384,  # all-MiniLM-L6-v2 embedding dimension
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        # Wait for index to be ready
        import time
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
            time.sleep(1)
    
    # Get the index
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Create embeddings and upsert to Pinecone
    vectors = []
    for i, chunk in enumerate(chunks):
        text = chunk.page_content
        
        # Extract metadata from text if present
        extracted_metadata, clean_text = extract_metadata_from_text(text)
        
        # Extract entities for relationship tracking
        entity_data = extract_entities_for_document(clean_text, extracted_metadata)
        
        # Build metadata dict
        metadata = {
            'text': clean_text,
            'source': chunk.metadata.get('source', ''),
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
        
        embedding = model.encode(clean_text).tolist()
        vectors.append({
            'id': str(uuid.uuid4()),
            'values': embedding,
            'metadata': metadata
        })
    
    # Upsert in batches
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch)
        print(f"Upserted batch {i//batch_size + 1}/{(len(vectors) + batch_size - 1)//batch_size}")
    
    print(f"Created embeddings and stored {len(vectors)} vectors in Pinecone index '{PINECONE_INDEX_NAME}'")
    return index

def main():
    print("Starting document ingestion...")
    
    # Load documents
    documents = load_documents()
    
    if not documents:
        print("No documents found. Please add documents to data/raw_docs/")
        return
    
    # Split documents
    chunks = split_documents(documents)
    
    # Create embeddings
    vectorstore = create_embeddings(chunks)
    
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
