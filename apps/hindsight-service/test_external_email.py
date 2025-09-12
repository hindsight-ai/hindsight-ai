#!/usr/bin/env python3
"""
Email Test with Different Recipient

Test sending to a different email address to verify the issue is with the recipient,
not the sending configuration.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.services.transactional_email_service import TransactionalEmailService

async def test_different_recipient():
    """Send test email to a different recipient."""
    print("🚀 Testing Email with Different Recipient")
    print("=" * 50)
    
    email_service = TransactionalEmailService()
    
    # Use a different email address that doesn't go through Cloudflare
    test_email = input("Enter a test email address (Gmail, Yahoo, etc.): ").strip()
    
    if not test_email or '@' not in test_email:
        print("❌ Invalid email address")
        return False
    
    template_context = {
        'organization_name': 'Hindsight AI Test',
        'inviter_name': 'Email System Test',
        'accept_url': 'https://hindsight-ai.com/accept/test',
        'decline_url': 'https://hindsight-ai.com/decline/test',
        'current_year': datetime.now().year,
        'invitation_message': 'This is a test to verify email delivery to external addresses.'
    }
    
    html_content, text_content = email_service.render_template(
        'organization_invitation',
        template_context
    )
    
    print(f"📧 Sending test email to {test_email}...")
    
    result = await email_service.send_email(
        to_email=test_email,
        subject="🧪 Hindsight AI Email Delivery Test",
        html_content=html_content,
        text_content=text_content
    )
    
    if result['success']:
        print("✅ Email sent successfully!")
        print(f"   Message ID: {result.get('message_id')}")
        print(f"\n📬 Check the inbox at {test_email}")
        return True
    else:
        print("❌ Email failed!")
        print(f"   Error: {result.get('error')}")
        return False

if __name__ == "__main__":
    asyncio.run(test_different_recipient())
