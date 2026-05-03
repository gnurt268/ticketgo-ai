from fastapi import APIRouter

from app.models.schemas import BotDetectionRequest, BotDetectionResponse
from app.services.bot_detection_service import bot_detection_service

router = APIRouter()


@router.post("/detect", response_model=BotDetectionResponse)
def detect_bot(request: BotDetectionRequest) -> BotDetectionResponse:
    result = bot_detection_service.predict(request)
    return BotDetectionResponse(**result)


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": bot_detection_service.is_ready(),
    }
