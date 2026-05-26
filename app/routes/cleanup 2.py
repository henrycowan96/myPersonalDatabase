import os
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pinecone import Pinecone

import utils

router = APIRouter()


@router.post("/cleanup-deleted-vectors")
async def cleanup_deleted_vectors_endpoint(user_id: str, older_than_days: Optional[int] = 7):
    """Clean up soft-deleted vectors from Pinecone that are older than specified days"""
    try:
        print(f"[CLEANUP] Starting cleanup for user {user_id}, older than {older_than_days} days")
        
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        if not utils.pinecone_index:
            # Initialize Pinecone if not already initialized
            if not os.getenv("PINECONE_API_KEY"):
                raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found")
            
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            utils.pinecone_index = pc.Index("personal-database")
            print(f"[CLEANUP] Initialized Pinecone index")
        
        # Run cleanup
        result = utils.cleanup_deleted_vectors(user_id, utils.pinecone_index, older_than_days)
        
        print(f"[CLEANUP] Cleanup completed: {result}")
        
        return {
            "message": "Cleanup completed successfully",
            "result": result
        }
    
    except Exception as e:
        print(f"[CLEANUP] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-jobs")
async def get_sync_jobs(user_id: str, source_type: Optional[str] = None, limit: int = 50):
    """Get sync job history for a user"""
    try:
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        query = utils.supabase.table("sync_jobs").select("*").eq("user_id", user_id)
        
        if source_type:
            query = query.eq("source_type", source_type)
        
        query = query.order("started_at", desc=True).limit(limit)
        result = query.execute()
        
        return {
            "sync_jobs": result.data,
            "count": len(result.data)
        }
    
    except Exception as e:
        print(f"[SYNC JOBS] ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingested-chunks")
async def get_ingested_chunks(user_id: str, source_type: Optional[str] = None, is_deleted: Optional[bool] = None, limit: int = 100):
    """Get ingested chunks for a user with optional filters"""
    try:
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        query = utils.supabase.table("ingested_chunks").select("*").eq("user_id", user_id)
        
        if source_type:
            query = query.eq("source_type", source_type)
        
        if is_deleted is not None:
            query = query.eq("is_deleted", is_deleted)
        
        query = query.order("ingested_at", desc=True).limit(limit)
        result = query.execute()
        
        return {
            "chunks": result.data,
            "count": len(result.data)
        }
    
    except Exception as e:
        print(f"[INGESTED CHUNKS] ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-source-data")
async def clear_source_data(user_id: str, source_type: str):
    """Clear all data for a specific source type (ingested_chunks, sync_jobs, facts, etc.)"""
    try:
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        print(f"[CLEAR SOURCE] Clearing data for user {user_id}, source_type {source_type}")
        
        # Call the clear_source_data function
        result = utils.supabase.rpc("clear_source_data", {
            "target_user_id": user_id,
            "source_type_param": source_type
        }).execute()
        
        print(f"[CLEAR SOURCE] Data cleared successfully")
        
        return {
            "message": "Source data cleared successfully",
            "result": result.data
        }
    
    except Exception as e:
        print(f"[CLEAR SOURCE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
