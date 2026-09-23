FROM python:3.11-slim

# ── System deps ────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python env ─────────────────────────────────────────────────────────────
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# ── Install deps first (cached layer) ──────────────────────────────────────
COPY pyproject.toml README.md ./
COPY backend/ ./backend/

RUN python -m venv .venv \
    && .venv/bin/pip install --upgrade pip \
    && .venv/bin/pip install -e ".[dev]"

# ── Dev helpers ────────────────────────────────────────────────────────────
RUN .venv/bin/pip install alembic

EXPOSE 8000

# Default command overridden in docker-compose.yml
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
