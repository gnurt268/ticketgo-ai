"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Chat message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Single chat message"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")
    user_id: Optional[int] = Field(None, description="User ID if logged in")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Làm sao để mua vé?",
                "session_id": "sess_abc123",
                "user_id": 1
            }
        }


class SourceDocument(BaseModel):
    """Source document used for RAG response"""
    content: str
    source: str
    relevance_score: Optional[float] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    answer: str
    session_id: str
    sources: List[SourceDocument] = []
    suggested_questions: List[str] = []
    processing_time_ms: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Để mua vé trên TicketGo, bạn có thể...",
                "session_id": "sess_abc123",
                "sources": [
                    {"content": "Hướng dẫn mua vé...", "source": "FAQ", "relevance_score": 0.95}
                ],
                "suggested_questions": [
                    "Thanh toán bằng những hình thức nào?",
                    "Làm sao để kiểm tra vé đã mua?"
                ],
                "processing_time_ms": 250
            }
        }


class KnowledgeBaseItem(BaseModel):
    """Knowledge base document"""
    id: Optional[int] = None
    title: str
    content: str
    category: str = Field(..., description="Category: faq, policy, guide, event")
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeBaseCreate(BaseModel):
    """Create knowledge base item"""
    title: str
    content: str
    category: str
    metadata: Optional[dict] = None


class EventSyncRequest(BaseModel):
    """Request to sync events from main API"""
    event_ids: Optional[List[int]] = Field(None, description="Specific event IDs to sync, or None for all")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str
    gemini: str


class ChatSession(BaseModel):
    """Chat session info"""
    session_id: str
    user_id: Optional[int] = None
    started_at: datetime
    last_message_at: datetime
    message_count: int


class ChatHistoryResponse(BaseModel):
    """Chat history for a session"""
    session_id: str
    messages: List[ChatMessage]
    total_messages: int
