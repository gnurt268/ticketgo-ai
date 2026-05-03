import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.bot_detection import router as bot_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

app = FastAPI(
    title="TicketGo AI Service",
    description="Microservice AI cho TicketGo — phát hiện bot mua vé",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bot_router, prefix="/api/bot", tags=["Bot Detection"])


@app.get("/")
def root() -> dict:
    return {"service": "ticketgo-ai", "status": "running"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
