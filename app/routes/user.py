import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
from fastapi import APIRouter, HTTPException
from pinecone import Pinecone, ServerlessSpec

from models import CreateUserDatabaseRequest, UploadDocumentsRequest, ResetDatabaseRequest, DocumentResponse
import utils

router = APIRouter()


@router.post("/create-user-database")
async def create_user_database(request: CreateUserDatabaseRequest):
    """Create a user-specific vector database in Pinecone"""
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="PINECONE_API_KEY not found"
        )
    
    try:
        # Check if user already has a database created
        if utils.supabase:
            existing = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
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
        if utils.supabase:
            # Insert new settings
            utils.supabase.table("user_settings").insert({
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


@router.get("/user-settings/{user_id}")
async def get_user_settings(user_id: str):
    """Get user settings including setup progress"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")
    
    try:
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        
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


@router.post("/save-permissions")
async def save_permissions(request: UploadDocumentsRequest):
    """Save user permissions without uploading documents"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")

    try:
        update_data = {
            "permissions": request.permissions,
        }

        # Only update setup_step if provided
        if request.setup_step is not None:
            update_data["setup_step"] = request.setup_step

        utils.supabase.table("user_settings").update(update_data).eq("user_id", request.user_id).execute()

        return {"message": "Permissions saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-user-database")
async def reset_user_database(request: ResetDatabaseRequest):
    """Delete user's Pinecone index, clear Supabase data, and recreate database"""
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found")
    
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")
    
    try:
        # Get user settings to find the Pinecone index name
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
        
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
                # Wait for index deletion to complete
                while pinecone_index_name in [index.name for index in pc.list_indexes()]:
                    time.sleep(1)
                print(f"[RESET] Pinecone index deleted successfully")
        
        # Clear user data in Supabase using the reset function
        print(f"[RESET] Clearing user data in Supabase")
        
        # Call the reset_user_database function
        utils.supabase.rpc("reset_user_database", {"target_user_id": request.user_id}).execute()
        
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
        utils.supabase.table("user_settings").update({
            "pinecone_index": new_index_name,
            "setup_step": 2
        }).eq("user_id", request.user_id).execute()
        
        return {"message": "Database reset successfully", "new_index_name": new_index_name}
    
    except Exception as e:
        print(f"[RESET] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
