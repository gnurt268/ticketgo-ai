"""
Chat API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db import get_db, ChatStore
from app.services import rag_service, knowledge_service
from app.models import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessage,
    MessageRole,
    KnowledgeBaseCreate,
    EventSyncRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message to the AI chatbot
    
    - **message**: User's question (required)
    - **session_id**: Session ID for conversation continuity (optional, auto-generated if not provided)
    - **user_id**: User ID if logged in (optional)
    """
    try:
        response = await rag_service.process_chat(request, db)
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý tin nhắn: {str(e)}"
        )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get chat history for a session"""
    try:
        messages = rag_service.get_chat_history(db, session_id)
        
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=len(messages)
        )
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Clear chat history for a session"""
    try:
        # Delete messages
        from app.db.vector_store import ChatMessageModel, ChatSessionModel
        
        db.query(ChatMessageModel).filter(
            ChatMessageModel.session_id == session_id
        ).delete()
        
        db.query(ChatSessionModel).filter(
            ChatSessionModel.session_id == session_id
        ).delete()
        
        db.commit()
        
        return {"message": "Chat history cleared", "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# === Knowledge Base Management ===

knowledge_router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@knowledge_router.get("")
async def list_knowledge(
    category: str = None,
    db: Session = Depends(get_db)
):
    """List all knowledge base items"""
    items = knowledge_service.get_all_knowledge(db, category)
    
    return {
        "total": len(items),
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content[:200] + "..." if len(item.content) > 200 else item.content,
                "category": item.category,
                "created_at": item.created_at,
            }
            for item in items
        ]
    }


@knowledge_router.post("")
async def add_knowledge(
    item: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """Add a new knowledge base item"""
    try:
        doc_id = await rag_service.add_knowledge(
            db,
            title=item.title,
            content=item.content,
            category=item.category,
            metadata=item.metadata
        )
        
        return {
            "message": "Knowledge added successfully",
            "id": doc_id
        }
        
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@knowledge_router.delete("/{doc_id}")
async def delete_knowledge(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Delete a knowledge base item"""
    success = knowledge_service.delete_knowledge(db, doc_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {"message": "Knowledge deleted successfully"}


@knowledge_router.post("/seed")
async def seed_knowledge(db: Session = Depends(get_db)):
    """Seed default FAQ and policies to knowledge base"""
    try:
        count = await knowledge_service.seed_default_knowledge(db)
        return {
            "message": f"Seeded {count} knowledge items",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error seeding knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@knowledge_router.post("/sync-events")
async def sync_events(
    request: EventSyncRequest = None,
    db: Session = Depends(get_db)
):
    """Sync events from main API to knowledge base"""
    try:
        event_ids = request.event_ids if request else None
        count = await knowledge_service.sync_events_from_main_api(db, event_ids)
        
        return {
            "message": f"Synced {count} events",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error syncing events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
