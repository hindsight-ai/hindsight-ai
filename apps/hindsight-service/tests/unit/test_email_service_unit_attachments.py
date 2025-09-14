import os
from unittest.mock import MagicMock, patch

import pytest

from core.services.email_service import EmailService


@pytest.mark.asyncio
async def test_send_email_with_attachments_and_reply_to(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")

    svc = EmailService()

    class _SMTP(MagicMock):
        async def __aenter__(self2):
            return self2
        async def __aexit__(self2, exc_type, exc, tb):
            return False
        async def send_message(self2, message):
            # Ensure our attachment is present
            assert any(p.get_content_type() == 'application/octet-stream' for p in message.get_payload())
            return {"status": "250 OK"}

    with patch("aiosmtplib.SMTP", _SMTP):
        out = await svc.send_email(
            to_email="user@example.com",
            subject="Hi",
            html_content="<b>hi</b>",
            text_content="hi",
            reply_to="reply@example.com",
            attachments=[{"filename": "a.txt", "content": b"data"}],
        )
        assert out["success"] is True

