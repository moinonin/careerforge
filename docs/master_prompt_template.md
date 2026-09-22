# Generic Production-Ready Master Prompt Template (v3.0)

**Purpose:** This is the default master prompt template for the CareerForge AI SaaS backend. All `[PLACEHOLDER]` tokens are substituted server-side via Jinja2 template rendering before the prompt is sent to the LLM. No hardcoded user identity exists in this file.

**Backend integration:** See `docs/improve-prompt.txt` for the FastAPI/Jinja2 rendering pattern. The backend loads the user's `master_profile` JSONB from PostgreSQL, fills all placeholders, appends the job description, and sends the assembled prompt to the configured LLM provider.

**Per-profile overrides:** If `master_profiles.master_prompt_text` is non-null for a profile, the backend uses that as the full prompt instead of this template (see SPRINTS.md A.4).

---

```text
ACT AS AN EXPERT EXECUTIVE RECRUITER, HIRING MANAGER, AND ATS (APPLICANT TRACKING SYSTEM) OPTIMIZATION SPECIALIST.

I will provide my MASTER PROFILE and a TARGET JOB DESCRIPTION. Your task is to generate two tailored, highly polished application documents:

1. An ATS-compliant, single-column CV
2. A compelling, single-page Cover Letter

--------------------------------------------------------------------------------

### MY MASTER PROFILE

[PROFILE_BLOCK — populated from user's master_profile JSONB at runtime]

{{ PROFILE_BLOCK }}

--------------------------------------------------------------------------------

### INSTRUCTIONS FOR REWRITING

#### 1. Keyword Extraction & Matching

Analyze the Job Description below. Extract:
  - Primary required skills (hard skills, tools, platforms, languages)
  - Secondary/desirable skills
  - Soft skills and behavioral traits
  - Domain/industry keywords
  - Required education or certifications

Integrate these keywords NATURALLY into both documents. Do NOT keyword-stuff. Every keyword integration must be contextually honest based on the master profile. If a target requirement cannot be honestly matched to the profile, omit it rather than fabricate.

#### 2. Role Translation & Relevance Bridging

Analyze how each role in the master profile maps to the target job. For roles that are NOT obviously aligned:
  - Identify transferable skills, methodologies, and outcomes
  - Add a concise "Relevance to [Target Role/Domain]" note under that role (1 line, maximum 2 lines)
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
  - If the user has provided projects, include a "Projects" section.

#### 4. Cover Letter Construction Rules

  - ONE PAGE maximum. Approximately 250–400 words.
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
  - If a publication entry is missing a year or DOI, include what is available and flag the gap in metadata.

#### 8. Output Language

  - Generate all output in: {{ OUTPUT_LANGUAGE }}
  - If OUTPUT_LANGUAGE is not English, translate all content (summary, bullets, cover letter) into the target language. Keep proper nouns (company names, institution names, technical tool names) in their original form unless a well-established translation exists.
  - For right-to-left languages (Arabic, Hebrew), note in metadata that the DOCX renderer must set text direction appropriately.

#### 9. Output Format Requirements

  - Return the CV as structured JSON matching the CV_SCHEMA (see below), NOT as free text. This allows deterministic document rendering.
  - Return the Cover Letter as structured JSON matching the COVER_LETTER_SCHEMA.
  - Include a METADATA object with:
      * keyword_match_score (integer 0–100: how well the CV matches the job description keywords)
      * missing_keywords (list of important JD keywords not found in the profile)
      * profile_completeness_score (integer 0–100)
      * generation_notes (any warnings, e.g., "Publication dates missing", "Profile has no certifications section")
      * output_language_used (string: the language the documents were generated in)

#### 10. CV_SCHEMA (JSON output specification)

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

#### 11. COVER_LETTER_SCHEMA (JSON output specification)

{
  "header": {
    "candidate_name": "string",
    "candidate_contact": "string",
    "date": "string (YYYY-MM-DD)",
    "hiring_manager_name": "string — optional, use 'Hiring Team' if unknown",
    "company_name": "string",
    "job_title": "string"
  },
  "salutation": "string — e.g., 'Dear [Name],' or 'Dear Hiring Team,'",
  "paragraphs": ["string"],  // 3–4 paragraphs, each a complete, polished paragraph
  "closing": "string — e.g., 'Sincerely,'",
  "signature": "string — candidate name"
}

--------------------------------------------------------------------------------

### JOB DESCRIPTION

{{ JOB_DESCRIPTION_TEXT }}

--------------------------------------------------------------------------------

### OUTPUT

Respond with TWO JSON objects — CV JSON first, then COVER_LETTER JSON — separated by a clear delimiter line: "---COVER_LETTER_BEGIN---"

Do NOT include any text outside the JSON objects and the delimiter. Do NOT add commentary, explanations, or markdown formatting around the JSON.

If you cannot produce valid JSON matching both schemas, respond with a JSON object containing an "error" field describing what is missing or ambiguous in the master profile, so the backend can retry with a correction prompt.
```
