.PHONY: install dev db-migrate db-revision db-upgrade db-downgrade lint typecheck test test-cov clean docker-up docker-down docker-build help dev-serve

# ── CareerForge AI — Development Makefiles ──────────────────────────────
# Sprint 0 scaffold. All commands assume you are at the repo root.
# ─────────────────────────────────────────────────────────────────────────

# Python virtualenv (backend + worker share one venv)
VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

# ── Help ──────────────────────────────────────────────────────────────────
help:
	@echo "CareerForge AI — available targets"
	@echo ""
	@echo "  install        Create venv + install backend deps + frontend deps"
	@echo "  dev            Start all 5 services via docker-compose (detached)"
	@echo "  db-migrate     Run alembic upgrade head (container DB)"
	@echo "  db-revision    Create a new alembic migration (pass message with MSG=…)"
	@echo "  lint           Run ruff over backend/"
	@echo "  typecheck      Run mypy over backend/"
	@echo "  test           Run pytest over backend/"
	@echo "  test-cov       Run pytest with coverage report"
	@echo "  docker-up      docker-compose up -d  (alias for dev)"
	@echo "  docker-down    docker-compose down"
	@echo "  docker-build   docker-compose build --no-cache"
	@echo "  clean          Remove venv, .pyc, .next, node_modules, build artefacts"

# ── Install ───────────────────────────────────────────────────────────────
install:
	@echo "[make] Creating virtualenv …"
	$(PYTHON) -m venv $(VENV) 2>/dev/null || python3 -m venv $(VENV)
	@echo "[make] Installing backend deps …"
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "[make] Installing frontend deps …"
	cd frontend && npm install

# ── Development server (Docker) ───────────────────────────────────────────
dev: docker-up
	@echo ""
	@echo "[make] Services running. Backend health:"
	@curl -s http://localhost:8000/health || echo "  (backend not ready yet — give it 10 s)"

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build --no-cache

# ── Database migrations ───────────────────────────────────────────────────
db-migrate:
	$(PYTHON) -m alembic upgrade head

db-revision:
	$(PYTHON) -m alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	$(PYTHON) -m alembic upgrade head

db-downgrade:
	$(PYTHON) -m alembic downgrade -1

# ── Quality gates ─────────────────────────────────────────────────────────
lint:
	$(PYTHON) -m ruff check backend/

typecheck:
	$(PYTHON) -m mypy backend/ --ignore-missing-imports

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov:
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=backend --cov-report=term-missing

# ── Clean ──────────────────────────────────────────────────────────────────
clean:
	rm -rf $(VENV) .next node_modules backend/__pycache__ backend/**/__pycache__ \
	       backend/**/**/__pycache__ tests/__pycache__ tests/**/__pycache__ \
	       build/ dist/ *.egg-info .coverage htmlcov/ \
	       docker-compose.override.yml

# ── Dev serve (local, blocks terminal; use docker-compose for full stack) ──
dev-serve:
	.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
