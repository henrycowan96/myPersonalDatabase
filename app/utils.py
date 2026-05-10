import os
import sys
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone import Pinecone, ServerlessSpec
from supabase import create_client, Client
import tiktoken

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
insights_engine = None


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


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in text using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: approximate 4 chars per token
        return len(text) // 4


def summarize_conversation(conversation_history: list, max_tokens: int = 2000, keep_recent: int = 3) -> dict:
    """
    Summarize older conversation turns if total tokens exceed threshold.
    
    Args:
        conversation_history: List of {query, answer} dicts
        max_tokens: Maximum tokens before summarization triggers
        keep_recent: Number of recent turns to keep in full detail
    
    Returns:
        dict with 'summary' (str) and 'recent_turns' (list)
    """
    if not conversation_history or len(conversation_history) <= keep_recent:
        return {"summary": None, "recent_turns": conversation_history}
    
    # Calculate total tokens
    full_text = "\n".join([
        f"Q: {turn.get('query', '')}\nA: {turn.get('answer', '')}"
        for turn in conversation_history
    ])
    total_tokens = count_tokens(full_text)
    
    if total_tokens <= max_tokens:
        return {"summary": None, "recent_turns": conversation_history}
    
    # Split into older turns and recent turns
    older_turns = conversation_history[:-keep_recent]
    recent_turns = conversation_history[-keep_recent:]
    
    # Build conversation text for summarization
    conversation_text = "\n\n".join([
        f"User: {turn.get('query', '')}\nAssistant: {turn.get('answer', '')}"
        for turn in older_turns
    ])
    
    # Generate summary using LLM
    if llm:
        try:
            summary_prompt = f"""Summarize the following conversation between a user and an AI assistant about the user's personal data and life. Focus on:
- Key topics discussed
- Important information revealed
- Any decisions or conclusions reached

Keep the summary concise (2-3 paragraphs) and preserve important context.

Conversation:
{conversation_text}

Summary:"""
            
            summary = llm.invoke(summary_prompt).content
            return {"summary": summary, "recent_turns": recent_turns}
        except Exception as e:
            print(f"Error generating conversation summary: {e}")
            # Fallback: return truncated recent turns
            return {"summary": None, "recent_turns": recent_turns}
    else:
        # No LLM available, just keep recent turns
        return {"summary": None, "recent_turns": recent_turns}


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash of content for deduplication"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def create_sync_job(user_id: str, source_type: str) -> str:
    """Create a new sync job and return its ID"""
    if not supabase:
        raise Exception("Supabase not initialized")
    
    job_data = {
        "user_id": user_id,
        "source_type": source_type,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "items_processed": 0,
        "items_created": 0,
        "items_updated": 0,
        "items_skipped": 0,
        "items_deleted": 0,
        "source_ids_seen": []
    }
    
    result = supabase.table("sync_jobs").insert(job_data).execute()
    return result.data[0]["id"]


def update_sync_job(sync_job_id: str, status: str, **kwargs):
    """Update sync job with current status and metrics"""
    if not supabase:
        return
    
    update_data = {
        "status": status,
        **kwargs
    }
    
    if status == "completed" or status == "failed":
        update_data["completed_at"] = datetime.now().isoformat()
    
    supabase.table("sync_jobs").update(update_data).eq("id", sync_job_id).execute()


def check_chunk_exists(user_id: str, source_type: str, chunk_hash: str) -> Optional[Dict]:
    """Check if a chunk with this hash already exists for this user and source"""
    if not supabase:
        return None
    
    result = supabase.table("ingested_chunks").select("*").eq("user_id", user_id).eq("source_type", source_type).eq("chunk_hash", chunk_hash).eq("is_deleted", False).execute()
    
    if result.data:
        return result.data[0]
    return None


def record_ingested_chunk(user_id: str, source_type: str, source_id: Optional[str], 
                          chunk_hash: str, pinecone_vector_id: str, 
                          content_preview: str, metadata: Dict, sync_job_id: str) -> str:
    """Record a newly ingested chunk in the tracking table"""
    if not supabase:
        return pinecone_vector_id  # Fallback if Supabase not available
    
    chunk_data = {
        "user_id": user_id,
        "source_type": source_type,
        "source_id": source_id,
        "chunk_hash": chunk_hash,
        "pinecone_vector_id": pinecone_vector_id,
        "content_preview": content_preview[:200] if content_preview else "",
        "metadata": metadata,
        "ingested_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat(),
        "is_deleted": False,
        "sync_job_id": sync_job_id
    }
    
    result = supabase.table("ingested_chunks").insert(chunk_data).execute()
    return result.data[0]["id"]


def update_chunk_last_seen(chunk_id: str, sync_job_id: str):
    """Update last_seen_at for an existing chunk (mark it as still present in source)"""
    if not supabase:
        return
    
    supabase.table("ingested_chunks").update({
        "last_seen_at": datetime.now().isoformat(),
        "sync_job_id": sync_job_id
    }).eq("id", chunk_id).execute()


def mark_stale_data(user_id: str, source_type: str, current_source_ids: List[str], sync_job_id: str) -> int:
    """Mark chunks not seen in current sync as deleted"""
    if not supabase:
        return 0
    
    # Call the PostgreSQL function to mark stale data
    result = supabase.rpc("mark_stale_data", {
        "user_id_param": user_id,
        "source_type_param": source_type,
        "current_source_ids": current_source_ids,
        "sync_job_id_param": sync_job_id
    }).execute()
    
    return result.data if result.data else 0


def get_deleted_vectors_for_cleanup(user_id: str, older_than_days: int = 7) -> List[Dict]:
    """Get vectors marked for deletion that are older than specified days"""
    if not supabase:
        return []
    
    result = supabase.rpc("get_deleted_vectors_for_cleanup", {
        "user_id_param": user_id,
        "older_than_days": older_than_days
    }).execute()
    
    return result.data if result.data else []


def delete_vector_from_pinecone(pinecone_index, vector_id: str):
    """Delete a vector from Pinecone"""
    try:
        pinecone_index.delete(ids=[vector_id])
        return True
    except Exception as e:
        print(f"Error deleting vector {vector_id} from Pinecone: {e}")
        return False


def cleanup_deleted_vectors(user_id: str, pinecone_index, older_than_days: int = 7) -> Dict[str, int]:
    """Clean up soft-deleted vectors from Pinecone and mark as cleaned"""
    deleted_vectors = get_deleted_vectors_for_cleanup(user_id, older_than_days)
    
    if not deleted:
        return {"total": 0, "deleted": 0, "failed": 0}
    
    deleted_count = 0
    failed_count = 0
    
    for vector_info in deleted_vectors:
        chunk_id = vector_info["chunk_id"]
        pinecone_vector_id = vector_info["pinecone_vector_id"]
        
        if delete_vector_from_pinecone(pinecone_index, pinecone_vector_id):
            # Mark the chunk as fully cleaned (you could add a cleaned_at column)
            deleted_count += 1
        else:
            failed_count += 1
    
    return {
        "total": len(deleted_vectors),
        "deleted": deleted_count,
        "failed": failed_count
    }


def initialize_services():
    """Initialize Pinecone, LLM, Supabase, and Insights Engine"""
    global pinecone_index, embedding_model, reranker, llm, supabase, insights_engine
    
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
                model="openai/gpt-oss-20b:free",
                temperature=0.2,
                openai_api_key=os.getenv("OPEN_ROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1"
            )
            print("OpenRouter LLM initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize OpenRouter LLM: {e}")
            print("Make sure OPEN_ROUTER_API_KEY is set in .env file")
        
        # Initialize Insights Engine
        try:
            from app.insights_engine import InsightsEngine
            insights_engine = InsightsEngine()
            print("Insights Engine initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize Insights Engine: {e}")
        
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
