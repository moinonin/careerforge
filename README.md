# CareerForge AI

ATS-compliant CV and cover letter generation SaaS, powered by a model-agnostic LLM adapter.

Built with **FastAPI** (backend), **Next.js 14** (frontend), **PostgreSQL 16 + Redis**. Works with OpenAI, Anthropic, Ollama, or any LiteLLM-compatible provider.

---

## Pricing

| Plan | Price | Generations/month |
|---|---|---|
| **Free** | $0 | 2/month (+ $1.99 per extra 4) |
| **Individual** | $9.99/mo | 20 |
| **Team** | $19.99/mo | 40 |

Trial accounts start with 2 credits. All plans include full CV + cover letter generation, job analyzer, and document export (DOCX/PDF).

---

## Features

- **Job Analyzer** — Paste a job description, get required skills, implied skills, red flags, salary estimate, and company research (no auth required)
- **CV Generation** — AI-generated CVs optimized for ATS, exported as DOCX or PDF
- **Cover Letter Generation** — Tailored cover letters matching the job and CV
- **Multi-Provider LLM** — Switch between OpenAI, Anthropic, Ollama, LiteLLM models without code changes
- **Trial Gating** — Free-tier rate limiting with credit-based consumption
- **JWT Auth** — Access + refresh token rotation, signup, login, logout, password reset
- **Rate Limiting** — Per-tier request limits (free: 1 req/min, trial: limited)
- **Stripe Billing** — Subscription management with product catalog
- **Production Hardening** — Security headers, input sanitization, structured logging, Sentry, DB indexes

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| **Frontend** | Next.js 14, React, TypeScript, Tailwind CSS |
| **Database** | PostgreSQL 16 + asyncpg, Redis (Celery broker) |
| **LLM** | OpenAI, Anthropic, Ollama, LiteLLM (model-agnostic adapter) |
| **Auth** | JWT (python-jose), Argon2 password hashing |
| **Billing** | Stripe SDK, webhook-driven subscription management |
| **Infra** | Docker Compose, alembic migrations, Sentry |
| **Quality** | ruff, mypy, pytest — all gates pass |

---

## Quick Start

```bash
# Install dependencies
make install

# Start PostgreSQL + Redis
make dev

# Apply database migrations
make db-migrate

# Verify backend is running
curl http://localhost:8000/health
# → {"status":"ok"}

# Open frontend
open http://localhost:3000
```

Or start the backend directly without Docker:

```bash
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Endpoints

### Public (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/analyzer` | Analyze a job description for skills, salary, red flags |
| GET | `/health` | Health check |

### Authenticated (JWT required)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/signup` | Create account |
| POST | `/api/v1/auth/login` | Login (returns access + refresh tokens) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Invalidate tokens |
| GET | `/api/v1/users/me` | Get current user profile |
| PUT | `/api/v1/users/me` | Update user profile |
| POST | `/api/v1/generate` | Generate CV + cover letter |
| GET | `/api/v1/generate/jobs/{job_id}` | Poll generation status |
| GET | `/api/v1/generate/jobs/{job_id}/cv` | Download CV as DOCX |
| GET | `/api/v1/generate/jobs/{job_id}/cover-letter` | Download cover letter as DOCX |
| GET/PUT | `/api/v1/profiles` | Manage profiles |
| POST | `/api/v1/billing/checkout` | Create Stripe checkout session |
| POST | `/api/v1/billing/portal` | Customer portal session |

---

## LLM Provider Configuration

The adapter is model-agnostic. Switch providers by changing `.env`:

```bash
# Local Ollama (default for dev)
LLM_PROVIDER=ollama
LLM_MODEL=karakanalabs/specgen2.2:3b
OLLAMA_BASE_URL=http://localhost:11434

# NVIDIA / OpenAI-compatible API
LLM_PROVIDER=openai
LLM_MODEL=openai/gpt-oss-20b
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
OPENAI_API_KEY=nvapi-...

# Official OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

**Note:** The Ollama adapter uses `OLLAMA_MODEL` and `OLLAMA_BASE_URL` env vars. The OpenAI adapter reads `LLM_MODEL`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`.

Both adapters include a **60-second timeout** to prevent indefinite hangs. The OpenAI adapter also retries up to 3 times on transient failures.

---

## Pricing & Billing

The billing system uses Stripe for subscription management:

- **Free**: 2 generations/month, $1.99 per extra 4 generations
- **Individual**: $9.99/mo, 20 generations/month
- **Team**: $19.99/mo, 40 generations/month

Credits are tracked per-user and decremented on generation. Trial accounts get 2 credits on signup.

---

## Configuration

Copy `.env.example` to `.env` and fill in real values. **Never commit `.env`.**

Required variables:

```bash
# Application
CAREERFORGE_ENVIRONMENT=development
CAREERFORGE_DB_URL=postgresql+asyncpg://careerforge:password@localhost:5432/careerforge
CAREERFORGE_REDIS_URL=redis://localhost:6379/0
CAREERFORGE_JWT_SECRET=change-me-in-production

# LLM (see LLM Provider Configuration above)
LLM_PROVIDER=ollama
LLM_MODEL=karakanalabs/specgen2.2:3b
```

---

## Project Structure

```
careerforge/
├── Makefile                  # dev commands: install, dev, db-migrate, lint, test
├── pyproject.toml            # backend package + dev tooling
├── .env.example              # template env file
├── .hermes/                  # Hermes agent config
├── backend/
│   ├── main.py               # FastAPI app, middleware stack, router registration
│   ├── config.py             # settings via pydantic-settings
│   ├── database.py           # async session factory
│   ├── alembic/              # database migrations
│   ├── middleware/           # rate_limit, security_headers, request_id, error_handler
│   ├── auth/                 # JWT service, router, schemas, service layer
│   ├── llm/                  # model-agnostic adapter + providers
│   │   ├── adapter.py        # base adapter, GenerationError
│   │   ├── adapters.py       # OpenAI, LiteLLM, Ollama adapters
│   │   ├── router.py         # adapter factory, build_adapter_from_config
│   │   ├── prompts.py        # CV/cover letter prompt assembly
│   │   └── service.py        # LLM config management
│   ├── api/routes/           # API endpoints
│   │   ├── analyzer.py       # job post analyzer (no auth)
│   │   ├── generate.py       # CV + cover letter generation
│   │   ├── billing.py        # Stripe checkout & portal
│   │   ├── health.py         # health, ready, metrics
│   │   ├── llm_config.py     # LLM provider configuration
│   │   ├── feedback.py       # user feedback collection
│   │   ├── organizations.py  # org management
│   │   └── admin.py          # admin APIs
│   ├── models.py             # SQLAlchemy tables: User, Profile, Subscription, etc.
│   ├── profiles/             # profile CRUD, schemas
│   └── validators/           # input sanitization
├── frontend/
│   ├── next.config.js        # API rewrites to backend
│   ├── src/app/
│   │   ├── page.tsx          # home page
│   │   ├── pricing/page.tsx  # pricing tiers
│   │   ├── billing/page.tsx  # subscription management
│   │   ├── analyzer/page.tsx # job analyzer UI
│   │   ├── (app)/            # authenticated routes
│   │   │   ├── layout.tsx    # auth gate
│   │   │   ├── dashboard/    # user dashboard
│   │   │   └── profiles/     # profile management
│   │   └── lib/
│   │       ├── auth-context.tsx  # React auth state
│   │       └── auth.ts         # API helpers
└── docs/
    ├── SPRINTS.md                    # 10-sprint development plan
    ├── cv-generator-saas-spec.md     # product specification
    └── master_prompt_template.md     # CV/cover letter prompt template
```

---

## Development Commands

```bash
make install          # create venv + install backend deps + frontend node_modules
make dev              # start all services via docker-compose
make dev-serve        # start backend locally (no Docker)
make db-migrate       # apply alembic migrations
make db-revision MSG="description"  # create new migration
make lint             # ruff check backend/
make typecheck        # mypy backend/
make test             # pytest backend/
make test-cov         # pytest with coverage
make clean            # remove venv, .pyc, .next, node_modules
```

---

## Testing

All quality gates pass:

```bash
ruff check backend/          # linter — clean
mypy backend/               # type checker — clean
pytest tests/               # 40+ tests pass
```

Run the analyzer without auth (no login required):

```bash
curl -X POST http://localhost:8000/api/v1/analyzer \
  -H "Content-Type: application/json" \
  -d '{"job_description":"Senior Python Engineer at a startup"}'
```

---

## Error Handling

The backend returns consistent JSON errors:

| Code | Meaning |
|---|---|
| `400` | Validation error (bad input, missing fields) |
| `401` | Authentication required or invalid token |
| `403` | Insufficient permissions |
| `404` | Resource not found |
| `429` | Rate limit exceeded |
| `502` | LLM generation failed (adapter error) |
| `500` | Internal server error |

Sentry captures all unhandled exceptions in production. Set `sentry_dsn` in `.env`.

---

## LLM Adapter Architecture

The LLM layer is model-agnostic via the `LLMAdapter` base class:

- **OpenAIAdapter** — OpenAI Chat Completions with `response_format=json_object`. Supports any OpenAI-compatible endpoint (NVIDIA, etc.)
- **OllamaAdapter** — Direct HTTP to local Ollama (`/api/chat`). Has a 120s internal timeout and 3 retry attempts.
- **LiteLLMAdapter** — Covers Anthropic, DeepSeek, Gemini, AWS Bedrock, and others via LiteLLM.

Each adapter implements `generate(prompt, schema) → dict` with automatic JSON schema validation and retry on failure.

---

## Deployment

See `docs/deployment.md` for production instructions.

Key steps:
1. Set all secrets in `.env` (never commit `.env`)
2. Configure `sentry_dsn` in `.env` for error tracking
3. Set `CAREERFORGE_ENVIRONMENT=production`
4. Run `make migrate` to apply database migrations
5. Start with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
6. Frontend: `npm run build` in `frontend/`, serve statically
7. Configure Stripe webhooks in production
8. Set up SSL/TLS and CORS origins

---

## License

Apache 2.0
