# Deployment Guide — CareerForge AI

Production deployment instructions for CareerForge AI backend + frontend.

## Prerequisites

- PostgreSQL 16+ running (production: managed instance like Supabase, Neon, or self-hosted)
- Redis 7+ running (for rate limiting and Celery broker)
- Python 3.11+ and Node.js 18+
- Domain with SSL (for HSTS and CORS)
- Sentry DSN (optional but recommended)

## Environment Variables

Copy `.env.example` to `.env` and set all required values:

```bash
# Required
CAREERFORGE_DB_URL=postgresql+asyncpg://user:password@host:5432/careerforge
CAREERFORGE_REDIS_URL=redis://host:6379/0
CAREERFORGE_ENVIRONMENT=production
CAREERFORGE_SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
CAREERFORGE_JWT_SECRET=<strong-random-secret>
CAREERFORGE_STRIPE_SECRET_KEY=sk_live_...
CAREERFORGE_OPENAI_API_KEY=sk-...

# Optional (configure if using)
CAREERFORGE_S3_ENDPOINT_URL=http://localhost:9000
CAREERFORGE_S3_ACCESS_KEY_ID=minio
CAREERFORGE_S3_SECRET_ACCESS_KEY=minio123
CAREERFORGE_EMAIL_API_KEY=re_...
```

Never commit `.env`. Add it to `.gitignore`.

## Build & Deploy

### 1. Install dependencies

```bash
cd backend
uv pip install -e ".[dev]"
cd ../frontend
npm install
```

### 2. Run database migrations

```bash
cd backend
uv run python -m backend.main --migrate
# Or use the migration script:
uv run python migrate_sprint8.py
```

### 3. Build frontend

```bash
cd frontend
npm run build
```

### 4. Start the backend

```bash
# Production (no --reload)
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Or via Makefile
make start
```

### 5. Serve the frontend

Serve the built Next.js app via nginx, Vercel, or any static file server.

### 6. Verify

```bash
curl https://yourdomain.com/health
# → {"status":"ok","service":"careerforge-backend","checks":{...}}
```

## Docker Compose (Development)

```bash
docker-compose up -d
make db-migrate
```

## Monitoring

- **Health:** `GET /health` — returns dependency status (DB, Redis, S3, LLM)
- **Readiness:** `GET /ready` — returns 200 only if all dependencies are healthy
- **Metrics:** Sentry captures errors and performance traces
- **Logs:** Structured JSON logs to stdout when `environment=production`

## Security Checklist

- [ ] `CAREERFORGE_ENVIRONMENT=production`
- [ ] `CAREERFORGE_SENTRY_DSN` configured
- [ ] CORS origins restricted to your domain
- [ ] JWT secret is strong and random
- [ ] HTTPS enforced (HSTS headers)
- [ ] Rate limiting active (trial: 1 gen/30s, paid: 60 gen/min)
- [ ] Input sanitization active (strips control chars, HTML, truncation)
- [ ] All FK columns have database indexes
- [ ] Admin endpoints require admin role

## Rollback

1. Revert to previous commit: `git checkout <previous-commit>`
2. Restart services: `docker-compose restart` or `make restart`
3. Verify: `curl https://yourdomain.com/health`
