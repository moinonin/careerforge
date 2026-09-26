# Sprint 10 — Post-Launch: Feedback Loop & Iteration

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship the feedback collection system + feature usage tracking so real user data starts flowing. Close out remaining Sprint 9 carry-over items (ToS/Privacy pages, OpenTelemetry tracing, metrics export).

**Architecture:** Track usage server-side via `OrganizationUsageLog` (already exists in models.py). Add feedback endpoint + tracking middleware. Reconcile Stripe with local counts via a scheduled job. ToS/Privacy pages are static frontend pages.

**Tech Stack:** FastAPI endpoints, PostgreSQL (existing `OrganizationUsageLog` model), Stripe SDK (already in pyproject.toml), Next.js frontend pages.

---

## Task 1: Feature Usage Tracking Middleware

**Objective:** Track every generation request with provider, model, language, format, ATS score so we know what's used most.

**Files:**
- Modify: `backend/api/routes/generate.py` — add tracking call after each generation
- Modify: `backend/api/routes/health.py` — expose usage stats endpoint
- Test: `tests/test_usage_tracking.py`

**Step 1: Add `track_usage()` helper to generate.py**

After each successful generation, log to `OrganizationUsageLog`:
```python
# In start_generation() after successful generation:
await track_usage(user_id, provider, model_name, output_language, format, ats_score)
```

**Step 2: Write failing test**

```python
async def test_usage_logged_after_generation(client, mock_db, auth_headers):
    # POST /api/v1/generate with valid request
    # GET /api/v1/admin/usage-stats
    # Assert usage_log entry exists with correct provider/model/language
```

**Step 3: Run test to verify failure**

**Step 4: Implement `track_usage()` in generate.py**

**Step 5: Run tests to verify pass**

**Step 6: Commit**

---

## Task 2: Feedback Endpoint

**Objective:** Allow users to rate generated CVs with 👍/👎 and optional comment.

**Files:**
- Create: `backend/api/routes/feedback.py` — POST `/api/v1/feedback` endpoint
- Modify: `backend/main.py` — register feedback router
- Test: `tests/test_feedback.py`

**Step 1: Write failing test**

```python
async def test_feedback_submission(client, mock_db, auth_headers):
    # POST /api/v1/feedback { job_id, rating: 1, comment: "helpful" }
    # Assert 201, entry in Feedback table
```

**Step 2: Run test to verify failure**

**Step 3: Implement feedback endpoint in feedback.py**

**Step 4: Run tests to verify pass**

**Step 5: Commit**

---

## Task 3: Billing Reconciliation Endpoint

**Objective:** Expose a reconciliation view comparing Stripe invoices with local generation counts.

**Files:**
- Modify: `backend/api/routes/billing.py` — add reconciliation endpoint
- Test: `tests/test_billing_reconciliation.py`

**Step 1: Write failing test**

```python
async def test_billing_reconciliation(client, mock_db, admin_auth_headers):
    # GET /api/v1/billing/reconciliation
    # Assert response has local_count, stripe_count, discrepancy fields
```

**Step 2: Run test to verify failure**

**Step 3: Implement reconciliation endpoint using Stripe SDK**

**Step 4: Run tests to verify pass**

**Step 5: Commit**

---

## Task 4: ToS and Privacy Policy Pages

**Objective:** Add static legal pages required for Stripe and GDPR compliance.

**Files:**
- Create: `frontend/src/app/terms/page.tsx`
- Create: `frontend/src/app/privacy/page.tsx`
- Modify: `frontend/src/app/layout.tsx` — add links to footer

**Step 1: Create ToS page**

**Step 2: Create Privacy Policy page**

**Step 3: Add navigation links**

**Step 4: Verify build passes**

**Step 5: Commit**

---

## Task 5: OpenTelemetry Tracing Stub

**Objective:** Add OpenTelemetry instrumentation stub so tracing can be enabled without changing code.

**Files:**
- Create: `backend/monitoring/otel_init.py` — initialize_otel() with stub mode
- Modify: `backend/main.py` — call initialize_otel() at startup
- Test: `tests/test_otel.py`

**Step 1: Write failing test**

**Step 2: Implement stub (no-op when OTEL_EXPORTER endpoint is None)**

**Step 3: Run tests to verify pass**

**Step 4: Commit**

---

## Task 6: Metrics Dashboard Endpoint

**Objective:** Expose generation metrics (count by tier, provider distribution, token usage, error rate).

**Files:**
- Modify: `backend/api/routes/admin.py` — add `/api/v1/admin/metrics` endpoint
- Test: `tests/test_metrics.py`

**Step 1: Write failing test**

**Step 2: Implement metrics endpoint aggregating OrganizationUsageLog**

**Step 3: Run tests to verify pass**

**Step 4: Commit**

---

## Verification

```bash
# Full test suite
python -m pytest tests/ -v

# Frontend build
cd frontend && npm run build

# Backend health
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

All tests passing + both servers healthy = Sprint 10 ✅ COMPLETED.
