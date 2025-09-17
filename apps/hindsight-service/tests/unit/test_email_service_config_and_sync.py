import pytest
pytest.importorskip("aiosmtplib")
pytest.importorskip("jinja2")

import os
from unittest.mock import MagicMock, patch

from core.services.email_service import EmailServiceConfig, send_email_sync


def test_config_validates_mutually_exclusive_ssl_tls(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_USE_SSL", "true")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    cfg = EmailServiceConfig()
    errs = cfg.validate()
    assert any("both SSL and TLS" in e for e in errs)


def test_send_email_sync(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")

    class _SMTP(MagicMock):
        async def __aenter__(self2):
            return self2
        async def __aexit__(self2, exc_type, exc, tb):
            return False
        async def send_message(self2, message):
            return {"status": "ok"}

    with patch("aiosmtplib.SMTP", _SMTP):
        out = send_email_sync("u@example.com", "S", "<b>H</b>", text_content="H")
        assert out["success"] is True
