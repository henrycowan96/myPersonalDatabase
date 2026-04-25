import os
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import DocumentResponse, SpotifyRequest
import utils
from data_processor import process_and_ingest_data

router = APIRouter()


@router.post("/ingest-spotify")
async def ingest_spotify_endpoint(request: SpotifyRequest, background_tasks: BackgroundTasks):
    """Fetch and ingest Spotify data for a user"""
    try:
        print(f"[SPOTIFY INGEST] Starting Spotify ingestion for user {request.user_id}")
        
        # Fetch Spotify data
        from ..services.spotify_service import fetch_spotify_data
        saved_files = await fetch_spotify_data(request.user_id)
        
        if not saved_files:
            return DocumentResponse(
                message="No Spotify data was fetched",
                document_count=0
            )
        
        # Get user's Pinecone index
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
        
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
