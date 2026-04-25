import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException

from models import SaveChatRequest, GetChatRequest
import utils

router = APIRouter()


@router.post("/chat-history/save")
async def save_chat_history(request: SaveChatRequest):
    """Save chat history to Supabase"""
    if not utils.supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        # Delete existing chat history for this user and session
        utils.supabase.table("chat_history").delete().eq("user_id", request.user_id).eq("session_id", request.session_id).execute()

        # Insert new chat messages with session_id
        for message in request.messages:
            utils.supabase.table("chat_history").insert({
                "user_id": request.user_id,
                "session_id": request.session_id,
                "role": message.role,
                "content": message.content,
                "sources": message.sources
            }).execute()

        return {"message": "Chat history saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-history/load")
async def load_chat_history(request: GetChatRequest):
    """Load chat history from Supabase"""
    if not utils.supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        response = utils.supabase.table("chat_history").select("*").eq("user_id", request.user_id).eq("session_id", request.session_id).order("created_at").execute()

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


@router.get("/sessions/{user_id}")
async def get_sessions(user_id: str):
    """Get all sessions for a user with message counts"""
    if not utils.supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        # Use SQL aggregation to get sessions with message counts
        response = utils.supabase.rpc("get_user_sessions", {"user_uuid": user_id}).execute()
        
        if response.data:
            return {"sessions": response.data}
        else:
            # Fallback: fetch all messages and group manually if RPC doesn't exist
            all_messages = utils.supabase.table("chat_history").select("session_id, created_at, content").eq("user_id", user_id).not_.is_("session_id", "null").order("created_at", desc=True).execute()
            
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
        print(f"Error in get_sessions: {e}")
        # Fallback to manual grouping if RPC fails
        try:
            all_messages = utils.supabase.table("chat_history").select("session_id, created_at, content").eq("user_id", user_id).not_.is_("session_id", "null").order("created_at", desc=True).execute()
            
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
            print(f"Fallback error: {fallback_error}")
            raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")
