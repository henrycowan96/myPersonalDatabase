import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException

from models import SaveChatRequest, GetChatRequest
import utils

router = APIRouter()


@router.post("/chat-history/save")
async def save_chat_history(request: SaveChatRequest):
    """Save chat history to Supabase with optional summary caching"""
    if not utils.supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase not initialized. Please check configuration."
        )

    try:
        # Delete existing chat history for this user and session
        utils.supabase.table("chat_history").delete().eq("user_id", request.user_id).eq("session_id", request.session_id).execute()

        # Convert conversation history to turn format for summarization
        conversation_turns = []
        for i, msg in enumerate(request.messages):
            if msg.role == "user" and i + 1 < len(request.messages) and request.messages[i + 1].role == "assistant":
                conversation_turns.append({
                    "query": msg.content,
                    "answer": request.messages[i + 1].content
                })

        # Check if we should generate and cache a summary
        summary = None
        if conversation_turns:
            summary_result = utils.summarize_conversation(conversation_turns, max_tokens=1500, keep_recent=2)
            if summary_result["summary"]:
                summary = summary_result["summary"]
                # Insert summary as a special system message
                utils.supabase.table("chat_history").insert({
                    "user_id": request.user_id,
                    "session_id": request.session_id,
                    "role": "system",
                    "content": f"CONVERSATION SUMMARY: {summary}",
                    "sources": None,
                    "is_summary": True
                }).execute()

        # Insert new chat messages with session_id
        for message in request.messages:
            utils.supabase.table("chat_history").insert({
                "user_id": request.user_id,
                "session_id": request.session_id,
                "role": message.role,
                "content": message.content,
                "sources": message.sources,
                "is_summary": getattr(message, 'is_summary', False)
            }).execute()

        return {"message": "Chat history saved successfully", "summary_cached": summary is not None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-history/load")
async def load_chat_history(request: GetChatRequest):
    """Load chat history from Supabase, excluding cached summaries"""
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
            if not msg.get("is_summary", False)  # Exclude cached summaries from regular message list
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
        # Use SQL aggregation to get sessions with message counts in parallel
        import asyncio
        
        async def fetch_sessions_rpc():
            return utils.supabase.rpc("get_user_sessions", {"user_uuid": user_id}).execute()
        
        async def fetch_sessions_fallback():
            return utils.supabase.table("chat_history").select("session_id, created_at, content").eq("user_id", user_id).not_.is_("session_id", "null").order("created_at", desc=True).execute()
        
        # Try RPC first, fallback to manual grouping if needed
        rpc_task = asyncio.create_task(fetch_sessions_rpc())
        rpc_response = await rpc_task
        
        if rpc_response.data:
            return {"sessions": rpc_response.data}
        else:
            # Fallback: fetch all messages and group manually in parallel
            fallback_task = asyncio.create_task(fetch_sessions_fallback())
            all_messages = await fallback_task
            
            # Process messages in parallel batches
            session_map = {}
            
            async def process_message_batch(messages_batch):
                local_session_map = {}
                for msg in messages_batch:
                    session_id = msg.get("session_id")
                    if not session_id:
                        continue
                    
                    if session_id not in local_session_map:
                        local_session_map[session_id] = {
                            "session_id": session_id,
                            "created_at": msg.get("created_at"),
                            "message_count": 0,
                            "last_message": msg.get("content", "")[:100] if msg.get("content") else ""
                        }
                    local_session_map[session_id]["message_count"] += 1
                return local_session_map
            
            # Split into batches for parallel processing
            batch_size = 50
            batches = [all_messages.data[i:i + batch_size] for i in range(0, len(all_messages.data), batch_size)]
            
            if batches:
                tasks = [asyncio.create_task(process_message_batch(batch)) for batch in batches]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Merge results
                for result in batch_results:
                    if isinstance(result, Exception):
                        print(f"Error processing message batch: {result}")
                    else:
                        session_map.update(result)
            
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
