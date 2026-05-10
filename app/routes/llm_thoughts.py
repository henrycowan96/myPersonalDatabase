from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.llm_service import LLMService
import utils

router = APIRouter()

class LLMThought(BaseModel):
    id: str
    thought_type: str
    title: str
    content: str
    prompt_used: str
    generated_at: str

class LLMThoughtsRequest(BaseModel):
    user_id: str
    insights: List[dict]

class LLMThoughtsResponse(BaseModel):
    thoughts: List[LLMThought]

@router.post("/llm-thoughts", response_model=LLMThoughtsResponse)
async def generate_llm_thoughts(
    request: LLMThoughtsRequest
):
    """Generate LLM thoughts based on user insights"""
    try:
        llm_service = LLMService()
        
        # 5 different prompts for generating thoughts
        prompts = [
            {
                "type": "summary",
                "title": "Life Summary",
                "prompt": f"Based on these insights about the user's life, provide a comprehensive summary of their current life situation, patterns, and overall state. Focus on the most important themes and patterns. Insights: {request.insights}"
            },
            {
                "type": "recommendations", 
                "title": "Actionable Recommendations",
                "prompt": f"Based on these insights, provide 3-5 specific, actionable recommendations that could improve the user's life. Make them practical and realistic. Insights: {request.insights}"
            },
            {
                "type": "patterns",
                "title": "Emerging Patterns", 
                "prompt": f"Analyze these insights and identify the most significant patterns, trends, or recurring themes in the user's life. What do these patterns suggest about their current life trajectory? Insights: {request.insights}"
            },
            {
                "type": "opportunities",
                "title": "Growth Opportunities",
                "prompt": f"Based on these insights, what are the biggest opportunities for personal growth, development, or positive change in the user's life? Focus on areas with high potential impact. Insights: {request.insights}"
            },
            {
                "type": "reflection",
                "title": "Deep Reflection",
                "prompt": f"Provide a thoughtful, philosophical reflection on what these insights reveal about the user's life journey, values, and deeper meaning. Be insightful and encouraging. Insights: {request.insights}"
            }
        ]
        
        thoughts = []
        from datetime import datetime
        
        for prompt_data in prompts:
            try:
                response = await llm_service.generate_response(prompt_data["prompt"])
                
                thought = LLMThought(
                    id=f"{prompt_data['type']}_{datetime.now().timestamp()}",
                    thought_type=prompt_data["type"],
                    title=prompt_data["title"],
                    content=response,
                    prompt_used=prompt_data["prompt"],
                    generated_at=datetime.now().isoformat()
                )
                thoughts.append(thought)
                
            except Exception as e:
                # Continue with other prompts if one fails
                print(f"Error generating thought for {prompt_data['type']}: {e}")
                continue
        
        return LLMThoughtsResponse(thoughts=thoughts)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate LLM thoughts: {str(e)}")


@router.post("/llm-thoughts/save")
async def save_thoughts(request: LLMThoughtsRequest):
    """Save LLM thoughts to Supabase for persistent storage across sessions"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        saved_count = 0
        for thought in request.insights:
            record = {
                'user_id': request.user_id,
                'thought_id': thought.get('id'),
                'thought_type': thought.get('thought_type'),
                'title': thought.get('title'),
                'content': thought.get('content'),
                'prompt_used': thought.get('prompt_used', ''),
                'generated_at': thought.get('generated_at'),
            }
            result = utils.supabase.table("llm_thoughts").upsert(
                record,
                on_conflict="user_id,thought_id"
            ).execute()
            if result.data:
                saved_count += 1
        
        return {
            "status": "success",
            "message": f"Saved {saved_count} thoughts",
            "count": saved_count
        }
    
    except Exception as e:
        print(f"[THOUGHTS SAVE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-thoughts/load/{user_id}")
async def load_thoughts(user_id: str):
    """Load persisted LLM thoughts from Supabase"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        response = utils.supabase.table("llm_thoughts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        thoughts = []
        for row in response.data:
            thoughts.append({
                'id': row['thought_id'],
                'thought_type': row['thought_type'],
                'title': row['title'],
                'content': row['content'],
                'prompt_used': row.get('prompt_used', ''),
                'generated_at': row['generated_at'],
            })
        
        return {
            "thoughts": thoughts,
            "count": len(thoughts)
        }
    
    except Exception as e:
        print(f"[THOUGHTS LOAD] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
