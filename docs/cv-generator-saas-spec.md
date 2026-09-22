# Software Requirement Specification (SRS)
## CareerForge AI: Multi-Tier, Model-Agnostic CV & Cover Letter Generation Platform

**Document Version:** 1.0.0  
**Author:** Lead Systems Architect  
**Date:** September 22, 2026  
**Status:** Approved for Implementation  

---

## 1. Executive Summary & Vision

### 1.1 Product Overview
**CareerForge AI** is a career intelligence and management system that happens to generate ATS-compliant CVs and Cover Letters as one of its outputs. It is not a document factory — it is a Career Operating System. The platform parses user master profiles alongside target job descriptions to produce customized, job-aligned application suites in downloadable Word (`.docx`) and PDF formats, but the CV generation is one node in a larger system that includes gap analysis, salary intelligence, market demand heatmaps, interview preparation, application tracking, and an outcome feedback loop that learns what works over time. The user's relationship with the product is ongoing, not transactional.

### 1.2 Business Objectives & Key Features
* **Career Operating System, Not a Document Factory:** CareerForge is a career intelligence and management system that happens to generate ATS-compliant CVs as one of its outputs. The CV generation is one node in a system — not the system itself. The user's relationship is ongoing: build a living profile → use the intelligence layer to understand market position → generate a CV + cover letter → track the application → prepare for the interview → record the outcome → the system learns.
* **Hybrid Monetization:** Pay-per-set (pay-as-you-go credit system) and monthly recurring subscription model.
* **Freemium Entry Point (Job Post Analyzer):** A free, no-account-required tool where any visitor can paste a job description and receive a breakdown: required skills, implied skills, red flags, salary estimate, and company research summary. This demonstrates the system's intelligence and funnels users into the profile-building flow.
* **14-Day Free Trial:** Full access to individual tier capabilities with usage limits during the trial window.
* **Multi-Tenancy & Tiers:** Individual user seats and Organization/Team seats with centralized billing and shared template management. **Note:** Team/agency tier is a Phase 3+ feature. The MVP focuses on the individual product; team seats are a distribution expansion, not a product differentiator.
* **LLM Agnosticism:** Complete provider flexibility, enabling users or enterprise admins to route requests to cloud APIs (OpenAI, Anthropic, Gemini, DeepSeek) or local/private hosted models (Ollama, vLLM, LM Studio).
* **ATS-Optimized Output:** Deterministic document builder ensuring 100% ATS compliance without visual obstacles, tables, or unparseable elements.
* **Two-Method Profile Onboarding + LinkedIn Sync:** Users create their master profile either by (1) filling out a structured web form, (2) uploading an existing CV file which the system parses and pre-fills, or (3) connecting LinkedIn for one-click profile pre-fill with ongoing sync option.
* **Intelligence Layer (Core Product, Not Add-On):** Before generating anything, the system tells the user something they didn't know: gap analysis vs. target role (which skills appear in 80%+ of real postings for the role they want), salary intelligence by skill combination, market demand heatmap (which of their skills are growing vs. declining in demand), and positioning advice (how to reframe their existing experience for a target domain without lying). This requires ongoing data ingestion and analysis — the defensible moat.
* **Interview Preparation (Core Product, Not Add-On):** Role-specific interview question prediction (15–20 questions calibrated to the actual role), simulated interview mode with LLM-evaluated feedback, and a STAR story bank parsed from the user's profile that surfaces the most relevant stories for predicted questions.
* **Personal Document Library:** Every generated CV and Cover Letter is saved to the user's personal library with a per-user storage quota (5 MB default; expandable with paid tiers). Users can browse, download, delete, and re-generate from prior jobs.
* **Outcome Feedback Loop:** After each application, the user records the outcome (interview, rejection, no response) with one click. Over time, the system learns which profile framings, keyword choices, and cover letter angles correlate with positive outcomes. This is the AI-era moat — a system that gets better the more a user uses it. Outcome reporting is low-friction and not required for core generation to work.

---

## 1.3 Account vs. Profile: Architectural Separation

CareerForge AI maintains a strict separation between the **Account** and the **Master Profile**. These are distinct entities with different purposes, data shapes, and lifecycle management.

### 1.3.1 The Account (Identity & Billing)

The Account is the top-level tenant entity. It owns billing, authentication, subscription state, and usage quotas. It does NOT contain CV content.

| Field | Purpose |
|---|---|
| `id` (UUID) | Primary key |
| `email` | Unique login identifier |
| `password_hash` | BCrypt/Argon2 hashed password (null for OAuth-only accounts) |
| `full_name` | Display name used in the UI (not the CV name — that lives in the profile) |
| `role` | `'user'`, `'org_admin'`, `'super_admin'` |
| `created_at` | Account creation timestamp |

**Account-owned tables (foreign key = `user_id`):**
- `subscriptions` — Stripe linkage, plan tier, trial state, credits
- `llm_configs` — BYOK API keys, local endpoint URLs
- `generation_jobs` — history of all generation requests
- `stored_artifacts` — library of saved CVs and cover letters (see 1.4)

The account does NOT store education, work experience, skills, publications, or any CV content. That lives exclusively in the Profile.

### 1.3.2 The Master Profile (CV Content)

The Master Profile is the structured data the master prompt consumes. A user can have multiple profiles (e.g., one for industry roles, one for academic roles, one per career direction). Each profile is a self-contained, canonical JSON document.

| Field | Purpose |
|---|---|
| `id` (UUID) | Primary key |
| `user_id` (FK → users) | Owner |
| `title` | User-given label (e.g., "Senior Engineer Profile", "Academic Profile") |
| `profile_data` (JSONB) | The full structured CV content: contact, education, experience, skills, publications, certifications, languages, projects |
| `master_prompt_text` (TEXT, nullable) | Optional per-profile prompt override (see SPRINTS.md Part A.4) |
| `created_at` | Profile creation timestamp |
| `updated_at` | Last edit timestamp |

**`profile_data` JSONB schema** (validated on write via Pydantic):

```json
{
  "contact": {
    "full_name": "string",
    "location": "string",
    "phone": "string (nullable)",
    "email": "string (nullable)",
    "linkedin": "string (nullable)",
    "website_portfolio": "string (nullable)"
  },
  "summary": "string (3–4 line professional summary, optional — can be auto-generated at generation time)",
  "education": [
    {
      "degree": "string",
      "institution": "string",
      "location": "string (nullable)",
      "start_date": "string (YYYY or MMM YYYY)",
      "end_date": "string (YYYY or MMM YYYY or 'Present')",
      "thesis": "string (nullable)",
      "details": ["string"]  // honors, coursework, relevant notes
    }
  ],
  "experience": [
    {
      "role": "string",
      "company": "string",
      "location": "string (nullable)",
      "start_date": "string (MMM YYYY or 'Present')",
      "end_date": "string (MMM YYYY or 'Present')",
      "relevance_note": "string (nullable — auto-filled by LLM at generation time, not stored here)",
      "bullets": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],      // grouped technical skills
    "domain": ["string"],         // domain-specific knowledge
    "tools": ["string"],          // software, platforms, languages
    "soft": ["string"]            // soft skills
  },
  "publications": [
    {
      "citation": "string",
      "year": "integer",
      "doi": "string (nullable)",
      "link": "string (nullable)"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "year": "integer (nullable)"
    }
  ],
  "languages": [
    {
      "language": "string",
      "proficiency": "string (e.g., Native, Fluent, Intermediate, Basic)"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "tech_stack": ["string"],
      "link": "string (nullable)"
    }
  ],
  "additional_info": "string (nullable — awards, volunteer work, interests, anything else)"
}
```

A profile is considered **complete** when it has at minimum: `contact.full_name`, at least one `education` entry, at least one `experience` entry, and a non-empty `skills` group. The UI surfaces a completeness indicator to drive users toward a usable profile.

---

## 1.4 Personal Document Library & Storage Quota

Every completed generation produces two artifacts: a CV (`.docx` + `.pdf`) and a Cover Letter (`.docx` + `.pdf`). These are stored in the user's personal library, not discarded after download.

### 1.4.1 Stored Artifacts Table

```sql
CREATE TABLE stored_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    generation_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    artifact_type VARCHAR(20) NOT NULL,  -- 'cv_docx', 'cv_pdf', 'cl_docx', 'cl_pdf'
    file_key VARCHAR(500) NOT NULL,      -- S3 object key
    file_size_bytes INT NOT NULL,
    file_url VARCHAR(500) NOT NULL,      -- presigned or permanent download URL
    title VARCHAR(255) NOT NULL,         -- user-given or auto-generated label
    job_title VARCHAR(255),
    company_name VARCHAR(255),
    at_score INT,                        -- ATS match score from generation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 1.4.2 Storage Quota

| Tier | Quota | Notes |
|---|---|---|
| Trial | 5 MB | Approximately 10–15 document sets (CV + CL, DOCX + PDF each) |
| Pay-Per-Set | 5 MB | Same base quota; users with large libraries can purchase quota upgrades |
| Individual | 25 MB | Approximately 50–75 document sets |
| Team | 100 MB (pooled) | Shared across organization members; admins can see usage breakdown |

Quota enforcement: before saving a new artifact, the system checks `SUM(file_size_bytes)` for the user against their quota. If the new artifact would exceed the quota, the generation still succeeds (the user can download immediately) but the artifact is NOT auto-saved to the library — the user sees a "Storage full — delete an old document or upgrade to save this one" prompt. Artifacts in S3 that are not saved to the library are purged after 30 days (matching the spec's data retention policy).

Quota expansion: higher tiers or add-on purchases increase the quota. The billing system charges for quota upgrades as one-time or recurring charges via Stripe.

### 1.4.3 Library UI

The library screen shows a grid/list of all saved document sets. Each card shows:
- Title (editable by user)
- Job title + company (if provided at generation time)
- Artifact type icons (CV + CL, DOCX + PDF)
- ATS score (if available)
- File size
- Date created
- Download buttons (individual files or "Download All" as ZIP)
- Delete button (with confirmation)

Users can search/filter by job title, company, or date range.

---

## 1.5 Two-Method Profile Creation

A user reaching the platform for the first time has no profile. The platform offers two paths to create one. Both paths result in a `master_profiles` row with a validated `profile_data` JSONB.

### Method A: Structured Web Form (Manual Entry)

The user fills out a multi-step wizard that captures every field the master prompt requires. This is the canonical, highest-quality path — the user has full control over every field.

**Steps:**

1. **Contact Information** — Full name (required), location (required), phone (optional), email (optional — the account email is used if this is left blank), LinkedIn URL (optional), portfolio/website URL (optional).

2. **Professional Summary** — A free-text 3–4 line summary. The UI offers a "Help me write this" button that calls the LLM with the profile data so far to draft a summary, which the user can edit. Optional — can be auto-generated at generation time if left blank.

3. **Education** — Add one or more entries. Each entry: degree, institution, location (optional), start year, end year (or "Present" for current), thesis/dissertation title (optional, for academic profiles), details/ honors (optional, bulleted).

4. **Work Experience** — Add one or more entries. Each entry: role title, company, location (optional), start date (MMM YYYY), end date (MMM YYYY or "Present"), bullet points (3–6 recommended, free text). The UI enforces chronological order (newest first) and validates date formats.

5. **Skills** — Three sub-groups:
   - Technical Skills (e.g., Python, TensorFlow, CFD)
   - Domain Knowledge (e.g., Process Modeling, Separation Technology)
   - Tools & Platforms (e.g., ANSYS, Git, Linux)
   - Soft Skills (e.g., Cross-functional Coordination, Mentorship)
   Each group is a tag-like input with autocomplete suggestions drawn from a built-in taxonomy (seeded from common CV skills, expandable). Users can add free-form tags that don't match the taxonomy.

6. **Publications** (optional) — Add one or more entries. Each: full citation text, year, DOI (optional), link (optional). The UI accepts raw citation text and does not attempt to parse it — the user provides the formatted citation.

7. **Certifications** (optional) — Name, issuer, year (optional).

8. **Languages** (optional) — Language name, proficiency level (Native / Fluent / Intermediate / Basic / Conversational).

9. **Projects** (optional) — Name, description, tech stack (tags), link (optional).

10. **Additional Info** (optional) — Free text for anything not covered: awards, volunteer work, interests, professional memberships.

At any point the user can **Save as Draft** (profile is usable but marked incomplete) or **Save & Finish** (profile is marked complete if all required fields are present).

**Validation on save:**
- `contact.full_name` must be non-empty.
- At least one `education` entry with non-empty `degree` and `institution`.
- At least one `experience` entry with non-empty `role` and `company`.
- `skills` must have at least one non-empty group.
- Dates must be parseable (the system accepts "2019", "Feb 2019", "February 2019", "Present" for end_date).
- Each experience bullet must be non-empty (stripped).

Invalid fields are highlighted in the UI with specific error messages. The profile is NOT saved until validation passes (or the user explicitly saves as draft with a warning).

### Method B: CV File Upload & Parse (Pre-fill)

The user uploads an existing CV file (PDF or DOCX). The system parses it, extracts the structured data, pre-fills the profile form (Method A's wizard), and the user reviews every field before saving.

**Why this is a first-class method, not a shortcut:** PDF/DOCX parsing is imperfect. The system must never silently accept incorrect parsed data. Every parsed field lands in the form as pre-filled values that the user must explicitly review. Fields that the parser could not extract are left empty with a visual indicator ("Not detected in uploaded file").

**Supported file formats:**
- PDF (text-based — not scanned images; see "Scanned PDFs" below)
- DOCX (Microsoft Word format)

**File size limit for upload:** 10 MB per file. The parser processes the file in a Celery task (not inline) to avoid blocking the request.

**Parsing pipeline:**

1. **File validation:** Check file type by content (magic bytes), not extension. Reject files that are not valid PDF or DOCX. Strip any macros, scripts, or embedded objects from DOCX before parsing (security).

2. **Text extraction:**
   - PDF: Use `pdfplumber` (preferred for table-aware extraction) or `pymupdf` (faster, fallback). Extract text per page, preserve reading order.
   - DOCX: Use `python-docx`. Extract paragraphs in document order. Extract bullet lists. Extract table contents as flat text (since CVs sometimes use tables for skills or education — the parser flattens them).

3. **Section segmentation:** Apply heuristics to identify CV sections from extracted text:
   - Look for standard section headers: "Experience", "Education", "Skills", "Summary", "Publications", "Certifications", "Languages", "Projects", "Work History", "Professional Experience", "Academic Background", etc. (case-insensitive, with fuzzy matching for slight variants)
   - Text between headers is assigned to the preceding section.
   - Text before the first recognized header goes to "contact" + "summary" candidates.

4. **Entity extraction per section:**

   **Contact** (from top-of-document text before first section header):
   - Name: First non-empty line that looks like a person name (heuristic: 2–4 words, title case, no numbers). Flag as "low confidence" if ambiguous.
   - Phone: Regex for international and local phone formats. Extract the first match.
   - Email: Regex for email pattern. Extract the first match.
   - Location: Text between name and contact details that looks like a city/country.
   - LinkedIn: URL matching `linkedin.com/in/...`.
   - All extracted contact fields are flagged with confidence levels in the UI.

   **Education entries:** Look for institution names (known universities list + heuristic: proper noun + "University"/"College"/"Institute"), degree types (BEng, BSc, MSc, MA, PhD, DBA, etc.), and date ranges near the institution. Each candidate entry is structured as `{degree, institution, location, start_date, end_date, thesis}`. Multiple entries are supported.

   **Experience entries:** Look for company names (heuristic: proper noun followed by location or date), role titles (text before company name on the same line or preceding line), date ranges (MMM YYYY – MMM YYYY pattern), and bullet points (lines starting with bullet characters, dashes, or numbered lists). Each candidate entry is `{role, company, location, start_date, end_date, bullets}`.

   **Skills:** Extract comma-separated lists, bulleted lists, or table contents that appear under a "Skills"/"Core Competencies"/"Technical Skills" header. Split on commas, semicolons, newlines, and bullets. Clean each item (trim whitespace, remove trailing punctuation).

   **Publications:** Look for citation-style entries (author names, journal names, years in parentheses, DOI patterns `doi: 10.xxxx/xxxxx`). Group into individual publication entries.

   **Certifications, Languages:** Similar pattern matching under their respective headers.

5. **Confidence scoring:** Each extracted field carries a confidence score (high / medium / low). High-confidence fields (e.g., email regex match, clear date pattern) are pre-filled without a flag. Medium-confidence fields are pre-filled with a subtle "review" indicator. Low-confidence fields are pre-filled but prominently flagged for manual review.

6. **Pre-fill into the form:** The parsed data populates Method A's wizard fields. The user opens the wizard at the first step that has data (or at Contact if contact was parsed). Every field shows the parsed value as the initial value. Fields not detected are empty. The user edits, adds, removes, and corrects as needed, then saves.

7. **Scanned PDFs (images with no text layer):** The system attempts OCR using `pytesseract` (or cloud OCR as a paid upgrade) on each page. OCR quality for CVs is variable. Extracted text from OCR gets the same parsing pipeline but all fields are flagged as "low confidence — OCR source." The user is shown a prominent notice: "This file appears to be a scanned image. Parsed data may be inaccurate — please review every field carefully." If OCR fails entirely (no text extracted), the user is told to use a text-based PDF or DOCX instead, or to enter their profile manually.

**Post-parse review UI:**
- The form wizard opens with parsed values pre-filled.
- A banner at the top: "We pre-filled your profile from the uploaded file. Please review every section before saving."
- Each field that was parsed with medium or low confidence has a small warning icon. Hovering shows: "Extracted from uploaded file — confidence: medium/low. Please verify."
- Fields not detected in the file are empty with a note: "Not found in uploaded file."
- The user can switch to a different uploaded file (re-parse) or go back to manual entry at any point.
|- Save is disabled until the user has explicitly reviewed the profile (the UI tracks which sections have been viewed; saving requires all sections to have been opened at least once, or the user to explicitly confirm "I have reviewed all sections").

### Method C: LinkedIn Profile Sync (One-Click Pre-Fill)

The user connects their LinkedIn account (via OAuth). The system pulls their LinkedIn profile data — experience, education, skills, summary — and uses it as a starting point for the master profile. This is a one-time sync with an optional ongoing sync that can pull updates periodically.

**Why this is a first-class method:** Most users have a LinkedIn profile; few have a structured CV. LinkedIn sync removes the data-entry friction for Method A dramatically. It is the second growth lever after the Job Post Analyzer.

**Flow:**
1. User clicks "Import from LinkedIn" → redirected to LinkedIn OAuth → authorizes → redirected back.
2. System pulls profile data via LinkedIn API: experience entries, education entries, skills, headline/summary, location, contact info.
3. Mapped to `profile_data` JSONB structure. LinkedIn data is mapped with medium confidence by default (LinkedIn profiles are self-reported and may be less structured than a CV).
4. The Method A wizard opens with LinkedIn data pre-filled. The user reviews, corrects, and saves.
5. Optional: user enables "ongoing sync" — the system periodically pulls LinkedIn updates and surfaces them as pending changes for the user to review.

**Data mapping:**
- LinkedIn "Experience" → `experience[]` entries
- LinkedIn "Education" → `education[]` entries
- LinkedIn "Skills" → `skills.technical[]` and `skills.tools[]` (mapped heuristically)
- LinkedIn "About" / headline → `summary` draft (editable)
- LinkedIn location → `contact.location`

**Limitations:** LinkedIn does not expose publications, certifications, languages, or projects in a structured way. These sections are left empty with a note: "Not available from LinkedIn — add manually."

---

### 1.6 Job Post Analyzer (Freemium Entry Point)

A free, no-account-required tool accessible at a public URL (e.g., `/analyzer`). Any visitor can paste a job description and receive an immediate breakdown without creating an account or providing any personal data.

**What the analyzer returns:**
- **Required skills:** Extracted from the JD — hard skills, tools, platforms, languages explicitly required.
- **Implied skills:** Skills not stated but strongly implied by the role context (e.g., a "Senior ML Engineer" JD that mentions "production pipelines" implies MLOps, Docker, CI/CD).
- **Red flags:** Vague requirements ("fast-paced environment"), unrealistic skill combinations, or signs the JD was written by someone who doesn't understand the role.
- **Salary estimate:** Based on the role, location (if mentioned), and required skill combination — sourced from aggregated market data.
- **Company research summary:** If the company name is extractable from the JD or URL, a brief summary of the company's domain, size indicators, and recent news.
- **Keyword coverage preview:** If the user has an account and a profile, the analyzer shows which of their skills already match the JD and which are missing.

**Why this works as a growth lever:** It requires zero commitment from the visitor. It demonstrates the intelligence the system has. The natural next step: "Want a CV tailored to this exact posting? Connect your profile." The profile can be built via Method B (upload existing CV) in under 2 minutes, or Method A/C for everyone else.

**Pricing:** Free, unlimited use. No account required. If the user is logged in, the analyzer also shows personal keyword coverage. If not logged in, it shows only the JD analysis.

---

### 1.7 Intelligence Layer

The intelligence layer is the core differentiator. Before generating anything, the system tells the user something they didn't know about their market position. This is defensible because it requires ongoing data ingestion and analysis — not just a prompt.

**Components:**

#### 1.7.1 Gap Analysis vs. Target Role

Given the user's profile and a target role (or job description), compare the profile against a database of real job postings for that role. Show:
- "You're missing these 4 skills that appear in 80%+ of postings for this role. Here's how the market describes them. Here's a learning path."
- Skills the user has that are rare for this role (differentiation opportunities).
- Skills the user has that are over-reported for this role (Potential redundancy).

The comparison is against real postings, not generic advice. The system maintains a corpus of job descriptions ingested from public sources and APIs.

#### 1.7.2 Salary Intelligence

"People with your profile + these 3 additional skills command $X–$Y more in Helsinki/Remote/EU. Here's the data."

Salary data is presented by skill combination, not just by job title. The system shows:
- Base salary range for the target role in the target location.
- Premium for each additional skill the user has or could add.
- Salary trend direction (growing/steady/declining) for the role.

#### 1.7.3 Market Demand Heatmap

For each skill in the user's profile, show:
- Posting volume trend over the last 12 months (growing, stable, declining).
- "Your CFD simulation skill is in 3x more postings this year than last year. Your MATLAB skill is in 40% fewer."
- Skills most commonly paired with each of the user's skills (co-occurrence data).

#### 1.7.4 Positioning Advice

"Your profile currently reads as a chemical engineer. If you want to move into ML engineering, here's exactly how to reframe your existing experience so it reads as ML-adjacent without lying."

This is the generalized "quant to industry" translation from the original master prompt — automated and available on demand. The system identifies the gap between the user's current framing and the target role's framing, then suggests specific rewording for experience bullets and skills ordering.

#### 1.7.5 Data Ingestion Pipeline (Required for Intelligence Layer Freshness)

The intelligence layer depends on fresh data. The system maintains a scheduled ingestion pipeline that:
- Pulls job postings from public sources, APIs, and partnerships on a daily/weekly schedule.
- Extracts skills, salary ranges, location, and role labels from each posting.
- Aggregates into the analytics database that backs the intelligence layer.
- Flags stale data: if a skill's posting volume hasn't been updated in 30 days, the UI shows a "data may be stale" notice.

**Staleness risk:** If the data is stale, the intelligence layer becomes misleading, which destroys trust. Freshness is a quality attribute, not a nice-to-have. The ingestion pipeline must be operational before the intelligence layer is exposed to users.

---

### 1.8 Interview Preparation

The generation is only halfway. The interview is where the job is won or lost. The interview prep module is a core product feature, not an add-on.

#### 1.8.1 Role-Specific Interview Question Prediction

From the job description + company + role level, predict the 15–20 questions the user is most likely to face. Not generic "tell me about yourself" — specific technical and behavioral questions calibrated to the actual role.

- Technical questions: derived from the required skills and domain in the JD.
- Behavioral questions: derived from the soft skills and company context.
- Role-level calibration: junior roles get more foundational questions; senior roles get more system-design and leadership questions.

#### 1.8.2 Simulated Interview Mode

The user practices answers to predicted questions. The system evaluates their responses using the same LLM pipeline and gives specific feedback:
- "You covered the technical detail well but didn't connect it to business impact — here's how to reframe."
- "Your answer was strong on X but didn't address Y, which is a key requirement in the JD."

The simulated interview can be text-based (user types answers) or voice-based (user speaks, system transcribes and evaluates) depending on UX resources.

#### 1.8.3 STAR Story Bank

The user's profile is parsed into STAR-format stories (Situation, Task, Action, Result). Before an interview, the system surfaces the most relevant stories for the predicted questions. The user doesn't have to remember — it's all in the system.

- Each experience bullet in the profile is analyzed for STAR components.
- Stories are tagged by competency (leadership, technical problem-solving, cross-functional coordination, etc.).
- Before an interview, the system recommends the top 3–5 stories to prepare for the predicted questions.

---

### 1.9 Outcome Feedback Loop

After each application, the user records the outcome. This feeds a learning system that improves generation quality over time.

**Flow:**
1. After generating a CV + cover letter for a specific job, the system creates an "application" record linked to the generation job.
2. The user tracks the application through the application tracker (see 1.10).
3. When the outcome is known, the user clicks one of: "Got interview," "No response," "Rejected," "Offered."
4. The outcome is stored with the generation job and the profile framing used.
5. Over time, the system learns which profile framings, keyword choices, cover letter angles, and skill orderings correlate with positive outcomes.

**Implementation notes:**
- Outcome reporting is one-click and low-friction. It is NOT required for core generation to work.
- The system can start with market data (intelligence layer) and add personal outcome learning over time as the user base grows.
- Privacy: outcome data is personal — it is not shared, aggregated, or used for the B2B intelligence products without explicit opt-in.

---

### 1.10 Application Tracker (Career Operating System Component)

A lightweight application tracker integrated with generation — not a separate tool the user has to switch to. Every job application they make feeds back into the living profile.

**Features:**
- Add an application: job title, company, date applied, link to JD, profile framing used (which profile variant), cover letter used.
- Status tracking: Applied → Interviewing → Offered / Rejected / No response.
- One-click outcome reporting (links to 1.9).
- Timeline view: all applications, sorted by date, with status indicators.
- Re-generate from an application: takes the user back to the generation studio with the original JD, company, and profile pre-filled.

**Relationship to the living profile:** Every application and its outcome feeds back into the profile's learning data. The profile gets sharper over time — not a static document maintained once a year.

---

### 1.11 Side-Cars & Output Format Suite

These are entry points, growth levers, and revenue expansion features. They are not the core product but extend its reach.

#### 1.11.1 Output Formats Beyond DOCX/PDF

| Format | Use Case | Tier |
|---|---|---|
| Plain text (email body) | Direct email applications | All tiers |
| Markdown | GitHub READMEs, Notion imports, plain-text applications | Individual+ |
| Notion export | Notion workspace integration | Individual+ |
| LaTeX | Academic CVs | Individual+ |
| Obsidian export | Personal knowledge management | Individual+ |

Each format opens a use case the core DOCX/PDF doesn't cover. Academic users need LaTeX. Tech users want Markdown. People applying via email need a plain-text version.

#### 1.11.2 AI-Era Resume Review (Standalone Paid)

User uploads their existing CV. System gives a detailed review: ATS compatibility score, keyword coverage vs. a role they specify, tone analysis, gaps, specific rewrite suggestions. This is a lower-friction entry point than full generation — users who aren't ready to build a profile can still get value.

#### 1.11.3 Career Pivot Compass

User says "I want to move from X to Y." System maps the gap, identifies transferable skills, suggests the most efficient path (which skills to build, which roles to target as stepping stones, which companies are known to hire from X into Y). High-value for career changers — the most anxious and motivated user segment.

#### 1.11.4 "What Should I Learn Next?"

Given the user's profile and a target role, recommend 2–3 specific skills to build, with a concrete project to do, a time estimate, and resources. Updated as the market changes. Continuous engagement — users come back monthly.

#### 1.11.5 Multi-CV Strategy

A user targeting 3 different role types (e.g., ML engineer, data scientist, research scientist) maintains 3 profile framings from the same underlying data. The system manages the variants. Power user feature — real professionals target multiple role types. Most generators force one CV.

#### 1.11.6 GitHub/Portfolio Importer

Connect GitHub, pull repos, languages, contribution history, project descriptions. Auto-map to profile's skills and projects sections. Makes the profile genuinely rich, not self-reported. Engineers and technical users have rich GitHub data.

---

## 1.12 Generated Document Storage Lifecycle

1. **Generation completes** → CV JSON and Cover Letter JSON are rendered to `.docx` and `.pdf` by the document engine.
2. **Artifacts are uploaded to S3** → `stored_artifacts` rows are created with `file_size_bytes` from the S3 head object.
3. **Quota check** → If the user has enough quota, artifacts are permanently saved. If not, artifacts are uploaded to a temporary S3 location with a 30-day TTL and the user is prompted to free up space or upgrade.
4. **Download** → User downloads from the library or immediately after generation. Each download generates a presigned S3 URL (24-hour expiry for security).
5. **Deletion** → User deletes an artifact from the library → `stored_artifacts` row is deleted → S3 object is deleted (async, via Celery task).
6. **Purge** → A daily Celery beat task scans for `stored_artifacts` rows where the associated generation job was not "saved" and the artifact was uploaded more than 30 days ago → deletes the S3 object and the DB row.

### 2.1 Pricing & Tier Structure

| Feature / Tier | **Free** (Job Post Analyzer) | Pay-Per-Set (Micro-transaction) | Individual Seat (Subscription) | Team / Agency Seat (Subscription) |
| :--- | :--- | :--- | :--- | :--- |
| **Price Point** | $0 (no account required) | $3.99 - $5.99 per set | $19.99 / month (after trial) | $79.99 / month (includes 5 seats) + $12/extra seat |
| **What's Included** | Job post analysis: required skills, implied skills, red flags, salary estimate, company research. No CV generation. | 1 Set (1 CV + 1 Cover Letter) per credit. DOCX & PDF exports. | Unlimited generations (fair-use cap: 50 sets/mo). DOCX, PDF, Markdown. Intelligence layer, interview prep, library, application tracker. | Shared pooled quota (250 sets/mo). DOCX, PDF, Markdown, Bulk ZIP. Centralized org profiles, admin dashboard, team analytics. |
| **Trial Period** | N/A (always free) | N/A | 14-Day Free Trial (Max 5 generations) | 14-Day Free Trial (Max 15 generations across team) |
| **Generations** | None (analysis only) | 1 Set per credit purchased | Unlimited (Fair-use cap: 50 sets/mo) | Shared pooled quota (250 sets/mo) |
| **LLM Provider** | N/A (analysis uses LLM internally) | Cloud Default (Host-provided) | Cloud Default or Custom API Keys | Custom API Keys, Local vLLM/Ollama, Custom Host |
| **Master Prompts** | N/A | Standard Profile | Multiple Master Profiles | Centralized Org Profiles, Brand Guidelines |
| **Intelligence Layer** | Basic JD analysis only | N/A | Full: gap analysis, salary intelligence, market demand heatmap, positioning advice | Full, shared across org |
| **Interview Prep** | N/A | N/A | Full: question prediction, simulated interview, STAR story bank | Full, shared across org |
| **Export Formats** | None (analysis only) | DOCX & PDF | DOCX, PDF, Plain Markdown | DOCX, PDF, Markdown, Bulk ZIP Export |
| **Team Management** | N/A | N/A | Single User | Admin Dashboard, Role Permissions, Shared Analytics |

**Note:** Team/agency tier is a Phase 4 feature. The MVP focuses on the individual product (Free + Pay-Per-Set + Individual). The free tier (Job Post Analyzer) is the entry point — it requires no account, demonstrates the system's intelligence, and funnels users into the profile-building flow.

### 2.2 Trial Lifecycle Logic
1. **Onboarding:** User signs up via OAuth or Email/Password. Trial state initialized with `trial_ends_at = NOW() + 14 DAYS` and `trial_credits_remaining = 5`.
2. **Credit Check Middleware:** Intercepts generation requests. If `now < trial_ends_at` and `trial_credits > 0`, execution proceeds.
3. **Conversion Trigger:** On Day 12, automated transactional emails and in-app banners prompt subscription confirmation.
4. **Expiration Handling:** Upon trial expiry, account degrades to `Read-Only` mode (existing CV downloads remain accessible; new generations require payment method attachment).

### 2.3 Stripe / Payment Gateway Integration
* **Webhook Architecture:** Event-driven listening for `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_succeeded`, and `checkout.session.completed`.
* **Metered Usage Billing:** Overage billing configured via Stripe Usage Records for teams exceeding their base monthly generation caps.

---

## 3. Model-Agnostic LLM Engine Design

### 3.1 LLM Abstraction Layer (Unified Gateway)
To prevent provider lock-in and enable air-gapped local execution, the system implements a unified `LLMAdapter` interface built on LiteLLM / LangChain principles.

```
                   +----------------------------------+
                   |    Master Prompt Pipeline Engine |
                   +----------------------------------+
                                    |
                                    v
                   +----------------------------------+
                   |       Unified LLM Adapter        |
                   +----------------------------------+
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
        v                           v                           v
+---------------+           +---------------+           +---------------+
| OpenAI / v1   |           | Anthropic v1  |           | Ollama / Local|
| API Driver    |           | Claude Driver |           | vLLM Driver   |
+---------------+           +---------------+           +---------------+
```

### 3.2 Provider Configuration Interface
Users and Team Admins can choose their execution target:
1. **Platform Default (Managed):** Uses system-managed API keys (OpenAI GPT-4o / Claude 3.5 Sonnet) billed via platform credits.
2. **Bring Your Own Key (BYOK):** Users provide their own API keys (encrypted at rest using AES-256-GCM).
3. **Self-Hosted / Local LLM:** Users specify a custom base URL (e.g., `http://localhost:11434` or private `http://vllm-server.internal:8000/v1`) and model identifier (e.g., `llama3.1:70b`, `deepseek-coder-v2`).

### 3.3 Prompt Pipeline Architecture
* **Profile Ingestion & Normalization:** Converts master CV inputs (PDF, DOCX, Markdown, JsonResume) into a canonical JSON schema.
* **Job Description Context Extractor:** Extracts key responsibilities, required technical skills, soft skills, and organizational domain keywords.
* **Master Prompt Execution Pipeline:**
  * Step 1: System prompt setup with ATS constraint rules and role translation directives.
  * Step 2: Generation of tailored CV content in structured JSON schema via function calling / instructor response models.
  * Step 3: Generation of single-page cover letter matching exact technical hooks.
* **Validation & Fallback:** JsonSchema validation on LLM output. If parsing fails, automated retry logic triggers with error correction prompts up to 3 times.

---

## 4. Backend Architecture & API Specification

### 4.1 Tech Stack
* **Runtime & Framework:** Python 3.11 / FastAPI or Node.js / TypeScript (NestJS).
* **Database:** PostgreSQL 16 with Prisma ORM.
* **Cache & Message Queue:** Redis 7 + Celery / BullMQ for asynchronous document compilation tasks.
* **Document Engine:** `python-docx` for `.docx` generation, `WeasyPrint` / `fpdf2` for pixel-perfect PDF rendering.
* **Object Storage:** AWS S3 / MinIO for secure document artifact caching.

### 4.2 Database Schema (Entity Relationship)

```sql
-- Users & Accounts
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user', -- 'user', 'org_admin', 'super_admin'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Organization & Team Seats
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID REFERENCES users(id),
    max_seats INT DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member', -- 'admin', 'member'
    UNIQUE(organization_id, user_id)
);

-- Subscription & Billing
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    plan_tier VARCHAR(50) NOT NULL, -- 'trial', 'pay_per_use', 'individual', 'team'
    status VARCHAR(50) NOT NULL, -- 'active', 'trialing', 'canceled', 'past_due'
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    credits_remaining INT DEFAULT 0
);

-- Master Profiles & Prompt Configurations
CREATE TABLE master_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT 'Default Master Profile',
    profile_data JSONB NOT NULL, -- Education, Work Experience, Skills, Publications
    master_prompt_text TEXT, -- Optional custom prompt overrides
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LLM Provider Configurations
CREATE TABLE llm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- 'system_default', 'openai', 'anthropic', 'ollama', 'custom'
    base_url VARCHAR(500),
    api_key_encrypted TEXT,
    model_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Generation Jobs & Artifacts
CREATE TABLE generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    job_description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    cv_file_url VARCHAR(500),
    cover_letter_file_url VARCHAR(500),
    tokens_used INT,
    execution_time_ms INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 Key REST & WebSocket API Endpoints

#### Public (No Authentication Required)
* `POST /api/v1/analyzer` - Job Post Analyzer: paste a JD, get skills breakdown, salary estimate, red flags, company research. No account required.

#### Authentication & Billing
* `POST /api/v1/auth/signup` - User Registration & Trial Initialization
* `POST /api/v1/auth/login` - JWT / OAuth Token Generation
* `POST /api/v1/auth/linkedin/connect` - Initiate LinkedIn OAuth flow for profile sync
* `POST /api/v1/auth/linkedin/callback` - LinkedIn OAuth callback; triggers profile pre-fill
* `POST /api/v1/billing/checkout-session` - Create Stripe Checkout Session (Sub or Credits)
* `POST /api/v1/billing/webhook` - Stripe Webhook Handler

#### LLM & Master Profile Management
* `GET/POST /api/v1/profiles` - Manage Master CV Profiles
* `GET/POST /api/v1/llm-config` - Set LLM Execution Target (BYOK or Local Server Endpoint)

#### Intelligence Layer
* `POST /api/v1/intelligence/gap-analysis` - Compare profile against target role/JD; returns missing skills, rare skills, over-reported skills, positioning advice
* `POST /api/v1/intelligence/salary-estimate` - Salary range and skill-premium data for a target role + location
* `POST /api/v1/intelligence/market-heatmap` - Posting volume trends and co-occurrence data for the user's skills
* `POST /api/v1/intelligence/positioning-advice` - Reframing suggestions for moving from current domain to target domain

#### Interview Preparation
* `POST /api/v1/interview/predict-questions` - Predict 15–20 likely interview questions from JD + company + role level
* `POST /api/v1/interview/evaluate-answer` - Evaluate a practice answer against the role's requirements; returns specific feedback
* `GET /api/v1/interview/star-stories` - Surface the most relevant STAR stories from the profile for predicted questions

#### Application Tracker & Outcome Feedback
* `POST /api/v1/applications` - Log an application (job title, company, JD link, profile framing used, cover letter used)
* `GET /api/v1/applications` - List user's applications with status
* `PUT /api/v1/applications/{id}/outcome` - Record outcome: "got_interview", "no_response", "rejected", "offered"
* `GET /api/v1/applications/{id}/regenerate` - Get the original generation parameters for re-generation

#### Generation Engine
* `POST /api/v1/generate` - Trigger CV + Cover Letter Generation Job
* `GET /api/v1/generate/jobs/:id` - Job Status & Artifact URLs
* `WS /api/v1/generate/stream/:id` - WebSocket for Live Token Streaming & Status Updates (**Note:** De-prioritized for MVP — generation takes 30–90 seconds; users will wait. Streaming is polish, not a differentiator.)

---

## 5. Frontend Architecture & User Experience (UX)

### 5.1 Tech Stack
* **Framework:** Next.js 14 (React 18, App Router, Server Components).
* **Styling & UI Components:** Tailwind CSS + Shadcn UI (Radix Primitives).
* **State Management & Data Fetching:** TanStack Query (React Query) + Zustand.
* **Document Preview Engine:** `@react-pdf/renderer` or PDF.js for instant browser preview.

### 5.2 Key User Interfaces & Screens

1. **Landing Page & Job Post Analyzer (Public):** The landing page leads with the Job Post Analyzer — a prominent textarea where any visitor can paste a job description and get an immediate free breakdown. No account required. This is the primary entry point and growth lever. The analysis result includes a CTA: "Want a CV tailored to this posting? Connect your profile."

2. **Dashboard & Trial Banner:** Displays active subscription status, trial countdown, remaining generation credits, and quick action buttons. Also surfaces: intelligence layer highlights (e.g., "3 skills growing in demand", "Salary potential: +$12K with Kubernetes"), recent applications, and next interview prep recommendations.

3. **Master Profile Builder:** Multi-step wizard (Methods A, B, C) to manage education, work experience, publications, and technical skill matrices. Allows importing existing CV files (Method B) or connecting LinkedIn (Method C) for one-click pre-fill. All three methods converge on the same wizard for review and save.

4. **Intelligence Dashboard:** The core differentiator screen. Shows:
   - **Gap Analysis:** "For Senior ML Engineer roles, you're missing these 4 skills that appear in 80%+ of postings." With learning path suggestions.
   - **Salary Intelligence:** "Your profile + Kubernetes commands $85K–$110K in Helsinki. Add MLOps and the range goes to $95K–$125K."
   - **Market Demand Heatmap:** Visual trend indicators for each skill (growing/stable/declining).
   - **Positioning Advice:** "Your profile reads as Chemical Engineering. Here's how to reframe for ML Engineering."

5. **Tailored Application Studio (Split View):**
   * *Left Pane:* Target Job Description input, Job Title, Company, profile selector, LLM provider selection toggle, and "Run Intelligence First" button (runs gap analysis before generation).
   * *Right Pane:* Tabbed preview — Intelligence Report tab, CV tab, Cover Letter tab. After generation: download buttons for DOCX, PDF, Markdown, plain text.

6. **Interview Prep Studio:** Predicted questions for the selected job, text-based practice mode with LLM-evaluated feedback, and STAR story bank surfaced from the profile.

7. **Application Tracker:** Timeline view of all applications with status indicators. One-click outcome reporting. "Re-generate from this application" action on each entry.

8. **Document Library:** Grid of saved CV and cover letter artifacts with search, filter, download (individual and ZIP), rename, and delete. Quota indicator in the header.

9. **Master Prompt & LLM Settings (Advanced):** Allows editing of prompt temperature, system prompts, BYOK API keys, or connecting to local Ollama endpoints (`http://localhost:11434`).

10. **Team Seat Management (For Team Tiers — Phase 4):** Organization admin panel to invite team members, assign admin/member roles, monitor usage quotas, and manage centralized company master templates.

---

## 6. Document Generation & ATS Compliance Engine

### 6.1 Formatting & ATS Rules
To guarantee 100% ATS parser compatibility:
* **Single-Column Flow:** Strict linear text hierarchy without floating boxes or multi-column structural frames.
* **Typography:** Built-in web-safe fonts (Calibri, Arial, Helvetica, Georgia).
* **Zero Tables for Layout:** Content alignment achieved via native tab-stops and paragraph margin indents.
* **Explicit Section Terminology:** Standard headers (`PROFESSIONAL SUMMARY`, `PROFESSIONAL EXPERIENCE`, `EDUCATION`, `CORE COMPETENCIES`).
* **Metadata Hygiene:** Stripped of unnecessary tracking attributes or unhandled XML tags.

---

## 7. Security, Privacy & GDPR Compliance

1. **Data Isolation:** User master profiles and generated documents are cryptographically isolated per tenant.
2. **Local Execution Mode (Privacy First):** For privacy-sensitive users, choosing local LLM routing (Ollama/vLLM) ensures zero third-party API data sharing.
3. **Data Retention Policy:** Output artifacts in temporary storage automatically purge after 30 days unless saved to user library.
4. **Encryption:** All API keys encrypted using AES-256-GCM prior to storage in PostgreSQL.

5. **AI-Generated Content Authenticity:** The system must produce CVs that read as authentic human work — specific, quantified, with the user's genuine voice. Generic AI prose ("highly motivated professional with a proven track record") is a red flag for employers and ATS systems. The master prompt's "do NOT fabricate" directive is enforced, not just encouraged. The profile data is the source of truth; the LLM is a framer, not a creator.

6. **Outcome Data Privacy:** Outcome feedback data (did you get an interview?) is personal and sensitive. It is never shared, aggregated, or used for B2B intelligence products without explicit opt-in. Outcome data is used only for the user's personal feedback loop and generation quality improvement.

---

## 8. Deployment & CI/CD Pipeline

### 8.1 Dockerized Architecture
* `frontend`: Next.js Node container
* `backend`: FastAPI Python container
* `worker`: Celery task execution container
* `db`: PostgreSQL 16
* `redis`: Redis 7 cache/broker

### 8.2 Deployment Options
* **Cloud Managed:** AWS ECS / DigitalOcean Kubernetes + Managed Postgres + Stripe.
* **Self-Hosted Enterprise:** Single `docker-compose.yml` or Helm chart for enterprise deployments with local LLM integration.

---

## 9. Next Steps & Roadmap

1. **Phase 1 (MVP - Weeks 1-4):** Master Profile Manager (Methods A, B, C), FastAPI backend, OpenAI/Anthropic Adapter, `python-docx` generation engine, Next.js UI, Stripe Trial & Subscription integration, Job Post Analyzer (free, no-account endpoint).
2. **Phase 2 (Intelligence Layer & Interview Prep - Weeks 5-8):** Gap analysis, salary intelligence, market demand heatmap, positioning advice. Data ingestion pipeline for job posting corpus. Interview question prediction, simulated interview mode, STAR story bank. Outcome feedback loop + application tracker.
3. **Phase 3 (LLM Agnosticism & Local Support - Weeks 9-10):** Ollama/vLLM Adapter integration, BYOK management screen. **Note:** WebSocket token streaming is de-prioritized — generation takes 30–90 seconds; users will wait. Streaming is polish, not a differentiator.
4. **Phase 4 (Team Seats & Advanced ATS Analytics - Weeks 11-12):** Multi-tenant organization accounts, team seat invitation flow, pooled quota tracking, team dashboard. Built-in ATS keyword match scoring surfaced in the UI. **Note:** Team/agency tier is a Phase 3+ feature; the MVP focuses on the individual product.
5. **Phase 5 (Output Formats, Side-Cars & Polish - Weeks 13-14):** Markdown, Notion, LaTeX, plain-text exports. AI-Era Resume Review (standalone paid). Career Pivot Compass. "What Should I Learn Next?" recommendations. Multi-CV strategy. GitHub/Portfolio importer. **Note:** Multi-language CV output is de-prioritized for MVP — add after core generation quality is proven. The market for non-English CVs is real but it's not the entry point.
6. **Phase 6 (Production Hardening - Weeks 15-16):** Rate limiting, input sanitization, encrypted API keys, CORS, CSP, auth token security. Sentry error tracking, OpenTelemetry tracing, structured logging, metrics. Health checks. Security audit. Admin dashboard.

---

## 10. LLM Quality Assurance & Evaluation Harness

The generation quality depends entirely on the model. A model update can silently degrade output. The system needs an evaluation harness that tests generation quality continuously.

### 10.1 Evaluation Harness

- Maintain a reference set of profile + job description pairs with expected output characteristics (not exact expected output — LLM output is non-deterministic — but expected quality thresholds).
- Run the evaluation set through every LLM provider/model combination on a schedule (e.g., weekly, and on every model update).
- Measure: ATS compliance (are standard headers present? single-column? no tables?), keyword coverage (does the output include the JD's required skills?), hallucination rate (does the output include skills/claims not in the profile?), cover letter quality (does it open with a motivation hook? is it under 400 words?).
- Alert when quality drops below threshold. The alert triggers a review before the model is used in production.
- This is not glamorous but it's essential for a generation product.

### 10.2 AI-Generated CV Stigma Mitigation

Some employers and ATS systems are beginning to flag or deprioritize obviously AI-generated content. The system must produce CVs that read as authentic human work — specific, quantified, with the user's genuine voice.

- The master prompt's emphasis on "do NOT fabricate" is the right instinct and must be enforced, not just encouraged.
- Generated content must be specific and quantified — generic AI prose ("highly motivated professional with a proven track record") is a red flag.
- The user's genuine voice should come through. The profile data is the source of truth; the LLM is a framer, not a creator.

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **LLM quality variance:** A model update silently degrades output quality. | Evaluation harness (Section 10.1) tests every provider/model on a schedule and alerts on degradation. |
| **Data freshness for intelligence layer:** Salary data, skill demand trends, and posting volume go stale. | Scheduled ingestion pipeline (Section 1.7.5) keeps data current. UI shows "data may be stale" notice when freshness threshold is exceeded. |
| **"AI-generated CV" stigma:** Employers/ATS flag obviously AI-generated content. | Enforce "do NOT fabricate" in the master prompt. Generate specific, quantified, authentic-sounding content (Section 10.2). |
| **Outcome data problem:** Users won't report outcomes; feedback loop starves. | Make outcome reporting one-click and low-friction. Do not require it for core generation. Intelligence layer starts with market data; personal outcome learning grows over time. |
| **Team tier overengineering:** Building team/agency features before proving the individual product. | Team tier is explicitly de-prioritized to Phase 4. MVP focuses on individual product. |
| **WebSocket streaming overengineering:** Building streaming UX before proving core generation value. | WebSocket streaming is de-prioritized. Generation is fast enough (30–90 seconds) that users will wait. |
