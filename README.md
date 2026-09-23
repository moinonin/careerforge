# CareerForge AI

ATS-compliant CV and cover letter generation SaaS.

Built with FastAPI (backend), Next.js 14 (frontend), PostgreSQL 16 + Redis.
Powered by a model-agnostic LLM adapter — OpenAI, Anthropic, Ollama, or your own.

## Quick start (Sprint 0)

```bash
make install      # create venv + install backend deps + frontend node_modules
docker-compose up -d   # postgres + redis
make db-migrate   # apply alembic migrations
curl http://localhost:8000/health   # → {"status":"ok"}
```

Open `http://localhost:3000` in the browser for the frontend landing page.

## Sprint plan

See `docs/SPRINTS.md` for the full 10-sprint breakdown.

## Configuration

Copy `.env.example` to `.env` and fill in real values. Never commit `.env`.

## Project layout

```
├── Makefile
├── pyproject.toml          # backend package + dev tooling (ruff, mypy, pytest)
├── .env.example
├── docker-compose.yml      # postgres + redis
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── middleware/          # Rate limiting, security headers, request ID
│   ├── validators/          # Input sanitization
│   ├── monitoring/          # Sentry initialization
│   ├── api/
│   │   └── routes/
│   ├── auth/              # Sprint 1 — JWT auth, signup/login/refresh/logout, /users/me
│   ├── models.py          # 14+ tables: User, RefreshToken + core tables
│   └── alembic/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── src/app/
└── docs/
     ├── SPRINTS.md
     ├── cv-generator-saas-spec.md
     └── master_prompt_template.md
```

## Status

- **Sprint 0 — Foundation:** complete. `make install && make dev` boots backend + frontend; `GET /health` and `GET /ready` respond 200.
- **Sprint 1 — Authentication & Identity:** backend complete (JWT access+refresh with rotation, signup, login, refresh, logout, forgot/reset password, /users/me GET+PUT, trial gating dependency). Frontend pages and email service stub pending.
- **Sprint 8 — Frontend Polish:** complete (dashboard redesign, quick-generate, library, ATS score).
- **Sprint 9 — Production Hardening:** complete — rate limiting, input sanitization, security headers, enhanced health, structured logging, Sentry, DB indexes, admin APIs.

All quality gates pass: `ruff check backend/` clean, `mypy backend/` clean, `pytest tests/` 40+ pass.

## Deployment

See `docs/deployment.md` for production deployment instructions.

Key steps:
1. Set all secrets in `.env` (never commit `.env`)
2. Configure `sentry_dsn` in `.env` for error tracking
3. Set `CAREERFORGE_ENVIRONMENT=production`
4. Run `make migrate` to apply database migrations
5. Start with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
6. Frontend: `npm run build` in `frontend/`, serve statically

## Error handling

The backend returns consistent JSON errors:
- `400` — Validation error (bad input)
- `401` — Authentication required
- `403` — Insufficient permissions
- `404` — Resource not found
- `429` — Rate limit exceeded
- `500` — Internal server error

Sentry captures all unhandled exceptions in production.
