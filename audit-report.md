# Githeri Audit Report

**Generated:** 2026-10-11T23:14:14.242465Z
**Repository:** /Users/nickrotich/Desktop/portfolio/projects/python/careerforge

## Summary

- **Total Specs:** 1
- **Total Endpoints:** 60
- **Implemented in code:** 506
- **Matched:** 58
- **Missing:** 2
- **Undocumented:** 384
- **Coverage:** 96.7%

## Endpoints by Spec

### careerforge-api
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `GET /api/v1/auth/verify-email`
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me`
- `GET /api/v1/profiles`
- `POST /api/v1/profiles`
- `GET /api/v1/profiles/{profile_id}`
- `PUT /api/v1/profiles/{profile_id}`
- `DELETE /api/v1/profiles/{profile_id}`
- `PATCH /api/v1/profiles/{profile_id}/sections/{section_name}`
- `POST /api/v1/profiles/{profile_id}/set-default`
- `GET /api/v1/profiles/skills/suggestions`
- `POST /api/v1/profiles/import`
- `GET /api/v1/profiles/import/{parse_job_id}`
- `POST /api/v1/generate`
- `GET /api/v1/generate/jobs/{job_id}/cv`
- `GET /api/v1/generate/jobs/{job_id}/cover-letter`
- `GET /api/v1/generate/jobs/{job_id}`
- `POST /api/v1/generate/bulk`
- `POST /api/v1/generate/{job_id}/save`
- `GET /api/v1/generate/library`
- `GET /api/v1/generate/library/{artifact_id}/download`
- `GET /api/v1/llm-config`
- `POST /api/v1/llm-config`
- `GET /api/v1/llm-config/models`
- `GET /api/v1/llm-config/{config_id}`
- `PUT /api/v1/llm-config/{config_id}`
- `DELETE /api/v1/llm-config/{config_id}`
- `POST /api/v1/llm-config/{config_id}/test`
- `POST /api/v1/organizations`
- `GET /api/v1/organizations/{org_id}`
- `GET /api/v1/organizations/{org_id}/members`
- `DELETE /api/v1/organizations/{org_id}/members/{user_id}`
- `POST /api/v1/organizations/{org_id}/invite`
- `POST /api/v1/organizations/invitations/accept`
- `POST /api/v1/organizations/{org_id}/master-profiles`
- `GET /api/v1/organizations/{org_id}/master-profiles`
- `DELETE /api/v1/organizations/{org_id}/master-profiles/{profile_id}`
- `POST /api/v1/organizations/{org_id}/usage/log`
- `GET /api/v1/organizations/{org_id}/usage`
- `POST /api/v1/organizations/{org_id}/usage/reset`
- `PATCH /api/v1/organizations/{org_id}/billing`
- `POST /api/v1/analyzer`
- `POST /api/v1/analyzer/jev`
- `POST /api/v1/billing/checkout-session`
- `POST /api/v1/billing/webhook`
- `POST /api/v1/billing/cancel`
- `GET /api/v1/billing/subscription`
- `GET /api/v1/billing/credit-bundles`
- `GET /api/v1/billing/reconciliation`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/generation-log`
- `GET /api/v1/admin/metrics`
- `POST /api/v1/feedback`
- `GET /api/v1/feedback/my`

## Monorepo Packages

| Package | Path | Specs | Matched | Missing | Coverage |
| :--- | :--- | ---: | ---: | ---: | ---: |
| frontend | `frontend` | 0 | 0 | 0 | 0.0% |
| .next | `frontend/.next` | 0 | 0 | 0 | 0.0% |

## Coverage by Area

- v1: 96.7%

## Before/After Review Diff

Baseline: 1 spec(s) generated as drafts.
Current:  0 active, 1 still draft.

Still draft (not enforced):
  - careerforge-api.yaml