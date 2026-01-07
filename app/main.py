"""
TicketGo AI Service - FastAPI Application
RAG-based Chatbot using Google Gemini and pgvector
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db, get_db_context
from app.api import chat_router, knowledge_router
from app.services import gemini_service
from app.models import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("🚀 Starting TicketGo AI Service...")
    
    try:
        # Initialize database
        init_db()
        logger.info("✅ Database initialized")
        
        # Check Gemini connection
        if await gemini_service.check_connection():
            logger.info("✅ Gemini AI connected")
        else:
            logger.warning("⚠️ Gemini AI connection failed")
        
        logger.info("✅ TicketGo AI Service started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down TicketGo AI Service...")


# Create FastAPI app
app = FastAPI(
    title="TicketGo AI Service",
    description="""
    🤖 **AI Chatbot Service for TicketGo Platform**
    
    Features:
    - RAG-based Q&A using Google Gemini
    - Vector similarity search with pgvector
    - Knowledge base management
    - Chat history tracking
    
    Built with FastAPI + LangChain + PostgreSQL/pgvector
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(chat_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")


# === Root endpoints ===

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - service info"""
    return {
        "service": "TicketGo AI Service",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Root"])
async def health_check():
    """Health check endpoint"""
    from sqlalchemy import text
    
    # Check database
    db_status = "healthy"
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Gemini
    gemini_status = "healthy" if await gemini_service.check_connection() else "unhealthy"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" and gemini_status == "healthy" else "degraded",
        version=settings.app_version,
        database=db_status,
        gemini=gemini_status
    )


# === Exception handlers ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }
    )


# === Run with uvicorn ===
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )