import os
import sys
from types import SimpleNamespace, ModuleType
import pytest
pytest.importorskip("jinja2")

from core.services.transactional_email_service import TransactionalEmailService, TransactionalEmailConfig


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for k in [
        "EMAIL_PROVIDER",
        "FROM_EMAIL",
        "FROM_NAME",
        "RESEND_API_KEY",
        "SENDGRID_API_KEY",
        "MAILGUN_API_KEY",
        "MAILGUN_DOMAIN",
    ]:
        monkeypatch.delenv(k, raising=False)


@pytest.mark.asyncio
async def test_resend_provider_success(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "rk")

    resend_mod = ModuleType("resend")
    class _Emails:
        @staticmethod
        def send(data):
            return {"id": "msg-1", "status": "ok"}
    resend_mod.api_key = None
    resend_mod.Emails = _Emails
    sys.modules["resend"] = resend_mod

    svc = TransactionalEmailService()
    out = await svc.send_email("u@example.com","Subject","<b>Hi</b>","Hi")
    assert out["success"] is True and out["provider"] == "resend"


@pytest.mark.asyncio
async def test_resend_provider_success_async(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "rk")

    # Mock resend
    resend_mod = ModuleType("resend")
    class _Emails:
        @staticmethod
        def send(data):
            return {"id": "msg-2"}
    resend_mod.api_key = None
    resend_mod.Emails = _Emails
    sys.modules["resend"] = resend_mod

    svc = TransactionalEmailService()
    out = await svc.send_email("user@example.com", "Hi", "<b>hi</b>")
    assert out["success"] is True
    assert out["provider"] == "resend"


@pytest.mark.asyncio
async def test_sendgrid_provider_success(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "sendgrid")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SENDGRID_API_KEY", "sk")

    # Build fake sendgrid module and helpers
    sg_mod = ModuleType("sendgrid")
    class _Client:
        def __init__(self, api_key=None):
            pass
        def send(self, mail):
            class Resp:
                status_code = 202
                headers = {"X-Message-Id": "sg-123"}
            return Resp()
    sg_mod.SendGridAPIClient = _Client
    sys.modules["sendgrid"] = sg_mod

    helpers = ModuleType("sendgrid.helpers")
    helpers_mail = ModuleType("sendgrid.helpers.mail")
    # Minimal placeholders
    class _From: 
        def __init__(self, email, name=None):
            self.email = email
    class _To: 
        def __init__(self, email):
            self.email = email
    class _Subject(str): pass
    class _HtmlContent(str): pass
    class _PlainTextContent(str): pass
    class _Mail:
        def __init__(self, from_email=None, to_emails=None, subject=None, html_content=None):
            self.from_email = from_email
            self.to_emails = to_emails
            self.subject = subject
            self.html_content = html_content
            self.plain_text_content = None
    helpers_mail.From = _From
    helpers_mail.To = _To
    helpers_mail.Subject = _Subject
    helpers_mail.HtmlContent = _HtmlContent
    helpers_mail.PlainTextContent = _PlainTextContent
    helpers_mail.Mail = _Mail
    sys.modules["sendgrid.helpers"] = helpers
    sys.modules["sendgrid.helpers.mail"] = helpers_mail

    svc = TransactionalEmailService()
    res = await svc.send_email("user@example.com", "Hi", "<b>test</b>")
    assert res["success"] is True and res["provider"] == "sendgrid"
    assert res.get("message_id") == "sg-123"


@pytest.mark.asyncio
async def test_mailgun_provider_success_and_failure(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "mailgun")
    monkeypatch.setenv("FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("MAILGUN_API_KEY", "mk")
    monkeypatch.setenv("MAILGUN_DOMAIN", "mg.example.com")

    class _RespOK:
        status_code = 200
        def json(self):
            return {"id": "mg-1"}
    class _RespBad:
        status_code = 400
        text = "bad"
    class _Req:
        def __init__(self):
            self.calls = []
        def post(self, url, auth=None, data=None):
            self.calls.append((url, data))
            return _RespOK()
    req = _Req()
    sys.modules["requests"] = req  # simple module-like object

    svc = TransactionalEmailService()
    ok = await svc.send_email("user@example.com", "S", "<b>H</b>")
    assert ok["success"] and ok["provider"] == "mailgun"

    # Now simulate failure
    class _Req2:
        def post(self, url, auth=None, data=None):
            return _RespBad()
    sys.modules["requests"] = _Req2()
    svc2 = TransactionalEmailService()
    bad = await svc2.send_email("user@example.com", "S", "<b>H</b>")
    assert bad["success"] is False and bad["provider"] == "mailgun"
