# CareerForge AI — Backend

FastAPI application for the CareerForge AI CV generation SaaS.

## Local development

```bash
make install
make dev
```

The backend listens on `http://localhost:8000`. Health check:

```bash
curl http://localhost:8000/health
```

## Configuration

All runtime configuration is via environment variables. See `.env.example` at the repo root — copy it to `.env` (never commit `.env`).

## Project structure

```
backend/
├── main.py            # FastAPI app factory + lifespan
├── config.py          # pydantic-settings settings
├── database.py        # async engine + session + base
├── logger.py          # structlog JSON logging setup
├── models/            # SQLAlchemy 2.0 declarative models
├── api/               # routers
├── services/          # business logic (auth, profiles, generation, billing)
├── schemas/           # Pydantic v2 request/response models
├── tasks/             # Celery task definitions
└── alembic/           # migration history
```
