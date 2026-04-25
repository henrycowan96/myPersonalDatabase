from typing import List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None


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
