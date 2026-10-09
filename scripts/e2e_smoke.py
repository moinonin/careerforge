#!/usr/bin/env python3
"""T6 end-to-end smoke test: signup → verify → profile → generate → download → library.

Runs against a live API (default http://localhost:8000). Exercises the full
user journey and asserts each step succeeds. Designed for staging with real
or sandboxed Stripe/LLM keys.

Usage:
    python scripts/e2e_smoke.py [--base-url http://localhost:8000]

Exit code 0 on success, 1 with a readable failure report otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

DEFAULT_BASE_URL = "http://localhost:8000"


class SmokeFailure(Exception):
    pass


def _request(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
    timeout: int = 120,
) -> tuple[int, dict | bytes]:
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return resp.status, json.loads(raw)
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SmokeFailure(f"{method} {url} → HTTP {exc.code}: {detail[:300]}") from exc


def _check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}{(' — ' + detail) if detail else ''}")
    if not ok:
        raise SmokeFailure(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--provider", default=None,
                        help="LLM provider override (e.g. ollama) — overrides server default")
    parser.add_argument("--model", default=None,
                        help="LLM model override (e.g. qwen3.8-27B:latest)")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"E2E smoke against {base}\n")

    # 1. Health
    print("1. Health check")
    code, data = _request("GET", f"{base}/health")
    _check("GET /health", code == 200 and isinstance(data, dict) and data.get("status") == "ok")

    # 2. Signup
    print("2. Signup")
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    password = "smoketest-pass-123"
    code, data = _request(
        "POST",
        f"{base}/api/v1/auth/signup",
        {"email": email, "password": password, "full_name": "Smoke Test"},
    )
    assert isinstance(data, dict)
    _check("POST /auth/signup", code in (200, 201) and "access_token" in data, f"email={email}")
    token = data["access_token"]

    # 3. Create profile
    print("3. Create master profile")
    profile_payload = {
        "title": "Smoke CV",
        "profile_data": {
            "contact": {"full_name": "Smoke Test", "location": "Nairobi, Kenya",
                        "email": email},
            "summary": "Backend engineer with Python and PostgreSQL experience.",
            "skills": {"technical": ["Python", "FastAPI", "PostgreSQL"],
                       "domain": ["Backend Development"],
                       "tools": ["Docker"],
                       "soft": ["Communication"]},
            "experience": [{
                "role": "Backend Engineer",
                "company": "Acme Ltd",
                "location": "Nairobi",
                "start_date": "2021-01",
                "end_date": "Present",
                "bullets": ["Built REST APIs with FastAPI."],
            }],
            "education": [{
                "degree": "BSc Computer Science",
                "institution": "University of Nairobi",
                "start_date": "2016",
                "end_date": "2020",
            }],
            "publications": [], "certifications": [], "languages": [],
            "projects": [], "additional_info": "",
        },
    }
    code, data = _request("POST", f"{base}/api/v1/profiles", profile_payload, token=token)
    assert isinstance(data, dict)
    profile_id = data.get("id")
    _check("POST /profiles", code in (200, 201) and profile_id, f"profile_id={profile_id}")

    # 4. Generate (inline mode: completes synchronously; celery: queued + poll)
    print("4. Generate CV + cover letter")
    code, data = _request(
        "POST",
        f"{base}/api/v1/generate",
        {
            "profile_id": profile_id,
            "job_description": (
                "Senior Backend Engineer: Python, FastAPI, PostgreSQL, Docker. "
                "Build and maintain REST APIs for a fintech platform."
            ),
            "job_title": "Senior Backend Engineer",
            "company_name": "Acme Fintech",
            **({"provider": args.provider} if args.provider else {}),
            **({"model": args.model} if args.model else {}),
        },
        token=token,
        timeout=600,
    )
    assert isinstance(data, dict)
    job_id = data.get("job_id")
    _check("POST /generate accepted", code == 202 and job_id, f"status={data.get('status')}")

    # Poll until completed (inline mode returns immediately)
    for _ in range(120):
        code, job = _request("GET", f"{base}/api/v1/generate/jobs/{job_id}", token=token)
        assert isinstance(job, dict)
        if job.get("status") == "completed":
            break
        if job.get("status") == "failed":
            raise SmokeFailure(f"Generation failed: {job.get('error_message')}")
        time.sleep(2)
    else:
        raise SmokeFailure("Generation did not complete within timeout")
    _check("generation completed", True, f"at_score={job.get('at_score')}")

    # 5. Download artifacts
    print("5. Download artifacts")
    code, blob = _request("GET", f"{base}/api/v1/generate/jobs/{job_id}/cv", token=token)
    assert isinstance(blob, bytes)
    _check("download CV docx", code == 200 and len(blob) > 1000, f"{len(blob)} bytes")
    code, blob = _request("GET", f"{base}/api/v1/generate/jobs/{job_id}/cover-letter", token=token)
    assert isinstance(blob, bytes)
    _check("download cover letter docx", code == 200 and len(blob) > 1000, f"{len(blob)} bytes")

    # 6. Save to library + list
    print("6. Document library")
    code, saved = _request(
        "POST",
        f"{base}/api/v1/generate/{job_id}/save",
        {"title": "Smoke E2E CV"},
        token=token,
    )
    _check("POST /generate/{job_id}/save", code == 200 and isinstance(saved, dict))

    code, lib = _request("GET", f"{base}/api/v1/generate/library", token=token)
    assert isinstance(lib, dict)
    _check("GET /generate/library", code == 200 and lib.get("total", 0) >= 1,
           f"documents={lib.get('total')}")

    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SmokeFailure as exc:
        print(f"\nSMOKE FAILED: {exc}")
        sys.exit(1)
