from typing import List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_history: Optional[List[dict]] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]


class DocumentResponse(BaseModel):
    message: str
    document_count: int


class RelationshipQueryRequest(BaseModel):
    entity_id: Optional[str] = None
    topic: Optional[str] = None
    source: Optional[str] = None
    question: Optional[str] = None
    user_id: Optional[str] = None


class RelationshipQueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    filters_applied: dict


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: Optional[List[dict]] = None
    is_summary: Optional[bool] = False


class SaveChatRequest(BaseModel):
    user_id: str
    session_id: str
    messages: List[ChatMessage]


class GetChatRequest(BaseModel):
    user_id: str
    session_id: str


class CreateUserDatabaseRequest(BaseModel):
    user_id: str
    apple_calendar_email: Optional[str] = None
    apple_calendar_password: Optional[str] = None


class UploadDocumentsRequest(BaseModel):
    user_id: str
    permissions: dict
    setup_step: Optional[int] = None
    apple_calendar_email: Optional[str] = None
    apple_calendar_password: Optional[str] = None


class AppleMusicRequest(BaseModel):
    user_id: str
    music_user_token: Optional[str] = None
    key_id: Optional[str] = None
    team_id: Optional[str] = None
    private_key: Optional[str] = None


class GoogleSearchHistoryRequest(BaseModel):
    user_id: str
    json_path: str


class SpotifyRequest(BaseModel):
    user_id: str


class ResetDatabaseRequest(BaseModel):
    user_id: str


class InsightItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    significance_score: float
    sources: List[dict]
    detected_at: str
    time_context: dict
    entities: List[str]
    actionable: bool


class ThoughtItem(BaseModel):
    id: str
    thought_type: str
    title: str
    content: str
    prompt_used: str
    generated_at: str


class SaveInsightsRequest(BaseModel):
    user_id: str
    insights: List[InsightItem]


class SaveThoughtsRequest(BaseModel):
    user_id: str
    thoughts: List[ThoughtItem]


class GetInsightsRequest(BaseModel):
    user_id: str
    limit: Optional[int] = 20


class GetThoughtsRequest(BaseModel):
    user_id: str
