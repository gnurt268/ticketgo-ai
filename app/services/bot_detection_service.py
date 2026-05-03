import logging
import math
import os
import pickle
from typing import Optional

import numpy as np

from app.models.schemas import BotDetectionRequest

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ml",
    "bot_model.pkl",
)

BOT_THRESHOLD = 0.6
MEDIUM_THRESHOLD = 0.3

DEFAULT_FEATURES = [
    "time_since_event_open_sec",
    "fingerprint_entropy",
    "is_authenticated",
    "requests_per_minute",
    "user_agent_score",
]


def _shannon_entropy(value: Optional[str]) -> float:
    if not value:
        return 0.0
    length = len(value)
    counts = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    entropy = 0.0
    for c in counts.values():
        p = c / length
        entropy -= p * math.log2(p)
    return entropy


def _user_agent_score(user_agent: Optional[str]) -> float:
    if not user_agent:
        return 0.0
    ua = user_agent.lower()
    suspicious_keywords = ("bot", "crawler", "spider", "headless", "phantom", "selenium", "puppeteer")
    if any(k in ua for k in suspicious_keywords):
        return 0.5
    if len(user_agent) < 20:
        return 1.5
    if len(user_agent) > 50 and ("mozilla" in ua or "chrome" in ua or "safari" in ua):
        return 8.0
    return 4.0


class BotDetectionService:
    def __init__(self) -> None:
        self._model = None
        self._features = DEFAULT_FEATURES
        self._load_model()

    def _load_model(self) -> None:
        if not os.path.exists(MODEL_PATH):
            logger.warning(
                "Model file not found at %s. Service will fail-open until model is trained.",
                MODEL_PATH,
            )
            return

        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)

        if isinstance(data, dict) and "model" in data:
            self._model = data["model"]
            self._features = data.get("features", DEFAULT_FEATURES)
        else:
            self._model = data

        logger.info("Bot detection model loaded from %s", MODEL_PATH)

    def is_ready(self) -> bool:
        return self._model is not None

    def predict(self, req: BotDetectionRequest) -> dict:
        if self._model is None:
            logger.warning("Model not loaded, returning LOW risk by default")
            return {"is_bot": False, "bot_probability": 0.0, "risk_level": "LOW"}

        features = np.array([[
            float(req.time_since_event_open_sec),
            _shannon_entropy(req.fingerprint),
            int(bool(req.is_authenticated)),
            float(req.requests_per_minute),
            _user_agent_score(req.user_agent),
        ]])

        proba = float(self._model.predict_proba(features)[0][1])
        is_bot = proba > BOT_THRESHOLD

        if proba < MEDIUM_THRESHOLD:
            risk_level = "LOW"
        elif proba < BOT_THRESHOLD:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "is_bot": is_bot,
            "bot_probability": round(proba, 4),
            "risk_level": risk_level,
        }


bot_detection_service = BotDetectionService()
