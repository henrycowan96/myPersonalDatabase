from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class ChatContextRequest(BaseModel):
    user_id: str
    content_type: str  # 'insight' or 'thought'
    content_id: str
    title: str
    content: str

class ChatContextResponse(BaseModel):
    prompt: str
    success: bool

@router.post("/chat-context", response_model=ChatContextResponse)
async def create_chat_context(request: ChatContextRequest):
    """
    Create a chat context prompt from insight or thought content
    """
    try:
        # Create contextual prompt for LLM
        if request.content_type == "insight":
            prompt = f"""I want to discuss this insight with you:

Title: {request.title}
Category: {request.content_id}
Description: {request.content}

Please help me understand this better, provide additional context, or discuss what this might mean for my life. Feel free to ask clarifying questions or suggest related topics we could explore."""        
        elif request.content_type == "thought":
            prompt = f"""I want to discuss this AI-generated thought with you:

Title: {request.title}
Type: {request.content_id}
Content: {request.content}

Please help me understand this analysis, provide additional context, or discuss what this might reveal about my patterns and behaviors. Feel free to ask clarifying questions or explore related topics we could explore."""        
        else:
            raise HTTPException(status_code=400, detail="Invalid content_type")
        
        return ChatContextResponse(
            prompt=prompt,
            success=True
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
