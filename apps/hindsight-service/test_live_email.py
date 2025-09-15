"""
Live Email Test Script

This script sends a real test email to verify the email system is working
with the configured Resend API key.

Run with: docker exec hindsight-service python test_live_email.py
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.notification_service import TEMPLATE_ORG_INVITATION

from core.services.transactional_email_service import TransactionalEmailService

async def send_test_email():
    """Send a test email to verify the configuration."""
    print("🚀 Testing Live Email Sending with Resend")
    print("=" * 50)
    
    # Check configuration
    email_provider = os.getenv('EMAIL_PROVIDER', 'resend')
    resend_api_key = os.getenv('RESEND_API_KEY')
    from_email = os.getenv('FROM_EMAIL', 'support@hindsight-ai.com')
    from_name = os.getenv('FROM_NAME', 'Hindsight AI')
    
    print(f"Email Provider: {email_provider}")
    print(f"From Email: {from_email}")
    print(f"From Name: {from_name}")
    print(f"API Key: {resend_api_key[:10] + '...' if resend_api_key else 'NOT SET'}")
    
    if not resend_api_key:
        print("❌ RESEND_API_KEY not configured!")
        return False
    
    # Initialize email service
    email_service = TransactionalEmailService()
    
    # Test email content
    test_to_email = "support@hindsight-ai.com"
    
    # Render email template
    try:
        template_context = {
            'organization_name': 'Hindsight AI Test Organization',
            'inviter_name': 'Email Test System',
            'accept_url': 'https://hindsight-ai.com/accept/test-invitation',
            'decline_url': 'https://hindsight-ai.com/decline/test-invitation',
            'current_year': datetime.now().year,
            'invitation_message': 'This is a test email to verify that the notification system is working correctly.'
        }
        
        html_content, text_content = email_service.render_template(
            TEMPLATE_ORG_INVITATION,
            template_context
        )
        
        print(f"\n✅ Template rendered successfully")
        print(f"   HTML length: {len(html_content)} characters")
        print(f"   Text length: {len(text_content)} characters")
        
    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        return False
    
    # Send the email
    try:
        print(f"\n📧 Sending test email to {test_to_email}...")
        
        result = await email_service.send_email(
            to_email=test_to_email,
            subject="🧪 Hindsight AI Email System Test",
            html_content=html_content,
            text_content=text_content
        )
        
        if result['success']:
            print("✅ Email sent successfully!")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            print(f"   Provider Response: {result.get('provider_response', 'N/A')}")
            print(f"\n📬 Check your inbox at {test_to_email}")
            print("   The email should arrive within a few seconds.")
            return True
        else:
            print("❌ Email sending failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            if 'provider_error' in result:
                print(f"   Provider Error: {result['provider_error']}")
            return False
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the live email test."""
    success = await send_test_email()
    
    if success:
        print("\n🎉 Email test completed successfully!")
        print("   Check your email inbox for the test message.")
        print("   If you don't see it, check your spam folder.")
    else:
        print("\n💥 Email test failed!")
        print("   Please check your configuration and try again.")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
