import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone import Pinecone, ServerlessSpec
from supabase import create_client, Client

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "scripts"))

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

# Global variables for Pinecone and LLM
pinecone_index = None
embedding_model = None
reranker = None
llm = None
supabase: Client = None


def extract_metadata_from_text(text):
    """Extract metadata header from text if present"""
    import json
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
