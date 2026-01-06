"""
RAG (Retrieval Augmented Generation) Service
Core logic for the AI chatbot
"""
import logging
import uuid
import time
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db import VectorStore, ChatStore, get_db_context
from app.services.gemini_service import gemini_service
from app.models import (
    ChatRequest, 
    ChatResponse, 
    SourceDocument, 
    ChatMessage, 
    MessageRole
)

logger = logging.getLogger(__name__)


class RAGService:
    """RAG Pipeline for TicketGo Chatbot"""
    
    def __init__(self):
        self.gemini = gemini_service
        self.max_context_length = 4000  # Max characters for context
        self.similarity_threshold = 0.5  # Minimum similarity score
    
    async def process_chat(
        self,
        request: ChatRequest,
        db: Session
    ) -> ChatResponse:
        """
        Process a chat request through the RAG pipeline
        
        Steps:
        1. Get or create session
        2. Retrieve relevant documents
        3. Build context
        4. Generate response
        5. Save to history
        6. Generate suggestions
        """
        start_time = time.time()
        
        # 1. Get or create session
        session_id = request.session_id or str(uuid.uuid4())
        session = ChatStore.get_session(db, session_id)
        
        if not session:
            session = ChatStore.create_session(
                db, 
                session_id, 
                request.user_id
            )
            logger.info(f"Created new session: {session_id}")
        
        # 2. Get chat history
        history_messages = ChatStore.get_chat_history(db, session_id, limit=6)
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages
        ]
        
        # 3. Retrieve relevant documents
        relevant_docs = await self._retrieve_documents(
            db, 
            request.message,
            limit=5
        )
        
        # 4. Build context from retrieved documents
        context, sources = self._build_context(relevant_docs)
        
        # 5. Generate response
        answer = await self.gemini.generate_response(
            user_message=request.message,
            context=context,
            chat_history=chat_history
        )
        
        # 6. Save messages to history
        ChatStore.add_message(db, session_id, "user", request.message)
        ChatStore.add_message(
            db, 
            session_id, 
            "assistant", 
            answer,
            sources=[s.model_dump() for s in sources]
        )
        
        # 7. Generate suggested questions
        suggestions = await self.gemini.generate_suggested_questions(
            request.message,
            answer
        )
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            answer=answer,
            session_id=session_id,
            sources=sources,
            suggested_questions=suggestions,
            processing_time_ms=processing_time
        )
    
    async def _retrieve_documents(
        self,
        db: Session,
        query: str,
        limit: int = 5
    ) -> List[Tuple]:
        """Retrieve relevant documents using vector similarity search"""
        try:
            # Generate query embedding
            query_embedding = await self.gemini.generate_query_embedding(query)
            
            # Search similar documents
            results = VectorStore.search_similar(
                db,
                query_embedding,
                limit=limit,
                similarity_threshold=self.similarity_threshold
            )
            
            logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Document retrieval error: {e}")
            return []
    
    def _build_context(
        self,
        documents: List[Tuple]
    ) -> Tuple[str, List[SourceDocument]]:
        """Build context string from retrieved documents"""
        if not documents:
            return "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu.", []
        
        context_parts = []
        sources = []
        current_length = 0
        
        for doc, score in documents:
            # Check context length limit
            doc_text = f"[{doc.category.upper()}] {doc.title}\n{doc.content}"
            
            if current_length + len(doc_text) > self.max_context_length:
                break
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
            
            sources.append(SourceDocument(
                content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                source=f"{doc.category}: {doc.title}",
                relevance_score=round(score, 3)
            ))
        
        context = "\n\n---\n\n".join(context_parts)
        return context, sources
    
    async def add_knowledge(
        self,
        db: Session,
        title: str,
        content: str,
        category: str,
        metadata: Optional[dict] = None
    ) -> int:
        """Add a new document to knowledge base with embedding"""
        try:
            # Generate embedding for the content
            text_to_embed = f"{title}\n{content}"
            embedding = await self.gemini.generate_embedding(text_to_embed)
            
            # Add to database
            doc = VectorStore.add_document(
                db,
                title=title,
                content=content,
                category=category,
                embedding=embedding,
                metadata=metadata
            )
            
            logger.info(f"Added knowledge: {title} (category: {category})")
            return doc.id
            
        except Exception as e:
            logger.error(f"Error adding knowledge: {e}")
            raise
    
    async def reindex_document(self, db: Session, doc_id: int) -> bool:
        """Regenerate embedding for a document"""
        try:
            doc = db.query(VectorStore).filter_by(id=doc_id).first()
            if not doc:
                return False
            
            text_to_embed = f"{doc.title}\n{doc.content}"
            embedding = await self.gemini.generate_embedding(text_to_embed)
            
            VectorStore.update_embedding(db, doc_id, embedding)
            return True
            
        except Exception as e:
            logger.error(f"Error reindexing document {doc_id}: {e}")
            return False
    
    def get_chat_history(
        self,
        db: Session,
        session_id: str
    ) -> List[ChatMessage]:
        """Get formatted chat history for a session"""
        messages = ChatStore.get_chat_history(db, session_id, limit=50)
        
        return [
            ChatMessage(
                role=MessageRole(msg.role),
                content=msg.content,
                timestamp=msg.created_at
            )
            for msg in messages
        ]


# Singleton instance
rag_service = RAGService()
