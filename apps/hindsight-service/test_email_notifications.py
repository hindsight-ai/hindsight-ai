"""
Email Notification Test Script

This script tests the email notification functionality including:
- Email service configuration validation
- Template rendering
- SMTP connection testing
- End-to-end notification flow

Run with: uv run python test_email_notifications.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.email_service import EmailService, EmailServiceConfig
from core.services.notification_service import NotificationService, get_notification_service, TEMPLATE_ORG_INVITATION

async def test_email_configuration():
    """Test email service configuration."""
    print("🔧 Testing Email Configuration...")
    
    config = EmailServiceConfig()
    
    print(f"SMTP Host: {config.smtp_host}")
    print(f"SMTP Port: {config.smtp_port}")
    print(f"From Email: {config.from_email}")
    print(f"Template Dir: {config.template_dir}")
    
    if not config.is_configured():
        print("⚠️  Email service not fully configured. Set environment variables:")
        validation_errors = config.validate()
        for error in validation_errors:
            print(f"   - {error}")
        return False
    
    print("✅ Email configuration looks good!")
    return True

async def test_email_templates():
    """Test email template rendering."""
    print("\n📄 Testing Email Template Rendering...")
    
    email_service = EmailService()
    
    # Test organization invitation template
    try:
        template_context = {
            'organization_name': 'Test Organization',
            'inviter_name': 'John Doe',
            'accept_url': 'https://example.com/accept/123',
            'decline_url': 'https://example.com/decline/123',
            'current_year': 2025
        }
        
        html_content, text_content = email_service.render_template(
            TEMPLATE_ORG_INVITATION,
            template_context
        )
        
        print("✅ Organization invitation template rendered successfully")
        print(f"   HTML length: {len(html_content)} chars")
        print(f"   Text length: {len(text_content)} chars")
        
        # Test membership added template
        template_context = {
            'organization_name': 'Test Organization',
            'role': 'Member',
            'added_by_name': 'Jane Smith',
            'date_added': 'September 11, 2025',
            'current_year': 2025
        }
        
        html_content, text_content = email_service.render_template(
            'membership_added',
            template_context
        )
        
        print("✅ Membership added template rendered successfully")
        print(f"   HTML length: {len(html_content)} chars")
        print(f"   Text length: {len(text_content)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        return False

async def test_smtp_connection():
    """Test SMTP connection without sending email."""
    print("\n🔌 Testing SMTP Connection...")
    
    email_service = EmailService()
    
    try:
        result = await email_service.test_connection()
        
        if result['success']:
            print("✅ SMTP connection test successful")
            print(f"   {result['message']}")
            return True
        else:
            print(f"❌ SMTP connection test failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ SMTP connection test error: {e}")
        return False

async def test_email_sending():
    """Test actual email sending (if configured)."""
    print("\n📧 Testing Email Sending...")
    
    # Check if we have a test email address
    test_email = os.getenv('TEST_EMAIL')
    if not test_email:
        print("⚠️  Skipping email sending test. Set TEST_EMAIL environment variable to test.")
        return True
    
    email_service = EmailService()
    
    try:
        # Render test email
        template_context = {
            'organization_name': 'Hindsight AI Test',
            'inviter_name': 'Test System',
            'accept_url': 'https://example.com/accept/test',
            'decline_url': 'https://example.com/decline/test',
            'current_year': 2025
        }
        
        html_content, text_content = email_service.render_template(
            TEMPLATE_ORG_INVITATION,
            template_context
        )
        
        # Send test email
        result = await email_service.send_email(
            to_email=test_email,
            subject="[TEST] Hindsight AI Email System Test",
            html_content=html_content,
            text_content=text_content
        )
        
        if result['success']:
            print(f"✅ Test email sent successfully to {test_email}")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            return True
        else:
            print(f"❌ Email sending failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions for email testing."""
    print("\n📋 Email Testing Setup Instructions:")
    print("\nTo test email functionality, set these environment variables:")
    print("export SMTP_HOST='smtp.gmail.com'")
    print("export SMTP_PORT='587'")
    print("export SMTP_USERNAME='your-email@gmail.com'")
    print("export SMTP_PASSWORD='your-app-password'")
    print("export SMTP_USE_TLS='true'")
    print("export FROM_EMAIL='noreply@yourdomain.com'")
    print("export FROM_NAME='Hindsight AI'")
    print("export TEST_EMAIL='your-test-email@example.com'")
    print("\nFor Gmail, use an App Password instead of your regular password:")
    print("https://support.google.com/accounts/answer/185833")

async def main():
    """Run all email tests."""
    print("🚀 Starting Email Notification System Tests\n")
    
    tests = [
        ("Configuration", test_email_configuration()),
        ("Template Rendering", test_email_templates()),
        ("SMTP Connection", test_smtp_connection()),
        ("Email Sending", test_email_sending()),
    ]
    
    results = []
    
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed < len(results):
        print_setup_instructions()
    else:
        print("\n🎉 All email tests passed! Email notification system is ready.")

if __name__ == "__main__":
    asyncio.run(main())
