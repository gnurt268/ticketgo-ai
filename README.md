# 🤖 TicketGo AI Service

AI-powered chatbot microservice for TicketGo platform using RAG (Retrieval Augmented Generation).

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TicketGo AI Service                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   FastAPI   │───►│    RAG      │───►│   Google Gemini     │ │
│  │   /api/chat │    │  Pipeline   │    │   (Free Tier)       │ │
│  └─────────────┘    └──────┬──────┘    └─────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│                    ┌───────────────┐                            │
│                    │  PostgreSQL   │                            │
│                    │  + pgvector   │                            │
│                    └───────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Google Gemini API Key (free at https://aistudio.google.com/apikey)

### Step 1: Get Gemini API Key

1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key

### Step 2: Setup Environment

```bash
cd ticketgo-ai

# Copy environment file
cp .env.example .env

# Edit .env and add your Gemini API key
nano .env
```

### Step 3: Run with Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f ai-service

# Stop services
docker-compose down
```

### Step 3 (Alternative): Run Locally

```bash
# Start PostgreSQL only
docker run -d \
  --name ticketgo-pgvector \
  -e POSTGRES_USER=ticketgo \
  -e POSTGRES_PASSWORD=ticketgo123 \
  -e POSTGRES_DB=ticketgo_ai \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the service
python -m uvicorn app.main:app --reload --port 8000
```

### Step 4: Initialize Knowledge Base

```bash
# Seed default FAQ & policies
curl -X POST http://localhost:8000/api/knowledge/seed

# Sync events from main API (optional)
curl -X POST http://localhost:8000/api/knowledge/sync-events
```

### Step 5: Test the Chatbot

```bash
# Send a message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Làm sao để mua vé?"}'
```

## 📚 API Documentation

After starting the service, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to chatbot |
| GET | `/api/chat/history/{session_id}` | Get chat history |
| GET | `/api/knowledge` | List knowledge base |
| POST | `/api/knowledge` | Add knowledge item |
| POST | `/api/knowledge/seed` | Seed default FAQ |
| POST | `/api/knowledge/sync-events` | Sync events from main API |
| GET | `/health` | Health check |

### Chat Request Example

```json
{
  "message": "Làm sao để mua vé concert?",
  "session_id": "optional-session-id",
  "user_id": 1
}
```

### Chat Response Example

```json
{
  "answer": "Để mua vé trên TicketGo, bạn thực hiện các bước sau...",
  "session_id": "sess_abc123",
  "sources": [
    {
      "content": "Hướng dẫn mua vé...",
      "source": "faq: Cách mua vé trên TicketGo",
      "relevance_score": 0.95
    }
  ],
  "suggested_questions": [
    "Thanh toán bằng những hình thức nào?",
    "Làm sao để kiểm tra vé đã mua?"
  ],
  "processing_time_ms": 250
}
```

## 🔧 Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_USER` | PostgreSQL user | ticketgo |
| `POSTGRES_PASSWORD` | PostgreSQL password | ticketgo123 |
| `POSTGRES_DB` | Database name | ticketgo_ai |
| `MAIN_API_URL` | Spring Boot API URL | http://localhost:8080/api |
| `CORS_ORIGINS` | Allowed origins | http://localhost:5173 |
| `DEBUG` | Debug mode | True |

## 📁 Project Structure

```
ticketgo-ai/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py          # Chat endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py    # Gemini AI
│   │   ├── rag_service.py       # RAG pipeline
│   │   └── knowledge_service.py # Knowledge base
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   └── db/
│       ├── __init__.py
│       └── vector_store.py  # pgvector operations
├── data/
│   └── knowledge_base/      # Static knowledge files
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app
```

## 📊 Monitoring

Health check endpoint: `GET /health`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "healthy",
  "gemini": "healthy"
}
```

## 🔗 Integration with Spring Boot

The AI service integrates with the main Spring Boot API:

1. **Event Sync**: Automatically indexes events from `/api/public/events`
2. **User Context**: Can receive `user_id` to personalize responses
3. **Session Management**: Tracks conversations per user

### Spring Boot Integration Example

```java
@Service
public class AIChatService {
    
    @Value("${ai.service.url}")
    private String aiServiceUrl;
    
    public ChatResponse sendMessage(String message, String sessionId, Long userId) {
        WebClient client = WebClient.create(aiServiceUrl);
        
        return client.post()
            .uri("/api/chat")
            .bodyValue(Map.of(
                "message", message,
                "session_id", sessionId,
                "user_id", userId
            ))
            .retrieve()
            .bodyToMono(ChatResponse.class)
            .block();
    }
}
```

## 📝 License

MIT License - TicketGo Project
