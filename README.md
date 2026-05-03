# ticketgo-ai

Microservice AI cho TicketGo — phát hiện bot mua vé bằng Random Forest.

## Cấu trúc

```
ticketgo-ai/
├── app/
│   ├── api/bot_detection.py        # FastAPI router
│   ├── models/schemas.py           # Pydantic schemas
│   ├── services/bot_detection_service.py
│   └── main.py                     # FastAPI entry
├── ml/
│   ├── generate_dataset.py         # Sinh dataset giả
│   ├── train_bot_model.py          # Train Random Forest
│   ├── bot_dataset.csv             # (generated)
│   └── bot_model.pkl               # (generated)
└── requirements.txt
```

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/Mac

python -m pip install -r requirements.txt
```

## Train model

```bash
python ml/generate_dataset.py
python ml/train_bot_model.py
```

## Chạy service

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Test endpoint

```bash
curl -X POST http://localhost:8001/api/bot/detect ^
  -H "Content-Type: application/json" ^
  -d "{\"fingerprint\":\"abc123xyz\",\"user_agent\":\"Mozilla/5.0 Chrome/120\",\"ip_address\":\"127.0.0.1\",\"is_authenticated\":true,\"time_since_event_open_sec\":45,\"requests_per_minute\":5}"
```

Response:

```json
{
  "is_bot": false,
  "bot_probability": 0.08,
  "risk_level": "LOW"
}
```

## Tích hợp với ticketgo-api

Backend Java (`ticketgo-api`) gọi `POST http://localhost:8001/api/bot/detect` từ `BotDetectionService.java` khi user join hàng chờ. Cấu hình URL qua biến môi trường `AI_SERVICE_URL`.
