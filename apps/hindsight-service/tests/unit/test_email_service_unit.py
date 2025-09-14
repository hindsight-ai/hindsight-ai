import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
import os

import pytest

from core.services.email_service import EmailService, EmailServiceConfig


@contextmanager
def _env(**env):
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_config_validate_and_is_configured():
    with _env(SMTP_HOST="smtp.example.com", SMTP_PORT="587", FROM_EMAIL="noreply@example.com"):
        cfg = EmailServiceConfig()
        assert cfg.is_configured() is True
        assert cfg.validate() == []

    with _env(SMTP_HOST="", SMTP_PORT="-1", FROM_EMAIL=""):
        cfg = EmailServiceConfig()
        errs = cfg.validate()
        assert any("SMTP_HOST" in e for e in errs)
        assert any("SMTP_PORT" in e for e in errs)
        assert any("FROM_EMAIL" in e for e in errs)


@pytest.mark.asyncio
async def test_send_email_not_configured():
    with _env(SMTP_HOST="", FROM_EMAIL=""):
        svc = EmailService()
        out = await svc.send_email("user@example.com", "Subject", "<b>Hi</b>")
        assert out["success"] is False
        assert "not configured" in (out.get("error") or "")


@pytest.mark.asyncio
async def test_send_email_success_with_mocked_smtp(tmp_path):
    # Minimal valid env
    with _env(SMTP_HOST="smtp.example.com", SMTP_PORT="587", FROM_EMAIL="noreply@example.com"):
        svc = EmailService()
        # Provide simple template folder to avoid warnings
        svc.template_env = None  # not needed for send

        class _SMTPMock(MagicMock):
            async def __aenter__(self2):
                return self2
            async def __aexit__(self2, exc_type, exc, tb):
                return False
            async def send_message(self2, message):
                return {"status": "250 OK"}

        with patch("aiosmtplib.SMTP", _SMTPMock):
            out = await svc.send_email("user@example.com", "Subject", "<b>Hi</b>", text_content="Hi")
            assert out["success"] is True
            assert "smtp_result" in out


def test_html_to_text_conversion():
    svc = EmailService()
    html = "<html><body>Hello &amp; world &lt;3&gt; &#39;quote&#39;</body></html>"
    text = svc._html_to_text(html)
    assert "Hello & world <3> 'quote'" in text


@pytest.mark.asyncio
async def test_test_connection_success_and_failure():
    with _env(SMTP_HOST="smtp.example.com", SMTP_PORT="587", FROM_EMAIL="noreply@example.com"):
        svc = EmailService()

        class _SMTPCtx(MagicMock):
            async def __aenter__(self2):
                return self2
            async def __aexit__(self2, exc_type, exc, tb):
                return False

        with patch("aiosmtplib.SMTP", _SMTPCtx) as mock_smtp:
            ok = await svc.test_connection()
            assert ok["success"] is True

    with _env(SMTP_HOST="smtp.example.com", SMTP_PORT="587", FROM_EMAIL="noreply@example.com"):
        svc = EmailService()
        with patch("aiosmtplib.SMTP", side_effect=Exception("boom")):
            res = await svc.test_connection()
            assert res["success"] is False
            assert "failed" in res.get("error", "").lower()
