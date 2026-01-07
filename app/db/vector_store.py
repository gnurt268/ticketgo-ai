"""
Database setup and vector store operations using pgvector
"""
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import List, Optional, Generator
from contextlib import contextmanager

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# SQLAlchemy setup
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Vector dimension for Gemini embedding-004
VECTOR_DIMENSION = 768


class KnowledgeBase(Base):
    """Knowledge base documents with embeddings"""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)  # faq, policy, guide, event
    extra_metadata = Column(JSON, nullable=True)
    embedding = Column(Vector(VECTOR_DIMENSION), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatSessionModel(Base):
    """Chat sessions"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    message_count = Column(Integer, default=0)


class ChatMessageModel(Base):
    """Chat messages history"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database with pgvector extension and tables"""
    try:
        # Create pgvector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension enabled")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Create vector index for similarity search
        with engine.connect() as conn:
            # Check if index exists
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'knowledge_base' AND indexname = 'idx_knowledge_embedding'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    CREATE INDEX idx_knowledge_embedding 
                    ON knowledge_base 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))
                conn.commit()
                logger.info("Vector index created")
                
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class VectorStore:
    """Vector store operations for RAG"""
    
    @staticmethod
    def add_document(
        db: Session,
        title: str,
        content: str,
        category: str,
        embedding: List[float],
        metadata: Optional[dict] = None
    ) -> KnowledgeBase:
        """Add a document with embedding to knowledge base"""
        doc = KnowledgeBase(
            title=title,
            content=content,
            category=category,
            embedding=embedding,
            extra_metadata=metadata or {}
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    
    @staticmethod
    def search_similar(
        db: Session,
        query_embedding: List[float],
        limit: int = 5,
        category: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> List[tuple]:
        """
        Search for similar documents using cosine similarity
        Returns list of (document, similarity_score)
        """
        # Build query with cosine distance
        query = db.query(
            KnowledgeBase,
            (1 - KnowledgeBase.embedding.cosine_distance(query_embedding)).label("similarity")
        )
        
        # Filter by category if specified
        if category:
            query = query.filter(KnowledgeBase.category == category)
        
        # Filter by similarity threshold and order by similarity
        query = query.filter(
            (1 - KnowledgeBase.embedding.cosine_distance(query_embedding)) >= similarity_threshold
        ).order_by(
            KnowledgeBase.embedding.cosine_distance(query_embedding)
        ).limit(limit)
        
        results = query.all()
        return [(doc, score) for doc, score in results]
    
    @staticmethod
    def get_all_documents(db: Session, category: Optional[str] = None) -> List[KnowledgeBase]:
        """Get all documents, optionally filtered by category"""
        query = db.query(KnowledgeBase)
        if category:
            query = query.filter(KnowledgeBase.category == category)
        return query.all()
    
    @staticmethod
    def delete_document(db: Session, doc_id: int) -> bool:
        """Delete a document by ID"""
        doc = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc_id).first()
        if doc:
            db.delete(doc)
            db.commit()
            return True
        return False
    
    @staticmethod
    def update_embedding(db: Session, doc_id: int, embedding: List[float]) -> bool:
        """Update embedding for a document"""
        doc = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc_id).first()
        if doc:
            doc.embedding = embedding
            doc.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False


class ChatStore:
    """Chat session and message operations"""
    
    @staticmethod
    def create_session(db: Session, session_id: str, user_id: Optional[int] = None) -> ChatSessionModel:
        """Create a new chat session"""
        session = ChatSessionModel(
            session_id=session_id,
            user_id=user_id
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def get_session(db: Session, session_id: str) -> Optional[ChatSessionModel]:
        """Get session by ID"""
        return db.query(ChatSessionModel).filter(
            ChatSessionModel.session_id == session_id
        ).first()
    
    @staticmethod
    def add_message(
        db: Session,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[dict]] = None
    ) -> ChatMessageModel:
        """Add a message to chat history"""
        message = ChatMessageModel(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources
        )
        db.add(message)
        
        # Update session
        session = db.query(ChatSessionModel).filter(
            ChatSessionModel.session_id == session_id
        ).first()
        if session:
            session.last_message_at = datetime.utcnow()
            session.message_count += 1
        
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_chat_history(
        db: Session,
        session_id: str,
        limit: int = 10
    ) -> List[ChatMessageModel]:
        """Get recent chat history for a session"""
        return db.query(ChatMessageModel).filter(
            ChatMessageModel.session_id == session_id
        ).order_by(
            ChatMessageModel.created_at.desc()
        ).limit(limit).all()[::-1]  # Reverse to get chronological order
    
    @staticmethod
    def get_user_sessions(db: Session, user_id: int) -> List[ChatSessionModel]:
        """Get all sessions for a user"""
        return db.query(ChatSessionModel).filter(
            ChatSessionModel.user_id == user_id
        ).order_by(
            ChatSessionModel.last_message_at.desc()
        ).all()