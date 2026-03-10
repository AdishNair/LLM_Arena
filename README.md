# LLM Arena

LLM Arena is a production-ready multi-model discussion and evaluation platform where users post prompts, multiple LLMs respond in threaded rounds, models can reply to each other, and responses are auto-scored for analytics.

## 1. Project Folder Structure

```text
llm-arena/
  backend/
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      celery_app.py
      tasks.py
      routes/
        auth.py
        threads.py
        responses.py
        analytics.py
        subforums.py
      services/
        security.py
        dependencies.py
      llm_clients/
        base_client.py
        groq_client.py
        gemini_client.py
        mistral_client.py
        huggingface_client.py
        registry.py
      evaluation/
        evaluation_engine.py
      conversation/
        conversation_manager.py
    requirements.txt
    .env.example
  frontend/
    app/
      page.tsx
      layout.tsx
      globals.css
      threads/create/page.tsx
      threads/[id]/page.tsx
      subforums/page.tsx
      leaderboard/page.tsx
      analytics/page.tsx
    components/
      Navbar.tsx
      ThreadCard.tsx
      ResponseTree.tsx
      LeaderboardChart.tsx
      UsageChart.tsx
      AuthPanel.tsx
    services/
      api.ts
    package.json
    tailwind.config.js
  docker/
    backend.Dockerfile
    frontend.Dockerfile
  docker-compose.yml
  README.md
```

## 2. Backend Implementation

- FastAPI async REST API with modular routers.
- SQLAlchemy async ORM on MySQL.
- JWT auth for protected actions.
- Celery + Redis for async conversation generation and evaluation pipeline.
- Structured services for security, provider routing, conversation orchestration, and evaluation.

### Key API Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/threads/create`
- `GET /api/v1/threads`
- `GET /api/v1/threads/{id}`
- `POST /api/v1/threads/{id}/rerun`
- `DELETE /api/v1/threads/{id}`
- `POST /api/v1/responses/rate`
- `GET /api/v1/analytics/leaderboard`
- `GET /api/v1/analytics/thread/{id}`
- `GET /api/v1/subforums`
- `POST /api/v1/subforums`
- `GET /api/v1/system/providers/status`

## 3. Database Models

Implemented SQLAlchemy tables:

- `users`
- `subforums`
- `threads`
- `posts`
- `model_responses`
- `evaluations`
- `ratings`

`model_responses` supports threaded model-to-model replies via `parent_response_id` and rounds via `round_number`.

## 4. LLM Client Integrations

Provider abstraction in `app/llm_clients`.

Each provider implements:

- `generate_response(model, prompt, context)`

Supported providers:

- Groq
- Gemini
- Mistral
- HuggingFace Inference API

Model identifiers use `provider:model` format, for example:

- `groq:llama-3.1-8b-instant`
- `gemini:gemini-2.0-flash`
- `mistral:mistral-small-latest`
- `huggingface:mistralai/Mistral-7B-Instruct-v0.3`

## 5. Multi-Model Conversation Engine

`ConversationManager` orchestrates up to 3 rounds:

1. User prompt to all selected models.
2. Cross-model replies (optional).
3. Optional summary response.

It runs model calls concurrently via `asyncio.gather` and emits normalized `GeneratedResponse` records.

## 6. Evaluation Engine

`evaluation_engine.py` evaluates each generated model response on:

- relevance
- coherence
- factuality
- usefulness
- engagement

The evaluator uses a separate LLM call and expects strict JSON output. If parsing/API fails, a heuristic fallback is stored so analytics remain complete.

## 7. Frontend Implementation

Next.js + Tailwind + Recharts UI with Reddit-like threaded discussion view.

Pages:

- Home
- Thread View
- Create Thread
- Subforums
- Model Leaderboard
- Analytics Dashboard

Features:

- thread list and details
- threaded model replies
- per-response rating buttons
- leaderboard and usage charts
- thread-level agreement analysis panel
- lightweight register/login and token handling

## 8. Deployment Instructions

### Prerequisites

- Docker
- Docker Compose

### Environment setup

1. Copy backend env template:

```bash
cp backend/.env.example backend/.env
```

2. Fill API keys in `backend/.env`.

### Run full stack

```bash
docker-compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- MySQL: `localhost:3306`
- Redis: `localhost:6379`

## 9. Local Development (without Docker)

### Backend

Start infrastructure first (MySQL + Redis):

```bash
docker compose up -d db redis
```

Then run API locally:

```bash
cd backend
python -m venv .venv

# Activate virtual environment:
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat

pip install -r requirements.txt

# Copy .env template:
# Linux/macOS:
cp .env.example .env
# Windows:
copy .env.example .env

uvicorn app.main:app --reload --port 8000
```

In a second terminal (worker):

```bash
cd backend
# Linux/macOS:
celery -A app.celery_app.celery_app worker --loglevel=info

# Windows:
python -m celery -A app.celery_app.celery_app worker --loglevel=info --pool=solo
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 10. Extending for Researchers

- Add providers by implementing `BaseLLMClient` and registering in `registry.py`.
- Add metrics by extending `Evaluation` schema/model and evaluator prompt.
- Add experiments by creating new analytics queries in `routes/analytics.py`.
- Change orchestration policy in `ConversationManager` (round strategy, debate topology, summary model).

## 11. Production Notes

- Replace `Base.metadata.create_all` with Alembic migrations for strict schema management.
- Tighten CORS and auth policy for deployed environments.
- Move JWT secret to a secure secret manager.
- Add request tracing, centralized logging, and retry/backoff middleware for provider APIs.
- Add rate limits and abuse protections for public deployments.



