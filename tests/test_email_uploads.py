"""T4 tests: transactional email + CV upload validation."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch


def _make_docx(with_macro: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<x/>")
        zf.writestr("word/document.xml", "<doc/>")
        if with_macro:
            zf.writestr("word/vbaProject.bin", b"macro")
    return buf.getvalue()


def _make_pdf() -> bytes:
    return b"%PDF-1.4 fake pdf body"


class TestUploadValidation:
    def test_accepts_valid_docx(self):
        from backend.validators.upload_validation import validate_cv_upload

        validate_cv_upload(_make_docx(), "cv.docx", None)

    def test_accepts_valid_pdf(self):
        from backend.validators.upload_validation import validate_cv_upload

        validate_cv_upload(_make_pdf(), "cv.pdf", "application/pdf")

    def test_rejects_unsupported_extension(self):
        import pytest

        from backend.validators.upload_validation import validate_cv_upload

        with pytest.raises(ValueError, match="Unsupported file type"):
            validate_cv_upload(b"data", "cv.txt", None)

    def test_rejects_oversized(self):
        import pytest

        from backend.validators.upload_validation import MAX_UPLOAD_BYTES, validate_cv_upload

        big = b"%PDF-" + b"x" * (MAX_UPLOAD_BYTES + 1)
        with pytest.raises(ValueError, match="10 MB"):
            validate_cv_upload(big, "cv.pdf", None)

    def test_rejects_empty(self):
        import pytest

        from backend.validators.upload_validation import validate_cv_upload

        with pytest.raises(ValueError, match="empty"):
            validate_cv_upload(b"", "cv.pdf", None)

    def test_rejects_spoofed_pdf(self):
        import pytest

        from backend.validators.upload_validation import validate_cv_upload

        with pytest.raises(ValueError, match="not a valid PDF"):
            validate_cv_upload(b"notapdf at all", "cv.pdf", None)

    def test_rejects_docx_with_macro(self):
        import pytest

        from backend.validators.upload_validation import validate_cv_upload

        with pytest.raises(ValueError, match="macros"):
            validate_cv_upload(_make_docx(with_macro=True), "cv.docx", None)

    def test_rejects_bad_docx_archive(self):
        import pytest

        from backend.validators.upload_validation import validate_cv_upload

        with pytest.raises(ValueError, match="not a valid DOCX"):
            validate_cv_upload(b"nonsense", "cv.docx", None)


class TestTransactionalEmail:
    def test_logs_instead_of_sending_without_api_key(self):
        import asyncio

        from backend import config
        from backend.email import send_email

        with patch.object(config.settings, "email_api_key", None):
            assert asyncio.run(send_email("a@b.c", "subj", "<p>hi</p>")) is False

    def test_resend_payload(self):
        import asyncio

        from backend import config
        from backend.email import send_email

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with (
            patch.object(config.settings, "email_api_key", "rk_test"),
            patch.object(config.settings, "email_provider", "resend"),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            assert asyncio.run(send_email("a@b.c", "Hello", "<p>body</p>")) is True

        call = client.post.call_args
        assert call.args[0] == "https://api.resend.com/emails"
        payload = call.kwargs["json"]
        assert payload["to"] == ["a@b.c"]
        assert payload["subject"] == "Hello"

    def test_unknown_provider_returns_false(self):
        import asyncio

        from backend import config
        from backend.email import send_email

        with (
            patch.object(config.settings, "email_api_key", "k"),
            patch.object(config.settings, "email_provider", "nonexistent"),
        ):
            assert asyncio.run(send_email("a@b.c", "s", "h")) is False

    def test_send_failure_never_raises(self):
        import asyncio

        import httpx

        from backend import config
        from backend.email import send_email

        with (
            patch.object(config.settings, "email_api_key", "rk_test"),
            patch.object(config.settings, "email_provider", "resend"),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            client = AsyncMock()
            client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            assert asyncio.run(send_email("a@b.c", "s", "h")) is False


class TestVerifyEmailEndpoint:
    def test_signup_sends_verification_and_verify_works(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from backend.main import app

        app.dependency_overrides.clear()

        class _FakeUser:
            id = "new-user"
            email = "new@example.com"

        with (
            patch("backend.auth.router.auth_signup", new_callable=AsyncMock) as mock_signup,
            patch("backend.email.send_verification_email", new_callable=AsyncMock) as mock_email,
        ):
            mock_signup.return_value = _FakeUser()
            mock_email.return_value = True

            from backend.auth.jwt_utils import create_verify_token
            from backend.database import get_session

            async def _mock_session():
                yield MagicMock()

            # use a real-ish session for verify endpoint
            async def _verify_session():
                session = AsyncMock()
                result = MagicMock()
                user = MagicMock()
                user.email_verified = False
                result.scalar_one_or_none.return_value = user
                session.execute = AsyncMock(return_value=result)
                session.commit = AsyncMock()
                yield session

            app.dependency_overrides[get_session] = _mock_session
            client = TestClient(app)
            resp = client.post(
                "/api/v1/auth/signup",
                json={"email": "new@example.com", "password": "supersecret1"},
            )
            assert resp.status_code in (200, 201, 204), resp.text
            mock_email.assert_awaited_once()

            # Verify endpoint with a token for the mocked user
            token = create_verify_token("new-user")
            app.dependency_overrides[get_session] = _verify_session
            vresp = client.get(f"/api/v1/auth/verify-email?token={token}")
            assert vresp.status_code == 200, vresp.text
            assert vresp.json()["status"] == "verified"

            # Bad token → 400 version
            bad = client.get("/api/v1/auth/verify-email?token=garbage")
            assert bad.status_code == 400
        app.dependency_overrides.clear()
