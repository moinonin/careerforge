"""Transactional email — provider-pluggable sender (T4 tightening).

Provider resolution order: settings.email_provider + settings.email_api_key.
Without an API key, emails are logged (not sent) so dev/tests never require a
provider account.

Supported providers: resend, sendgrid, postmark, ses.
"""

from __future__ import annotations

import structlog

from backend.config import settings

log = structlog.get_logger()


async def _send_resend(to: str, subject: str, html: str, api_key: str) -> None:
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        resp.raise_for_status()


async def _send_sendgrid(to: str, subject: str, html: str, api_key: str) -> None:
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {
                    "email": settings.email_from_address,
                    "name": settings.email_from_name,
                },
                "subject": subject,
                "content": [{"type": "text/html", "value": html}],
            },
        )
        resp.raise_for_status()


async def _send_postmark(to: str, subject: str, html: str, api_key: str) -> None:
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.postmarkapp.com/email",
            headers={
                "X-Postmark-Server-Token": api_key,
                "Content-Type": "application/json",
            },
            json={
                "From": f"{settings.email_from_name} <{settings.email_from_address}>",
                "To": to,
                "Subject": subject,
                "HtmlBody": html,
            },
        )
        resp.raise_for_status()


async def _send_ses(to: str, subject: str, html: str, api_key: str) -> None:
    """api_key format: ``<aws_access_key_id>:<aws_secret_access_key>``."""
    import asyncio

    import boto3

    key_id, _, secret = api_key.partition(":")
    if not secret:
        raise ValueError("SES api_key must be '<access_key_id>:<secret_access_key>'")

    def _send() -> None:
        client = boto3.client(
            "ses",
            region_name=settings.s3_region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        client.send_email(
            Source=f"{settings.email_from_name} <{settings.email_from_address}>",
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html}},
            },
        )

    await asyncio.to_thread(_send)


_SENDERS = {
    "resend": _send_resend,
    "sendgrid": _send_sendgrid,
    "postmark": _send_postmark,
    "ses": _send_ses,
}


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email. Returns True if actually delivered.

    Without a configured provider key, logs the email and returns False —
    never raises, so a broken mail provider cannot break auth flows.
    """
    if not settings.email_api_key:
        log.info(
            "email_not_configured",
            to=to,
            subject=subject,
            provider=settings.email_provider,
        )
        return False

    sender = _SENDERS.get(settings.email_provider)
    if sender is None:
        log.error("email_unknown_provider", provider=settings.email_provider)
        return False

    try:
        await sender(to, subject, html, settings.email_api_key)
    except Exception as exc:  # noqa: BLE001 — mail must not break the request
        log.error("email_send_failed", to=to, error=str(exc))
        return False

    log.info("email_sent", to=to, subject=subject, provider=settings.email_provider)
    return True


async def send_verification_email(to: str, token: str, base_url: str = "") -> bool:
    link = f"{base_url}/verify-email?token={token}" if base_url else token
    return await send_email(
        to,
        "Verify your CareerForge email",
        f"<p>Welcome! Verify your email by clicking "
        f'<a href="{link}">this link</a>.</p>'
        f"<p>The link expires in 24 hours.</p>",
    )


async def send_password_reset_email(to: str, token: str, base_url: str = "") -> bool:
    link = f"{base_url}/reset-password?token={token}" if base_url else token
    return await send_email(
        to,
        "Reset your CareerForge password",
        f"<p>Reset your password by clicking "
        f'<a href="{link}">this link</a>.</p>'
        f"<p>The link expires in 1 hour. If you didn't request this, ignore this email.</p>",
    )


async def send_trial_expiry_warning(to: str, generations_left: int) -> bool:
    return await send_email(
        to,
        "Your CareerForge trial is almost done",
        f"<p>You have {generations_left} free generation(s) left. "
        f"Upgrade to keep generating ATS-compliant CVs and cover letters.</p>",
    )
