"""Import a CV file (PDF/DOCX) directly into a user's profile, bypassing the web form.

Flow:
1. Parse CV file with pymupdf + Jev → MasterProfileData
2. Create a profile in the backend via the API

Usage:
    .venv/bin/python import_cv.py <path-to-cv.pdf> --email user@example.com --password pass123
    .venv/bin/python import_cv.py <path-to-cv.pdf> --token <jwt_token>

Prerequisites:
    - Backend must be running on localhost:8000
    - Hermes proxy must be running: hermes proxy start --provider nous
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from backend.profiles.jev_parser import parse_cv_with_jev

NOUS_BASE_URL = "http://localhost:8645/v1"
NOUS_MODEL = "inclusionai/ling-3.0-flash-fin:free"
BACKEND_URL = "http://localhost:8000"


async def signup(email: str, password: str) -> str:
    """Create a new user and return their JWT token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/auth/signup",
            json={"email": email, "password": password, "full_name": "CV Import User"},
        )
        if resp.status_code == 201:
            return resp.json()["access_token"]
        elif resp.status_code == 409:
            print(f"User {email} already exists — use --token instead")
            sys.exit(1)
        else:
            print(f"Signup failed: {resp.status_code} {resp.text[:200]}")
            sys.exit(1)


async def import_cv(cv_path: str, token: str) -> dict:
    """Parse a CV file and create a profile."""
    # Step 1: Parse the CV
    with open(cv_path, "rb") as f:
        cv_bytes = f.read()
    
    print(f"Parsing {cv_path} with pymupdf + Jev...")
    profile = await parse_cv_with_jev(cv_bytes, Path(cv_path).name)
    profile_dict = profile.model_dump()
    
    # Clean up the contact name (pymupdf sometimes picks up header text)
    if profile_dict["contact"]["full_name"] and "|" in profile_dict["contact"]["full_name"]:
        profile_dict["contact"]["full_name"] = profile_dict["contact"]["full_name"].split("|")[0].strip()
    
    print(f"  Name: {profile_dict['contact']['full_name']}")
    print(f"  Experience: {len(profile_dict['experience'])} entries")
    print(f"  Skills: {len(profile_dict['skills'])} categories")
    
    # Step 2: Create profile via API
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": f"CV Import - {profile_dict['contact']['full_name']}", "profile_data": profile_dict},
        )
        
        if resp.status_code == 201:
            result = resp.json()
            print(f"\nProfile created successfully!")
            print(f"  ID: {result['id']}")
            print(f"  Title: {result['title']}")
            contact = result.get("profile_data", {}).get("contact", {})
            print(f"  Name: {contact.get('full_name', 'N/A')}")
            print(f"  Email: {contact.get('email', 'N/A')}")
            print(f"  Experience entries: {len(result.get('profile_data', {}).get('experience', []))}")
            return result
        else:
            print(f"Failed to create profile: {resp.status_code} {resp.text[:200]}")
            sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(description="Import a CV file into your profile")
    parser.add_argument("cv_path", help="Path to the CV PDF or DOCX file")
    parser.add_argument("--email", help="Sign up with this email (if new user)")
    parser.add_argument("--password", default="TempPass123!", help="Password for signup")
    parser.add_argument("--token", help="Existing JWT token (skip signup)")
    args = parser.parse_args()
    
    if not args.token and not args.email:
        parser.error("Either --token or --email is required")
    
    token = args.token or await signup(args.email, args.password)
    await import_cv(args.cv_path, token)


if __name__ == "__main__":
    asyncio.run(main())
