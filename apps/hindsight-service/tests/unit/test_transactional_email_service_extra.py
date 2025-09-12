from core.services.transactional_email_service import TransactionalEmailService


def test_html_to_text_basic():
    svc = TransactionalEmailService()
    html = "<html><body>Hello &amp; welcome &lt;User&gt;! &#39;Quote&#39;</body></html>"
    text = svc._html_to_text(html)
    assert "Hello & welcome <User>! 'Quote'" in text

