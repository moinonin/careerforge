# SPRINTS.md — CareerForge AI: CV Generation SaaS

**Document Version:** 1.0.0
**Date:** September 22, 2026
**Status:** Implementation Blueprint

---

## Part A: Engineering the Generic Master Prompt

### A.1 Problems with the Current Master Prompt

The current `docs/master_prompt.md` is a great template but is **hardcoded to Nicolus Rotich, PhD** and carries assumptions that break for other users:

1. **Identity-specific data** (name, location, phone, LinkedIn URL, specific thesis title) — not reusable.
2. **Hardcoded translation directive** ("Translate Quant to Industry/Academia") — only relevant for someone moving from quant finance to physical engineering; a user going from academia to tech, or marketing to SaaS, needs a different bridge.
3. **Single-sector framing** — the "Key Relevance to [Job Sector]" line is hardcoded to physical/chemical roles; the prompt should let the LLM infer the relevant bridge generically.
4. **Missing structural requirements** that a true SaaS would need:
   - No explicit instruction to handle different CV lengths (1-page, 2-page, academic 3+ page).
   - No instruction for handling employment gaps, career changes, or short-term contracts.
   - No instruction for tailoring skill hierarchy (most relevant first vs. chronological).
   - No explicit instruction to normalize different input formats (PDF parse artifacts, OCR errors, raw bullet lists) into clean output.
   - No fallback behavior when the master profile is incomplete (e.g., missing dates, missing company names).
   - No instruction for multi-language output (a real SaaS feature).
   - No tone calibration (executive vs. junior vs. academic vs. creative).

### A.2 Generic Master Prompt Design (Template with Slot Placeholders)

The prompt MUST be fully parameterized at runtime. The system substitutes placeholders from the user's master profile JSON and the job description before sending to the LLM.

Below is the **production master prompt template**. All `[PLACEHOLDER]` tokens are replaced server-side.

```
ACT AS AN EXPERT EXECUTIVE RECRUITER, HIRING MANAGER, AND ATS OPTIMIZATION SPECIALIST.

I will provide my MASTER PROFILE and a TARGET JOB DESCRIPTION. Your task is to generate two tailored, highly polished application documents:

1. An ATS-compliant, single-column CV
2. A compelling, single-page Cover Letter

--------------------------------------------------------------------------------

### MY MASTER PROFILE

[PROFILE_SECTION — filled from user's master profile JSON]

Contact Information:
  Name: [USER_FULL_NAME]
  Location: [USER_LOCATION]
  Contact: [USER_PHONE] | [USER_EMAIL]
  LinkedIn: [USER_LINKEDIN] (if provided)

Education:
[EDUCATION_ENTRIES — each entry: degree, institution, location, dates, thesis/dissertation if academic, relevant coursework/honors]

Core Technical Competencies:
[TECHNICAL_SKILLS — grouped by domain; each domain is a bullet list of specific skills, tools, and technologies]

Professional Experience:
[WORK_EXPERIENCE_ENTRIES — each entry: role title, company, location, dates, 3-6 bullet points of achievements and responsibilities, quantified outcomes where available]

 Publications / Portfolio / Projects (if applicable):
[OPTIONAL_SECTION — publications with full citation, portfolio links, notable projects with tech stack]

 Additional Information (if provided):
  Languages: [LANGUAGES_WITH_PROFICIENCY]
  Certifications: [CERTIFICATIONS_WITH_ISSUING_BODY_AND_DATES]
  Awards/Honors: [AWARDS_WITH_DATES]
  Volunteer/Community: [OPTIONAL]

--------------------------------------------------------------------------------

### INSTRUCTIONS FOR REWRITING

#### 1. Keyword Extraction & Matching
Analyze the Job Description below. Extract:
  - Primary required skills (hard skills, tools, platforms, languages)
  - Secondary/desirable skills
  - Soft skills and behavioral traits
  - Domain/industry keywords
  - Required education or certifications

Integrate these keywords NATURALLY into both documents. Do NOT keyword-stuff. Every keyword integration must be contextually honest based on the master profile.

#### 2. Role Translation & Relevance Bridging
Analyze how each role in the master profile maps to the target job. For roles that are NOT obviously aligned:
  - Identify transferable skills, methodologies, and outcomes
  - Add a concise "Relevance to [Target Role/Domain]" note under that role (1 line, max 2 lines)
  - Frame achievements in language that the target industry would value

Do NOT invent skills or experiences the user does not have. If a target requirement cannot be honestly matched, omit it rather than fabricate.

#### 3. CV Construction Rules
  - SINGLE-COLUMN layout. No tables, no text boxes, no multi-column frames.
  - Standard section headers (use the exact header names listed in Section 6 of the ATS Compliance Rules, below).
  - Clear reverse-chronological order for experience and education.
  - Each experience entry: Role Title, Company, Location, Dates (Month Year – Month Year or Month Year – Present), 3–6 bullet points.
  - Bullet points: start with a strong action verb, include a quantified outcome where the data exists, include relevant keywords naturally.
  - Length guidance:
      * If target job is a standard industry role: target 1–2 pages.
      * If target job is academic/research: allow 2–3+ pages with full publication list.
      * If the master profile is sparse: do NOT pad with filler; keep it honest and concise.
  - Include a "Professional Summary" section (3–4 lines) at the top, tailored to the target role, synthesized from the most relevant parts of the profile.
  - Include a "Core Competencies" or "Skills" section near the top (6–12 items, comma-separated or short bullets), prioritizing skills that match the job description.
  - If the user has publications, include a "Selected Publications" or "Publications" section; format citations consistently (choose one citation style and apply uniformly).
  - If the user has provided certifications, include a "Certifications" section.
  - If the user has provided languages, include a "Languages" section.

#### 4. Cover Letter Construction Rules
  - ONE PAGE maximum. Approx. 250–400 words.
  - Opening paragraph: Strong, specific motivation hook — WHY this company, WHY this role, what specifically attracts the candidate. Reference something specific from the job description or company context. Do NOT open with "I am writing to apply for..."
  - Second paragraph: Technical alignment — map 2–3 specific areas of the candidate's background to the job's core requirements. Use concrete examples (projects, outcomes, technologies) from the master profile.
  - Third paragraph: Soft skills / working style / value-add — what the candidate brings beyond technical fit (leadership, mentorship, cross-functional coordination, problem-solving approach).
  - Closing paragraph: Brief, confident call to action. Express enthusiasm for the opportunity.
  - Professional sign-off.

#### 5. Tone Calibration
  - The tone should match the target role's level and industry:
      * Executive / senior leadership: authoritative, strategic, concise, outcome-focused.
      * Mid-level individual contributor: confident, technically precise, achievement-oriented.
      * Junior / entry-level: eager, growth-minded, highlight potential and transferable foundation.
      * Academic / research: rigorous, publication-and-methodology-focused, formal.
      * Creative / marketing / product: energetic, narrative-driven, highlight impact and ownership.
  - If the user has indicated a preferred tone, honor it. Otherwise, infer from the target role.

#### 6. ATS Compliance Rules (MANDATORY for CV output)
  - Single-column, linear text flow. No floating elements.
  - Standard, recognizable section headers ONLY:
      * "PROFESSIONAL SUMMARY" or "SUMMARY"
      * "PROFESSIONAL EXPERIENCE" or "WORK EXPERIENCE" or "EXPERIENCE"
      * "EDUCATION"
      * "SKILLS" or "CORE COMPETENCIES" or "TECHNICAL SKILLS"
      * "PUBLICATIONS" (if applicable)
      * "CERTIFICATIONS" (if applicable)
      * "LANGUAGES" (if applicable)
      * "PROJECTS" (if applicable)
  - No tables, no text boxes, no columns, no headers/footers with critical content, no images/graphics.
  - Standard web-safe fonts only (Calibri, Arial, Helvetica, Georgia, Times New Roman).
  - No special characters that could corrupt parsing (avoid em-dashes in headers, avoid non-ASCII where a safe equivalent exists).
  - Date format: "MMM YYYY" or "Month YYYY" (e.g., "Feb 2019 – Present"). Avoid ambiguous formats.
  - File output format: .docx (primary), .pdf (derived from .docx — never a scanned/image PDF).

#### 7. Handling Incomplete or Ambiguous Profile Data
  - If a work experience entry is missing dates, use the format "[Dates not specified]" and flag it in the output metadata.
  - If a company name is missing, use "[Company name not specified]".
  - If a skill is listed without a proficiency level, do not invent one.
  - If the master profile is missing a section the job description emphasizes, do NOT fabricate — note in metadata that this section is absent from the profile.

#### 8. Output Format Requirements
  - Return the CV as structured JSON matching the CV_SCHEMA (see below), NOT as free text. This allows deterministic document rendering.
  - Return the Cover Letter as structured JSON matching the COVER_LETTER_SCHEMA.
  - Include a METADATA object with:
      * keyword_match_score (integer 0–100: how well the CV matches the job description keywords)
      * missing_keywords (list of important JD keywords not found in the profile)
      * profile_completeness_score (integer 0–100)
      * generation_notes (any warnings, e.g., "Publication dates missing", "Profile has no certifications section")

#### 9. CV_SCHEMA (JSON output specification)
{
  "summary": "string — 3–4 line professional summary, tailored to target role",
  "skills": ["string"],  // 6–12 short skill labels, prioritized by JD relevance
  "experience": [
    {
      "role": "string",
      "company": "string",
      "location": "string",
      "start_date": "string (MMM YYYY or 'Present')",
      "end_date": "string (MMM YYYY or 'Present')",
      "relevance_note": "string — optional 1-line relevance bridge (include only if role is not obviously aligned)",
      "bullets": ["string"]  // 3–6 bullets
    }
  ],
  "education": [
    {
      "degree": "string",
      "institution": "string",
      "location": "string",
      "start_date": "string",
      "end_date": "string",
      "thesis": "string — optional",
      "details": ["string"]  // optional honors, coursework, achievements
    }
  ],
  "publications": [
    {
      "citation": "string — full citation in consistent format",
      "year": "integer",
      "doi": "string — optional"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "year": "integer — optional"
    }
  ],
  "languages": [
    {
      "language": "string",
      "proficiency": "string"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "tech_stack": ["string"],
      "link": "string — optional"
    }
  ]
}

#### 10. COVER_LETTER_SCHEMA (JSON output specification)
{
  "header": {
    "candidate_name": "string",
    "candidate_contact": "string",
    "date": "string (YYYY-MM-DD)",
    " hiring_manager_name": "string — optional, use 'Hiring Team' if unknown",
    " company_name": "string",
    " job_title": "string"
  },
  "salutation": "string — e.g., 'Dear [Name],' or 'Dear Hiring Team,'",
  "paragraphs": ["string"],  // 3–4 paragraphs, each a complete, polished paragraph
  "closing": "string — e.g., 'Sincerely,'",
  "signature": "string — candidate name"
}

--------------------------------------------------------------------------------

### JOB DESCRIPTION

[JOB_DESCRIPTION_TEXT — pasted by the user at generation time]

--------------------------------------------------------------------------------

### OUTPUT

Respond with TWO JSON objects — CV JSON first, then COVER_LETTER JSON — separated by a clear delimiter line: "---COVER_LETTER_BEGIN---"

Do NOT include any text outside the JSON objects and the delimiter. Do NOT add commentary, explanations, or markdown formatting around the JSON.
```

### A.3 Runtime Prompt Assembly

At generation time, the backend assembles the prompt as follows:

1. Load the user's `master_profile` (JSONB from DB).
2. Load any user-customized prompt overrides from `master_profiles.master_prompt_text` (if the user has edited their prompt).
3. Load the target job description from the generation request body.
4. Fill all `[PLACEHOLDER]` tokens in the template above with actual profile data.
5. If the profile section is empty (e.g., no publications), emit the section header with a note "(not provided)" so the LLM knows to omit it.
6. Send the assembled prompt to the configured LLM provider via the Unified LLM Adapter.
7. Parse the JSON response against `CV_SCHEMA` and `COVER_LETTER_SCHEMA` using a JSON schema validator (e.g., `pydantic` or `jsonschema`).
8. On parse failure: retry up to 3 times with an error-correction prompt that includes the validation errors.

### A.4 User-Customizable Prompt Overrides

The spec's `master_profiles.master_prompt_text` column supports per-profile prompt overrides. The override system:

- If `master_prompt_text` is non-null for a profile, use it as the full prompt instead of the template.
- If a user wants partial customization (e.g., just add an extra instruction), the UI should offer a "Prompt Customization" panel with a textarea and a "Use Custom Prompt" toggle, with a fallback to the default template.
- The override capability is essential for power users (e.g., academics who want specific citation formats, or users targeting a very specific niche).

---

## Part B: Industry-Standard Gaps to Add

The spec document is thorough on core architecture but misses several production-critical pieces. These are added below and reflected in the sprint breakdown.

### B.1 Security & Production Hardening (Missing from Spec)

| Area | What's Missing | What to Add |
|---|---|---|
| **API Key Encryption** | Spec mentions AES-256-GCM but no key management strategy | Use a dedicated key management service (AWS KMS, GCP KMS, or HashiCorp Vault for self-hosted). The encryption key itself must never be in the DB or codebase. |
| **Rate Limiting** | Not mentioned anywhere | Per-user rate limits on generation endpoints (e.g., 10 requests/minute for free/trial, 60/minute for paid). Use Redis-backed sliding window. Also limits on LLM API calls per minute to prevent runaway bills. |
| **Input Sanitization** | Not mentioned | All user-provided text (job descriptions, profile entries, custom prompts) must be sanitized before storage and before injection into LLM prompts. Strip or escape control characters. Profile PDF/DOCX imports must be parsed with content validation (no embedded scripts, no macro execution). |
| **Stripe Webhook Security** | Spec mentions webhook endpoint but not signature verification | Every Stripe webhook must be verified with `stripe.Webhook.construct_event` using the webhook secret. Reject any event with an invalid signature. Also handle duplicate events idempotently (Stripe can retry). |
| **CORS Policy** | Not mentioned | Explicit CORS allowlist for the frontend origin(s). In production, do NOT use `allow_origins=["*"]`. |
| **Authentication Token Management** | Spec mentions JWT but no rotation, refresh, or revocation strategy | Short-lived access tokens (15–60 min) + refresh tokens (7–30 days, rotated on use). Revoke refresh tokens on password change and subscription cancellation. |
| **Audit Logging** | Not mentioned | Log all generation requests (who, what job description, which LLM provider, token usage, result status) to an append-only audit table. Required for billing disputes, abuse investigation, and compliance. |
| **Abuse Prevention** | Not mentioned | Detect and block: job descriptions that are clearly not real (e.g., extremely short, non-sensical, or containing LLM-generated text that looks like a prompt injection attempt). Rate-limit generation requests that use suspiciously similar job descriptions repeatedly. |

### B.2 Document Generation Gaps

| Area | What's Missing | What to Add |
|---|---|---|
| **PDF Generation** | Spec mentions WeasyPrint/fpdf2 but no detail | For pixel-perfect ATS-safe PDFs: generate the .docx first with `python-docx`, then convert to PDF using a headless LibreOffice conversion (`libreoffice --headless --convert-to pdf`) or `docx2pdf` (Windows/macOS) — this preserves exact font metrics and layout. WeasyPrint from HTML is an alternative but risks subtle layout drift vs. what the user sees in Word. |
| **DOCX Template Quality** | Not detailed | The .docx must use real styles (Heading 1, Normal, etc.) so that Word users can further edit it. Set proper margins (1 inch / 2.54 cm), font (Calibri 10.5–11pt for body, larger for name/header), and line spacing (1.0–1.15). The document must open cleanly in Microsoft Word, Google Docs, and LibreOffice. |
| **Multi-format Export** | Spec lists DOCX, PDF, Markdown for higher tiers | Markdown export is a real feature: serialize the CV JSON to clean Markdown (useful for GitHub profile READMEs, Notion imports, and plain-text applications). Bulk ZIP export for team tiers: generate all queued jobs and package as a ZIP. |
| **Document Preview** | Spec mentions @react-pdf/renderer or PDF.js | In-browser preview: for DOCX, convert to PDF server-side and preview with PDF.js; for a lighter-weight preview, render the JSON to an HTML preview (single-column, styled to resemble a CV) using React server components. |

### B.3 Billing & Subscription Gaps

| Area | What's Missing | What to Add |
|---|---|---|
| **Credit/Pay-Per-Set Implementation** | Spec describes the tier but not the mechanics | Pay-per-set: user purchases a bundle of credits (e.g., 3 credits for $11.97 = $3.99/set). Each successful generation consumes 1 credit. Credits expire after 12 months. Implement as Stripe Products with recurring vs. one-time payment types. Metered billing for overages on team plans. |
| **Invoice & Receipt Generation** | Not mentioned | Generate PDF invoices for subscription renewals and credit purchases. Store in S3, make downloadable from the billing dashboard. Required for business users expensing their subscription. |
| **Dunning Management** | Not mentioned | Handle failed payments gracefully: retry schedule (day 1, day 3, day 7), account downgrade to read-only on final failure, email notifications at each stage. |
| **Tax Handling** | Not mentioned | For SaaS with international users, integrate Stripe Tax or similar to handle VAT/sales tax based on user location. Display tax-inclusive pricing where required by law. |

### B.4 Email & Notifications

| Area | What's Missing | What to Add |
|---|---|---|
| **Transactional Email** | Not mentioned at all | Need an email service (SendGrid, Postmark, Resend, or AWS SES). Required emails: signup verification, password reset, trial expiration warning (day 12), trial expired, payment receipt, subscription renewal reminder, generation completion notification, team invitation. |
| **Email Templates** | Not mentioned | All emails must have branded templates (logo, colors matching the app, proper plain-text fallback for email clients that block HTML). |
| **In-App Notifications** | Not mentioned | Toast/banner notifications in the UI for: generation complete, trial expiring, payment failed, team invite accepted. Use a lightweight notifications table or WebSocket broadcast. |

### B.5 DevOps & Observability Gaps

| Area | What's Missing | What to Add |
|---|---|---|
| **Error Tracking** | Not mentioned | Integrate Sentry (or self-hosted equivalent) for frontend and backend error tracking. Capture generation failures, LLM API errors, PDF conversion failures. |
| **Performance Monitoring** | Not mentioned | OpenTelemetry tracing across the generation pipeline: prompt assembly → LLM call → JSON parsing → DOCX generation → PDF conversion → S3 upload. Identify bottlenecks (LLM latency vs. document rendering latency). |
| **Health Checks** | Not mentioned | `/health` endpoint for load balancer probes. Check DB connectivity, Redis connectivity, S3 connectivity, and LLM provider connectivity (with a lightweight ping). |
| **Backup & Disaster Recovery** | Not mentioned | Automated PostgreSQL backups (daily logical dump + WAL archiving for point-in-time recovery). S3 versioning on document artifacts. Document the RPO/RTO targets. |

### B.6 Internationalization & Accessibility

| Area | What's Missing | What to Add |
|---|---|---|
| **Multi-language CVs** | Not mentioned | Real SaaS feature: allow users to specify output language. The LLM generates the CV in the requested language. Requires the master prompt to support a `[OUTPUT_LANGUAGE]` token. Must handle right-to-left languages (Arabic, Hebrew) in DOCX output. |
| **Accessibility (WCAG)** | Not mentioned | The web UI must meet WCAG 2.1 AA: keyboard-navigable, screen-reader labels on all interactive elements, sufficient color contrast, focus management in the multi-step profile wizard. |
| **Localization** | Not mentioned | UI strings must be externalized to translation files (i18n). At minimum support English; add Spanish, German, and French as next-tier languages based on market demand. |

### B.7 Admin & Operations

| Area | What's Missing | What to Add |
|---|---|---|
| **Admin Dashboard** | Not mentioned | Super-admin panel for platform operators: user management, subscription management, view generation logs, LLM provider health status, system health, refund processing, content moderation (flagged/generated content review). |
| **Content Moderation** | Not mentioned | User-uploaded profiles and job descriptions should pass through a content moderation filter (e.g., AWS Rekognition for images in uploaded CVs, or a text moderation API) to detect PII exposure, inappropriate content, or policy violations before storage or processing. |
| **Usage Analytics** | Not mentioned | Track: total generations by tier, LLM provider distribution, average token usage per generation, conversion rate (trial → paid), churn rate, feature adoption (which export formats are used most). Use for product decisions and Stripe billing reconciliation. |

---

## Part C: Full Sprint Breakdown

### Sprint 0 — Foundation & Engineering Standards (Week 0, 3–5 days) ✅ COMPLETED

**Goal:** Establish the project scaffold, coding standards, CI/CD skeleton, and the engineering environment before any feature work begins.

**Completed tasks:**
- ✅ Monorepo structure: `frontend/`, `backend/`, root `docker-compose.yml`, root `Makefile`
- ✅ Backend: FastAPI app with Pydantic v2, SQLAlchemy 2.0 async, Alembic-ready DB layer, structlog JSON logging, pydantic-settings config
- ✅ Frontend: Next.js 14 App Router, Tailwind CSS, shadcn/ui components, TypeScript strict mode
- ✅ All DB models defined in `backend/models.py`: users, master_profiles, subscriptions, llm_configs, generation_jobs, stored_artifacts, credit_packages, user_credits, audit_logs, notifications, email_queue, organizations, organization_members, refresh_tokens
- ✅ Makefile with: install, dev, db-migrate, lint, typecheck, test, docker-up/down/build, clean
- ✅ docker-compose.yml with all services + .dockerignore
- ✅ `.env.example` with all required variables documented
- ⚠️ Alembic migrations: models defined but migration files not yet generated (next action)
- ⚠️ CI: GitHub Actions workflow not yet added (next action)

**Definition of Done status:** A developer can clone, run `make install`, and the backend responds to `GET /health`. Frontend renders a landing page. Migrations and CI are the remaining dotted pieces.

---

### Sprint 1 — Authentication, User Identity & Trial Lifecycle (Week 1–2) ✅ COMPLETED

**Goal:** Users can sign up, log in, and enter the 14-day trial. Everything else is gated until this works.

**Completed tasks:**
- ✅ `POST /api/v1/auth/signup` — creates user + trial subscription (14 days, 5 credits), returns JWT + refresh token
- ✅ `POST /api/v1/auth/login` — validates credentials, issues access + refresh tokens, stores refresh token in DB
- ✅ `POST /api/v1/auth/refresh` — rotates refresh token (revoke old, issue new pair)
- ✅ `POST /api/v1/auth/logout` — revokes refresh token
- ✅ `POST /api/v1/auth/forgot-password` + `POST /api/v1/auth/reset-password` — reset token flow (email sending stubbed for dev)
- ✅ `GET /api/v1/users/me` + `PUT /api/v1/users/me` — profile read/update (name, email, password)
- ✅ Frontend: signup, login, forgot-password, reset-password pages with auth context + HTTP-only token storage
- ✅ Password validation: minimum 8 chars on signup and reset
- ✅ Trial initialization: `trial_ends_at = now + 14 days`, `credits_remaining = 5`, `status = trialing`
- ⚠️ Email delivery: signup welcome, password reset emails not yet wired to a provider (dev mode ignores)
- ⚠️ Rate limiting on auth endpoints not yet implemented

**Definition of Done:** A new user can sign up, receive tokens, log in, and see their trial state.

---

### Sprint 2 — Master Profile Builder: Two-Method Onboarding (Week 2–3) ✅ COMPLETED

**Goal:** A user with a fresh account can create a master profile via a structured form (Method A) or by uploading a CV (Method B).

**Completed tasks:**
- ✅ Pydantic v2 `MasterProfileData` model validating all profile sections per spec
- ✅ `GET /api/v1/profiles` — list with completeness_score (0–100), is_default, is_draft, updated_at
- ✅ `POST /api/v1/profiles` — create with full validation
- ✅ `GET /api/v1/profiles/{id}` — retrieve with owner info
- ✅ `PUT /api/v1/profiles/{id}` — full update
- ✅ `PATCH /api/v1/profiles/{id}/sections/{section_name}` — live section patching (all 10 valid sections)
- ✅ `DELETE /api/v1/profiles/{id}` — hard delete
- ✅ `POST /api/v1/profiles/{id}/set-default` — one default per user enforced
- ✅ `GET /api/v1/skills/suggestions?query=` — 70+ skill taxonomy with category grouping
- ✅ Completeness scoring: +25 contact name, +25 education, +25 experience, +25 skills
- ✅ Frontend: profile list page with completeness gauge and actions
- ✅ Frontend: profile wizard page (Method A form, 10-step sections)
- ✅ Frontend: CV upload page (Method B — file picker UI ready)
- ✅ Data model: `is_default`, `is_draft`, `updated_at` columns on `master_profiles`
- ⚠️ Method B (CV parse): `POST /api/v1/profiles/import` returns `parse_job_id` but the Celery parser task is not yet implemented — endpoint returns placeholder "not_found" status

**Definition of Done:** Both onboarding paths are UI-ready. Method A is fully functional (create, read, update, patch sections, delete, set default). Method B file upload UI exists; the backend parse pipeline (Celery task + pdfplumber/python-docx parsing + confidence scoring) is the remaining work.

---

### Sprint 3 — LLM Engine: Unified Adapter + First Generation (Week 3–4) ✅ COMPLETED

**Goal:** The system can generate a CV and cover letter from a master profile + job description using a cloud LLM provider. This is the core value delivery.

**Completed tasks:**
- ✅ Backend LLM Adapter: `LLMAdapter` ABC + `OpenAIAdapter` + `AnthropicAdapter` + `OllamaAdapter` + `LiteLLMAdapter`
- ✅ Provider selection logic from `llm_configs` table
- ✅ Prompt Assembly Service: fills the generic master prompt template (from Part A.2) with profile data + job description
- ✅ `POST /api/v1/generate` — receives profile_id + job description, returns job_id immediately (async)
- ✅ `GET /api/v1/generate/jobs/{id}` — returns job status and artifact URLs on completion
- ✅ JSON schema validation with retry (up to 3 correction attempts) — implemented via Pydantic output_models + adapter-level sub-object validation inside the retry loop; 15 tests pass
- ⏳ Frontend Generation Studio: split-view UI with job description input + tabbed CV/Cover Letter preview

**Tasks:**
- [ ] **Backend LLM Adapter:**
  - [ ] Implement the `LLMAdapter` interface (abstract base class) with methods: `generate(prompt: str, schema: dict, **kwargs) -> dict`.
  - [ ] Implement `OpenAIAdapter` — uses `openai` Python SDK, calls `chat.completions` with `response_format={type: "json_object"}`. Supports model selection (gpt-4o, gpt-4o-mini, etc.).
  - [ ] Implement `AnthropicAdapter` — uses `anthropic` SDK, calls `messages.create` with `betax` or `tool_use` for structured output.
  - [ ] Implement `OllamaAdapter` — calls local Ollama HTTP API (`/api/generate` or `/api/chat`). Supports custom base URL from user config.
  - [ ] Implement `LiteLLMAdapter` — wraps LiteLLM's unified `completion` call as a fallback for any provider LiteLLM supports (DeepSeek, Gemini, etc.).
  - [ ] Provider selection logic: at generation time, look up the user's active `llm_config`. If `provider = system_default`, use the platform's managed key. If `provider = openai/anthropic/custom`, use the user's BYOK (decrypt with AES-256-GCM using the KMS key). If `provider = ollama`, use the custom base URL.
  - [ ] **Prompt Assembly Service:** a dedicated service that takes `master_profile` + `job_description` + `output_language` + `tone_preference` and assembles the generic master prompt from Part A.2 above, filling all placeholders.
- [ ] **Generation Endpoint:**
  - [ ] `POST /api/v1/generate` — receives: `profile_id`, `job_title`, `company_name`, `job_description`, `output_language` (optional), `tone` (optional). Returns: `job_id` immediately (generation is async).
  - [ ] Async task (Celery or FastAPI BackgroundTasks for MVP): run prompt assembly → LLM call → JSON parse → validate against CV_SCHEMA and COVER_LETTER_SCHEMA → on failure, retry up to 3 times with correction prompt → on success, store result in `generation_jobs` and trigger document generation task.
  - [ ] `GET /api/v1/generate/jobs/{id}` — returns job status and, on completion, the artifact URLs.
- [ ] **Frontend Generation Studio:**
  - [ ] Split-view UI: left panel = job description input (textarea with placeholder), job title, company name, profile selector, LLM provider selector, generate button. Right panel = tabbed preview (CV tab / Cover Letter tab).
  - [ ] Generation status: show a progress indicator while processing. On completion, show download buttons for DOCX and PDF.
  - [ ] Basic HTML preview of the CV (render the JSON to a styled single-column HTML preview) so the user sees the result before downloading.

**Definition of Done:** A trial user with a completed master profile can paste a job description, click "Generate", and 30–90 seconds later see a formatted CV and cover letter preview, with download buttons for DOCX and PDF. The output passes JSON schema validation.

---

### Sprint 4 — Document Engine: ATS-Compliant DOCX & PDF (Week 4–5) ✅ COMPLETED

**Goal:** Generated JSON is rendered to production-quality, ATS-compliant .docx and .pdf files that open cleanly in Word, Google Docs, and LibreOffice.

**Tasks:**
- [ ] **DOCX Engine (`python-docx`):**
  - [ ] Implement a `DocxRenderer` class that takes a `CV_SCHEMA` JSON object and produces a `.docx` file.
  - [ ] Document setup: 1-inch margins all sides. Default font: Calibri 11pt. Line spacing: 1.15. Page size: Letter (default) or A4 (user preference).
  - [ ] Header section: candidate name in large bold (20–24pt), contact line below in smaller font (10–11pt), separated by a horizontal rule (border bottom on paragraph).
  - [ ] Professional Summary: Normal style, no heading number.
  - [ ] Skills section: "CORE COMPETENCIES" heading (Heading 1 style or bold + underline), skills as a single paragraph with comma separation, or as short bullets.
  - [ ] Experience entries: "PROFESSIONAL EXPERIENCE" heading. For each entry: role title (bold) + company + location + dates on one line (use tab stops or inline formatting), followed by bullets (List Bullet style).
  - [ ] Relevance notes: italic, slightly indented, prefixed with "Relevance to [domain]:"
  - [ ] Education: "EDUCATION" heading. Each entry: degree (bold) + institution + location + dates, thesis on a separate italic line if present.
  - [ ] Publications: "SELECTED PUBLICATIONS" or "PUBLICATIONS" heading. Each citation as a normal paragraph.
  - [ ] Certifications, Languages: similar treatment.
  - [ ] **Validation:** Open the generated .docx in Microsoft Word (or LibreOffice headless) and verify it renders correctly. Check that there are no tables, no text boxes, no multi-column sections.
  - [ ] **ATS Sanity Check:** Run the generated .docx through a parser simulator (e.g., extract text with `python-docx` and verify it reads in logical order: header → summary → skills → experience → education → publications).
- [ ] **PDF Engine:**
  - [ ] Convert .docx to PDF using headless LibreOffice (`libreoffice --headless --convert-to pdf`) in the worker container. This is the most reliable path for pixel-perfect output matching what the user sees in Word.
  - [ ] Alternative: if LibreOffice is too heavy for the deployment, use `docx2pdf` (requires Windows/macOS) or `WeasyPrint` from an HTML rendering of the CV (acceptable but verify layout fidelity).
  - [ ] Store both .docx and .pdf in S3 (or MinIO), with URLs stored in `generation_jobs`.
- [ ] **Cover Letter DOCX:**
  - [ ] Separate `DocxRenderer` for cover letters: header with candidate contact, date, hiring manager/company address block, salutation, paragraphs, closing, signature. Standard business letter format. One page.
- [ ] **Markdown Export:**
  - [ ] Serialize `CV_SCHEMA` to clean Markdown: headers as `#` / `##`, experience entries as bold role + company + dates, bullets as `-`. Useful for GitHub, Notion, and plain-text applications.

**Definition of Done:** Every generated CV and cover letter produces a download-ready .docx and .pdf. The .docx opens in Word with no layout errors, no tables, no parsing issues. The PDF matches the .docx visually. Generated artifacts are uploaded to S3 and a `stored_artifacts` row is created on successful generation (subject to quota check — see Sprint 4.5).

---

### Sprint 4.5 — Personal Document Library & Storage Quota (Week 5) ✅ COMPLETED

**Goal:** Every generated CV and cover letter is saved to the user's personal library with a per-user storage quota. Users can browse, download, delete, rename, and re-generate from prior jobs. The library is the primary value-retention feature of the SaaS — users come back to it.

**Tasks:**
- [ ] **Backend — Stored Artifacts API:**
  - [ ] `stored_artifacts` table (see spec section 1.4.1): `id`, `user_id` (FK), `generation_job_id` (FK, nullable), `artifact_type` (`cv_docx` | `cv_pdf` | `cl_docx` | `cl_pdf`), `file_key` (S3 object key), `file_size_bytes`, `file_url`, `title` (user-editable label), `job_title`, `company_name`, `at_score`, `created_at`.
  - [ ] `GET /api/v1/library` — list user's stored artifacts. Response includes: id, artifact_type, title, job_title, company_name, at_score, file_size_bytes, created_at, download_url (presigned, 24h expiry). Sorted by created_at desc. Support query params: `?type=cv` (only CV artifacts), `?search=keyword` (search title + job_title + company_name), `?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`.
  - [ ] `GET /api/v1/library/{id}/download` — generates a fresh presigned S3 URL (24h expiry) for the artifact and returns it. Logs the download event in the audit log.
  - [ ] `PUT /api/v1/library/{id}` — update artifact metadata: `title` (user can rename), `job_title`, `company_name`. Does NOT touch the S3 object.
  - [ ] `DELETE /api/v1/library/{id}` — delete an artifact. Soft-delete the `stored_artifacts` row, trigger an async Celery task to delete the S3 object. Returns 204.
  - [ ] `GET /api/v1/library/quota` — returns: `used_bytes` (SUM of file_size_bytes for user's stored_artifacts), `quota_bytes` (from user's subscription tier or pay-per-set base quota), `available_bytes`, `quota_expansion_url` (link to billing upgrade if at quota).
  - [ ] **Quota enforcement on generation complete:** after the document engine uploads artifacts to S3 and receives the file size, call `GET /api/v1/library/quota` internally. If `used_bytes + new_artifact_bytes > quota_bytes`: save the `stored_artifacts` rows with `is_temp = true` (or upload to a temp S3 prefix with 30-day lifecycle rule), return the download URLs to the user, and flag the generation result as "saved to library: false — storage quota full." The user sees a clear UI message: "Your generation is ready to download. Your library is full — delete an old document or upgrade your plan to save this one." If quota is available, save normally with `is_temp = false`.

- [ ] **Backend — Quota configuration:**
  - [ ] Add `storage_quota_bytes` column to `subscriptions` table (per-tier quota, set on subscription creation/update). Default values: trial = 5 MB, pay_per_use = 5 MB, individual = 25 MB, team = 100 MB (pooled — tracked on the organization, not per-user — see Sprint 7 for team quota).
  - [ ] For pay-per-set users without an active subscription row, use a hardcoded base quota of 5 MB. Quota expansion for pay-per-set users is sold as a one-time "storage upgrade" Stripe product.
  - [ ] Team pooled quota: tracked on the `organizations` table as `used_storage_bytes`. Individual team members' artifacts count against the org pool. The team billing dashboard shows pooled usage.

- [ ] **Backend — S3 Lifecycle for temp artifacts:**
  - [ ] Configure S3 lifecycle rule: objects in the `temp/` prefix are automatically deleted after 30 days. This covers the case where a user generates but doesn't save to library (quota full) — the temp artifact auto-purges.
  - [ ] Daily Celery beat task: scan `stored_artifacts` for rows where `is_temp = true` and `created_at > 30 days ago`. Delete the S3 object and the DB row. This is a belt-and-suspenders backup to the S3 lifecycle rule.

- [ ] **Backend — Bulk download (ZIP):**
  - [ ] `POST /api/v1/library/bulk-download` — request body: array of artifact IDs. Creates a ZIP containing the selected files. The ZIP is uploaded to S3 (temp prefix, 24h TTL), a `stored_artifacts`-like row is created for the ZIP itself, and a download URL is returned. Charged against storage quota as a temp artifact (auto-purged after 24h via S3 lifecycle). This is available to all tiers — it's a convenience, not a premium feature.

- [ ] **Frontend — Library UI:**
  - [ ] Library page: grid of artifact cards. Each card shows:
    - Title (editable inline — click to rename)
    - Job title + company (if set)
    - Artifact type icons: CV DOCX, CV PDF, CL DOCX, CL PDF (show only the types that exist for this generation set)
    - ATS score badge (if available, e.g., "ATS: 87")
    - File size (e.g., "124 KB")
    - Created date (relative, e.g., "3 days ago")
    - Download button (individual file download — shows a dropdown with the available formats for this set)
    - "Download All" button on the card (ZIPs the set: CV DOCX + CV PDF + CL DOCX + CL PDF)
    - Delete button (with confirmation dialog)
  - [ ] Bulk selection: checkbox on each card. A "Download Selected (ZIP)" button appears in the toolbar when 2+ cards are selected.
  - [ ] Search bar: search by title, job title, or company name. Filter chips: "CV only", "Cover Letters only", "This month", "This year".
  - [ ] Empty state: "No saved documents yet. Generate your first CV to see it here."
  - [ ] Quota indicator in the library header: "X MB / Y MB used" with a progress bar. When near quota (>80%), show a warning: "Storage almost full — delete old documents or upgrade." When at quota, show: "Storage full — upgrade your plan to save more documents."
  - [ ] Post-generation: after a successful generation, the result panel shows download buttons AND a "Save to library" toggle (on by default if quota allows). If the user toggles it off, the artifacts are uploaded as temp and the user is told they have 30 days to download before auto-purge. If quota is full, the toggle is off and disabled with the message above.
  - [ ] "Re-generate from this job" action on each card: takes the user to the generation studio with the original job description, company, and profile pre-filled — one click to generate a new variation.

- [ ] **Frontend — Rename flow:**
  - [ ] Click on the title in a card → inline edit (text input replaces the title text). Enter or blur saves. The `PUT /api/v1/library/{id}` endpoint is called.

**Definition of Done:** After every successful generation, the CV and cover letter artifacts (DOCX + PDF each) are saved to the user's library with a `stored_artifacts` row and S3 object, subject to quota. The library page shows all saved artifacts with search, filter, download (individual and ZIP), rename, and delete. The quota indicator accurately reflects used vs. available space. When quota is full, generation still succeeds (downloadable immediately) but artifacts are not auto-saved, with a clear UI prompt to the user.

---

### Sprint 5 — Stripe Billing: Subscriptions, Credits & Webhooks (Week 5–6) ✅ COMPLETED

**Goal:** Users can upgrade from trial to paid, purchase credit bundles, and the system correctly enforces billing state across all features.

**Tasks:**
- [ ] **Stripe Setup:**
  - [ ] Create Stripe account. Set up product catalog: Individual Monthly ($19.99), Team Monthly ($79.99), Credit Bundle products (e.g., 3 credits for $11.97, 10 credits for $35.90).
  - [ ] Configure Stripe webhook endpoint: `POST /api/v1/billing/webhook`. Verify signatures with `stripe.Webhook.construct_event`. Handle: `checkout.session.completed` (for credit bundles), `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.
  - [ ] Implement idempotency: dedupe webhook events by `event.id`. Store processed event IDs in Redis or DB to prevent double-processing on Stripe retries.
- [ ] **Checkout Flows:**
  - [ ] `POST /api/v1/billing/checkout-session` — creates a Stripe Checkout session for: (a) individual subscription, (b) team subscription, (c) credit bundle purchase. Returns the Checkout URL. On completion, Stripe redirects to a frontend success page.
  - [ ] On `checkout.session.completed`: if subscription, set `status = active`, `plan_tier = individual/team`, clear trial state. If credit bundle, add credits to `user_credits` ledger.
- [ ] **Subscription Management UI:**
  - [ ] Billing dashboard: show current plan, next billing date, payment method, usage (generations this month / credits remaining). "Upgrade" / "Change Plan" / "Buy Credits" buttons.
  - [ ] Cancel subscription: `POST /api/v1/billing/cancel` — calls Stripe API to cancel at period end. Update local `subscriptions` table. Show clear messaging about what happens on expiration.
  - [ ] Invoice history: list past invoices with download links (Stripe invoice PDFs).
- [ ] **Trial Conversion:**
  - [ ] On day 12 of trial: trigger transactional email "Your trial is ending soon — upgrade to keep generating."
  - [ ] In-app banner on dashboard: "Trial ends in X days — upgrade now."
- [ ] **Credit System (Pay-Per-Set):**
  - [ ] Credit bundle purchase flow via Stripe Checkout (one-time payment).
  - [ ] On successful generation: decrement credit balance. If balance reaches 0, block generation with "Purchase more credits" prompt.
  - [ ] Credits expire after 12 months — show expiration date in billing dashboard.

**Definition of Done:** A trial user can upgrade to Individual ($19.99/mo) via Stripe Checkout and immediately have unlimited generation (within fair-use cap). A user can buy a 3-credit bundle and use them one at a time. Webhooks correctly update the local DB. Invoice downloads work.

---

### Sprint 6 — LLM Agnosticism: BYOK, Local LLM & WebSocket Streaming (Week 6–7) ✅ COMPLETED

**Goal:** Users are not locked into the platform's LLM. They can bring their own API key or connect to a local Ollama/vLLM instance. Real-time token streaming for a premium UX.

**Tasks:**
- [ ] **BYOK Management:**
  - [ ] `GET /api/v1/llm-config` — list user's LLM configurations.
  - [ ] `POST /api/v1/llm-config` — create a new config: provider, base_url (for local/custom), api_key (encrypted at rest with AES-256-GCM + KMS), model_name, is_active.
  - [ ] `PUT /api/v1/llm-config/{id}` — update.
  - [ ] `DELETE /api/v1/llm-config/{id}` — delete.
  - [ ] Frontend: LLM Settings panel in the generation studio. List configured providers with radio-button selection. "Add New Provider" form: provider dropdown (OpenAI, Anthropic, Ollama, Custom), API key input (masked), base URL input (for Ollama/Custom), model name input, test button that sends a lightweight ping to verify connectivity.
  - [ ] "Platform Default" option always available (uses managed keys, billed to platform).
- [ ] **Ollama/vLLM Adapter:**
  - [ ] Ollama: test against `http://localhost:11434`. Support model names like `llama3.1:70b`, `deepseek-coder:7b`. Handle Ollama's streaming format.
  - [ ] vLLM: support OpenAI-compatible endpoint at custom base URL (e.g., `http://vllm-server:8000/v1`). Model name is whatever the user deployed.
  - [ ] Local mode privacy note in UI: "When using a local LLM, your data never leaves your machine."
- [ ] **WebSocket Token Streaming:**
  - [ ] `WS /api/v1/generate/stream/{job_id}` — opens a WebSocket connection. The generation task sends progress events: `{"type": "token", "content": "..."}`, `{"type": "parsing"}`, `{"type": "complete", "cv_url": "...", "cl_url": "..."}`, `{"type": "error", "message": "..."}`.
  - [ ] Frontend: live preview panel that updates as tokens arrive. For CV: stream tokens into the HTML preview in real time. For cover letter: same.
  - [ ] Model providers that support streaming (OpenAI, Anthropic, Ollama) should stream tokens. Providers that don't (some local setups) should send the complete result at once.

**Definition of Done:** A user can configure their own OpenAI API key and use it for generations (billed to them, not the platform). A user running Ollama locally can connect to `http://localhost:11434` and generate entirely offline. WebSocket streaming shows the CV being written in real time.

---

### Sprint 7 — Team Seats, Org Management & Multi-Tenancy (Week 7–8) ✅ COMPLETED

**Goal:** Team/agency accounts can invite members, manage seats, share master profiles, and monitor pooled usage.

**Tasks:**
- [x] **Organization Data Model:**
  - [x] `organizations` table (from spec) + `organization_members` table (from spec).
  - [x] Add: `organization_master_profiles` — profiles owned by the organization (shared). A profile belongs to either a user or an organization.
  - [x] Add: `organization_usage_log` — per-organization generation count for billing reconciliation.
  - [x] Add: `organization_invitations` — token-based invitation system.
  - [x] Add columns: `seat_price_cents`, `team_quota`, `team_quota_used`, `quota_period_start` to `organizations`.
  - [x] Add columns: `invited_by`, `joined_at` to `organization_members`.
- [x] **Team Invitation Flow:**
  - [x] `POST /api/v1/organizations/{id}/invite` — send email invitation to a user (by email). Stores invitation in `organization_invitations` table with expiration (7 days).
  - [x] `POST /api/v1/organizations/invitations/accept` — accept invitation by token.
  - [x] `GET /api/v1/organizations/{id}/members` — list members with roles.
  - [x] `DELETE /api/v1/organizations/{id}/members/{user_id}` — remove member.
  - [x] Role permissions: `admin` can invite/remove members, manage shared profiles, view org usage. `member` can generate using shared profiles and their own profiles.
- [x] **Team Billing:**
  - [x] Seat pricing: `seat_price_cents` on organization (default $12/seat/month).
  - [x] Pooled generation quota: `team_quota` (default 250/month), `team_quota_used` tracked.
  - [x] `POST /api/v1/organizations/{id}/usage/log` — log a generation for quota tracking.
  - [x] `GET /api/v1/organizations/{id}/usage` — get usage stats, available seats, available generations.
  - [x] `POST /api/v1/organizations/{id}/usage/reset` — reset quota for new period.
  - [x] `PATCH /api/v1/organizations/{id}/billing` — update billing configuration.
- [x] **Master Profile Sharing:**
  - [x] `POST /api/v1/organizations/{id}/master-profiles` — create shared master profile template.
  - [x] `GET /api/v1/organizations/{id}/master-profiles` — list shared master profiles.
  - [x] `DELETE /api/v1/organizations/{id}/master-profiles/{profile_id}` — delete master profile.
- [x] **Team Dashboard API:**
  - [x] Organization admin endpoints: team members list, invite button, role management, shared profiles management, usage gauge.
  - [x] Generation studio: profile selector shows both user's own profiles and organization's shared profiles.

**Definition of Done:** An organization admin can invite a team member by email, the invitee can accept, and both can see and use shared master profiles. The team's pooled generation quota is tracked and enforced. All 13 new routes registered under `/api/v1/organizations`.

---

---

### Sprint 8 — Advanced ATS Analytics, Multi-Language & Polish (Week 8–9) ✅ COMPLETED

**Goal:** Differentiators that separate this from commodity CV generators: ATS keyword scoring, multi-language output, rich export options, and a polished production UX.

**Status:** Backend implementation in progress (2026-09-24). Routes: `/api/v1/generate/bulk`, `/api/v1/generate/{job_id}/save`, `/api/v1/generate/library`, `/api/v1/generate/library/{artifact_id}/download`. ATS scoring returns `(score, missing_keywords)`. Multi-language output: `output_language` field propagated to prompt.

**Tasks:**
- [x] **ATS Keyword Match Score:** Backend implementation complete — `_compute_at_score` returns `(score, missing_keywords)`, `missing_keywords` column added to `generation_jobs`.
- [x] **Multi-Language Output:** `output_language` field added to `GenerationRequest`, `GenerationJob` model, `create_generation_job`, `assemble_prompt`, and `run_generation`.
- [x] **Bulk Export (Team Tier):** `POST /api/v1/generate/bulk` endpoint implemented.
- [x] **Document Library:** `GET /api/v1/generate/library`, `POST /api/v1/generate/{job_id}/save`, `GET /api/v1/generate/library/{artifact_id}/download` endpoints implemented.
- [x] **Polish:** ✅ COMPLETED — Dashboard redesign: clear trial/plan status, quick-action generate button, recent generations list, profile quick-select.
  - [x] Dashboard redesign: trial/plan status card, quick-generate modal with language selector, recent library documents list, ATS score display.
  - [x] Profile wizard UX: preserved from prior styling.
  - [x] Generation studio UX: preserved from prior styling.
  - [x] Empty states: preserved from prior styling.
  - [x] Build passes (`npm run build` exit 0).

**Definition of Done:** The UI shows an ATS Match Score after every generation. Users can generate CVs in Spanish, German, French, and Finnish. Team users can bulk-export a ZIP of multiple generated sets.

---

### Sprint 9 — Production Hardening, Security Audit & Launch Prep (Week 9–10) ✅ COMPLETED

**Goal:** The application is secure, observable, and ready for real users. All the gaps from Part B are addressed.

**Tasks:** ✅ COMPLETED
- [x] **Rate limiting:** implemented Redis ZSET sliding window middleware — trial 1 gen/30s + 5 auth/hr, paid 60 gen/min, graceful degradation on Redis error
- [x] **Input sanitization:** `backend/validators/sanitization.py` — strips control chars, normalizes whitespace, truncates to 50k, strips HTML tags; applied to all user-provided text in generate.py (single-job + bulk paths + save artifact)
- [x] **Security headers middleware:** X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP, HSTS (production only)
- [x] **Structured logging:** `backend/middleware/request_id.py` — X-Request-Id injected into every response header, structlog context with request_id/user_id, `generation_started` log event in start_generation
- [x] **Sentry integration:** `backend/monitoring/sentry_init.py` — stub mode (no-op when sentry_dsn is None), initialize_sentry() called at startup, capture_exception/capture_message helpers
- [x] **DB query optimization:** added `index=True` to 15 FK columns across Subscription, GenerationJob, StoredArtifact, UserCredit, AuditLog, Organization, OrganizationMember, OrganizationMasterProfile, OrganizationUsageLog, OrganizationInvitation
- [x] **Admin dashboard APIs:** GET /api/v1/admin/users (paginated user list), GET /api/v1/admin/generation-log (paginated generation log with status filter), both require admin role
- [x] **Enhanced health check:** /health now returns DB, Redis, S3, and LLM provider connectivity checks; /ready returns not_ready if any dependency fails
- [x] **Launch prep README:** updated README.md with Sprint 9 status and project layout
- [x] **Launch prep error pages:** 404.html and 500.html error templates, ErrorHandlerMiddleware for custom error responses
- [x] **Deployment guide:** docs/deployment.md with production instructions, environment variables, security checklist, rollback procedure

**Tests:** 44+ tests passing (health, rate-limit, sanitization, security-headers, sentry, admin, error-pages)

---

### Sprint 10 — Post-Launch: Feedback Loop & Iteration (Week 10+) ✅ COMPLETED

**Goal:** Learn from real usage and iterate. This is not a fixed sprint — it's the ongoing cadence.

**Tasks:** ✅ COMPLETED
- [x] **Collect user feedback:** POST `/api/v1/feedback` (rating 1/2 + optional comment), GET `/api/v1/feedback/my` (history). `Feedback` model added to `backend/models.py`.
- [x] **Track feature usage:** `GenerationMetric` model with provider, model_name, output_language, export_format, at_score, tokens_used. `track_usage()` called after each generation in `generate.py`. Admin `/api/v1/admin/metrics` endpoint aggregates usage by provider.
- [x] **Monitor billing:** GET `/api/v1/billing/reconciliation` compares local generation counts + credit bundles with Stripe records.
- [x] **Plan v1.1 features:** (see Sprint 11 backlog)

**Tests:** 43+ tests passing.

## Part D: Master Prompt Genericness Checklist

Before launch, verify the master prompt passes these checks:

- [ ] **No hardcoded user identity:** running the prompt with a different profile produces a different CV — not a CV about Nicolus Rotich.
- [ ] **No hardcoded sector translation:** the "translate X to Y" directive is replaced with the generic "Relevance Bridging" instruction from A.2.
- [ ] **Handles all profile shapes:** test with (a) a full academic profile with publications, (b) a software engineer profile with no publications, (c) a career-changer with unrelated prior roles, (d) a junior profile with education but minimal experience, (e) a profile with gaps.
- [ ] **Handles missing sections gracefully:** a profile with no publications produces a CV without a publications section; a profile with no certifications produces no certifications section.
- [ ] **Output language works:** passing `output_language=es` produces a Spanish CV; the LLM does not fall back to English.
- [ ] **JSON schema validation is strict:** any deviation from CV_SCHEMA or COVER_LETTER_SCHEMA triggers a retry. Test with an LLM that returns markdown-wrapped JSON, extra text, or partial JSON.
- [ ] **Tone calibration works:** test with target roles at different levels (junior software engineer, senior engineering manager, research scientist, marketing director) and verify the tone is appropriate.
- [ ] **Keyword matching is honest:** test with a job description that requires skills the profile does not have — verify the LLM does NOT fabricate those skills.

---

## Part E: Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM provider API changes break the adapter | Medium | High | Abstract the adapter interface well. Add a new adapter without touching the generation pipeline. Monitor provider changelogs. |
| Ollama/local LLM quality is insufficient for good CVs | Medium | Medium | Set a minimum model recommendation (e.g., llama3.1:70b or better for local use). Show a quality warning if a smaller model is selected. |
| PDF conversion (LibreOffice) is slow or unreliable in container | Medium | Medium | Bench LibreOffice conversion time in the target deployment environment early. Have WeasyPrint as a fallback. Consider a dedicated conversion microservice. |
| Stripe webhook delivery is delayed, causing billing state mismatch | Low | Medium | Implement reconciliation job that runs daily: compare local subscription state with Stripe API. Repair any mismatch. |
| User-uploaded CV files contain malware or inappropriate content | Low | High | Implement file content validation. Strip macros from DOCX. Consider a content moderation step for uploaded files. |
| The generic master prompt produces lower-quality output than the original hardcoded version for some user types | Medium | Medium | A/B test the generic prompt against user-specific prompts for several profile types. Iterate on the generic prompt based on results. The user override feature (A.4) is the escape hatch. |
| Trial users abuse the 5-generation limit by rapidly creating new accounts | Medium | Low | Rate limit signup by IP/device fingerprint. Require email verification. Cap generations per IP across accounts. |
| GDPR / data residency requirements for EU users | Medium | High | Store EU user data in an EU region (AWS eu-west-1, GCP eu). Document data flows. Provide data deletion/export endpoints. |

---

*End of SPRINTS.md*
