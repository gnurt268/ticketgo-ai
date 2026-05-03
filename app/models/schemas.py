from typing import Optional
from pydantic import BaseModel, Field


class BotDetectionRequest(BaseModel):
    fingerprint: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_authenticated: bool = False
    time_since_event_open_sec: float = Field(default=0.0, ge=0)
    requests_per_minute: float = Field(default=0.0, ge=0)


class BotDetectionResponse(BaseModel):
    is_bot: bool
    bot_probability: float
    risk_level: str
