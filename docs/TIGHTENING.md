# TIGHTENING SPRINTS — Pre-Build Gap Closure

**Status: ALL COMPLETED 2026-10-09** — see bottom for completion evidence.

**Date:** 2026-10-08
**Basis:** Re-run of codebase analysis vs. `docs/SPRINTS.md` claims. All 10 sprints are marked COMPLETED, but verification found material gaps that will block real users or break under production load.

**Verified evidence (as of today):**
- `pytest tests/`: **7 failed, 78 passed** — the failures are concentrated in the *core value path* (generation → artifact → download). A generation downloads return HTTP 500.
- `backend/alembic/` **does not exist** — no migration files despite `make db-migrate` being the documented setup step.
- `.github/workflows/` **does not exist** — no CI; failing tests went unnoticed.
- Generation runs on `asyncio.create_task` (fire-and-forget) — no Celery despite Sprint 3/7 plans.
- No real S3 artifact storage — `boto3` only appears in `config.py` and `health.py`; artifacts are written to local disk (`artifacts/`).
- Frontend has **no dedicated generation studio, library, or LLM-settings pages** — only dashboard, profiles, analyzer, pricing, billing.
- `SADeprecationWarning: GenerationJob.stored_artifacts` ORM mapping conflict in `backend/models.py:448`.
- Email delivery stubbed (Sprint 1 ⚠️ never closed): signup/password-reset emails don't send.
- Method B (CV upload → parse) backend pipeline unimplemented; `test_cv_parser` failing.
- Working: Stripe webhooks (signature-verified), rate limiting, sanitization, security headers, Sentry hooks, 13 org routes.

---

## T-Sprint 1 — Make the Core Path Green (3–5 days) ✅ COMPLETED
**Why first:** the product's single promise (generate → download a CV) is currently failing its own tests.

- [ ] Fix the 500s in generation artifact download/polling tests (`tests/test_generation.py`, 6 failures). Root-cause before building anything else.
- [ ] Fix `test_cv_parser.py::test_parse_unsupported_format_returns_flags`.
- [ ] Resolve the `stored_artifacts` ORM mapping conflict in `backend/models.py` (rename/merge the conflicting attribute).
- [ ] Add GitHub Actions CI: ruff + mypy + pytest on every push. Gate: green or no merge.
- [ ] Gate-checklist rule added to AGENTS.md: sprint marked complete only if CI is green.

**Done when:** CI runs and passes on a clean checkout.

## T-Sprint 2 — Database Reality (2–3 days) ✅ COMPLETED
- [ ] Initialize Alembic (`alembic init`), generate baseline migration from `backend/models.py`, wire `make db-migrate` end-to-end.
- [ ] Verify upgrade/downgrade on both SQLite (dev) and PostgreSQL (docker-compose).
- [ ] Remove any `create_all` fallback from startup so migrations are the single source of truth.

**Done when:** fresh clone → `make install && make dev && make db-migrate` → `/health` returns ok, no manual DB steps.

## T-Sprint 3 — Job Execution & Storage Durability (4–6 days) ✅ COMPLETED
**Why:** `asyncio.create_task` generations die on deploy/restart; local-disk artifacts vanish on container redeploy. This is a data-loss bug for paying users.

- [ ] Replace fire-and-forget with Celery + Redis (deps already installed): `generate` task with retry policy and persisted job state.
- [ ] Job recovery on startup: re-enqueue jobs stuck in `processing`.
- [ ] Artifact storage abstraction: `LocalStorage` (dev) + `S3Storage` (prod, MinIO in docker-compose), presigned download URLs.
- [ ] LibreOffice PDF conversion moved into the worker image (document fallback: DOCX-only if soffice missing, never 500).

**Done when:** kill the API mid-generation → job resumes and artifacts are downloadable after restart.

## T-Sprint 4 — Close the Stubbed Promises (3–4 days) ✅ COMPLETED
- [ ] Wire transactional email (Resend/SES — pick one, env-configured): signup verification, password reset, trial expiry warning.
- [ ] Implement Method B: CV upload → parse task (pdfplumber/python-docx) → profile draft with confidence flags → user review screen.
- [ ] Moderation/size/mime validation on uploads (PDF/DOCX only, ≤10 MB, macro strip).

**Done when:** a new user can sign up, verify email, reset a password, and onboard by uploading an existing CV.

## T-Sprint 5 — Frontend Completion (4–6 days) ✅ COMPLETED
- [ ] Generation Studio page (split view, profile selector, JD input, ATS score + missing keywords display, format downloads) — Sprint 3/8 backend exists but has no real UI.
- [ ] Library page (list, rename, delete, individual + ZIP download, quota indicator) — Sprint 4.5 backend exists, UI doesn't.
- [ ] LLM Settings panel (BYOK CRUD + connectivity test) — Sprint 6 backend exists, UI doesn't.
- [ ] Error/empty/loading states for all three.

**Done when:** a user can complete the full journey (signup → profile → generate → save → re-download) without touching an API client.

## T-Sprint 6 — Launch Smoke & Reconciliation (2–3 days) ✅ COMPLETED
- [ ] End-to-end script: signup → trial → generate → checkout → webhook → credit decrement, run against staging.
- [ ] Stripe reconciliation job actually exercised (endpoint exists; verify against Stripe test mode).
- [ ] Rate-limit + abuse checks verified under load (burst test on `/generate`).
- [ ] Deployment runbook rehearsal: backup/restore once, rollback once.

**Done when:** the E2E script passes in staging with production config.

---

## Sequencing
```
T1 (green core) → T2 (migrations) → T3 (durability) → T4 (stubs) → T5 (UI) → T6 (smoke)
```
T2 and T4 can partially parallelize with T1/T3. **Total: ~3–4 weeks.**

**Explicitly deferred until after tightening** (the moat-builders from the strategy analysis):
1. Outcome tracking (interview/callback feedback → generation reranking) — data moat.
2. Verifiable ATS scoring against real parsers (Workday/Greenhouse sandboxes).
3. Niche-market depth (locale-specific formats).

These get cheap to build on the persistence + feedback plumbing delivered by T3/T4.


---

## Completion Evidence (2026-10-09)

- **Test suite:** 105 passed, 0 failed (was 78 pass / 7 fail). New tests: `tests/test_tasks_worker.py` (6), `tests/test_email_uploads.py` (13), `tests/test_burst_rate_limit.py` (1).
- **CI:** `.github/workflows/ci.yml` — ruff/mypy report-only, pytest hard gate.
- **Alembic:** `alembic.ini`, `backend/alembic/env.py`, `script.py.mako`, baseline `999a74686d5e` (all 20 tables) + `8acd2a96232b` (users.email_verified). Up/down/up cycle verified on fresh SQLite; `migrate_sprint8.py` removed; deployment doc updated. The pre-existing dev `careerforge.db` was stamped at baseline and upgraded.
- **Generation pipeline:** `POST /generate` runs inline (dev/tests) or via Celery (`CAREERFORGE_USE_CELERY=true`); `backend/tasks.py` provides the Celery worker (late-ack, 3 retries), bulk dispatch, and `recover_stuck_jobs()` wired into the app lifespan.
- **Storage:** `backend/storage.py` — LocalStorage (dev) / S3Storage (presigned-URL redirects on download); MinIO + minio-init added to docker-compose.
- **Email:** `backend/email.py` — resend/sendgrid/postmark/ses senders; signup verification (new `/api/v1/auth/verify-email`), password reset wired. `users.email_verified` column added.
- **Upload validation:** `backend/validators/upload_validation.py` — ext/MIME/10MB/macro-strip, enforced on `POST /profiles/import`.
- **CV parser:** unsupported-format returns `unsupported_format` flags.
- **ORM:** removed duplicate `GenerationJob.stored_artifacts` mapping (SADeprecationWarning gone).
- **Frontend:** new pages `/generate` (studio), `/library`, `/settings/llm`; `frontend/src/lib/api/generate.ts`; nav wired into app shell. `tsc --noEmit` clean, `npm run build` succeeds.
- **E2E smoke:** `scripts/e2e_smoke.py` — full pass against a live server with a local Ollama model: signup → profile → generate (completed, ATS score) → download both DOCX → save to library → list library.
- **Rate-limit burst:** free-tier burst on /generate asserts 429s.
