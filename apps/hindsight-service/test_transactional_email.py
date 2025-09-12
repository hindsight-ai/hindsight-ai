"""
Transactional Email Service Test Script

This script tests the transactional email functionality including:
- Configuration validation for multiple providers (Resend, SendGrid, Mailgun)
- Template rendering
- Provider connection testing
- Email sending with proper error handling

Run with: uv run python test_transactional_email.py
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.transactional_email_service import (
    TransactionalEmailService, 
    TransactionalEmailConfig, 
    EmailProvider
)

async def test_email_configuration():
    """Test email service configuration for different providers."""
    print("🔧 Testing Transactional Email Configuration...")
    
    config = TransactionalEmailConfig()
    
    print(f"Selected Provider: {config.provider.value}")
    print(f"From Email: {config.from_email}")
    print(f"From Name: {config.from_name}")
    print(f"Template Dir: {config.template_dir}")
    
    if not config.is_configured():
        print("⚠️  Email service not fully configured. Check environment variables:")
        validation_errors = config.validate()
        for error in validation_errors:
            print(f"   - {error}")
        return False
    
    print("✅ Email configuration looks good!")
    return True

async def test_email_templates():
    """Test email template rendering with transactional service."""
    print("\n📄 Testing Email Template Rendering...")
    
    email_service = TransactionalEmailService()
    
    try:
        # Test organization invitation template
        template_context = {
            'organization_name': 'Test Organization',
            'inviter_name': 'John Doe',
            'accept_url': 'https://example.com/accept/123',
            'decline_url': 'https://example.com/decline/123',
            'current_year': 2025
        }
        
        html_content, text_content = email_service.render_template(
            'organization_invitation',
            template_context
        )
        
        print("✅ Organization invitation template rendered successfully")
        print(f"   HTML length: {len(html_content)} chars")
        print(f"   Text length: {len(text_content)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        return False

async def test_provider_connection():
    """Test connection to the configured email provider."""
    print("\n🔌 Testing Email Provider Connection...")
    
    email_service = TransactionalEmailService()
    
    try:
        result = await email_service.test_connection()
        
        if result['success']:
            print("✅ Email provider connection test successful")
            print(f"   Provider: {result.get('provider', 'unknown')}")
            print(f"   Message: {result['message']}")
            return True
        else:
            print(f"❌ Email provider connection test failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Email provider connection test error: {e}")
        return False

async def test_email_sending():
    """Test actual email sending via transactional service."""
    print("\n📧 Testing Transactional Email Sending...")
    
    # Check if we have a test email address
    test_email = os.getenv('TEST_EMAIL')
    if not test_email:
        print("⚠️  Skipping email sending test. Set TEST_EMAIL environment variable to test.")
        return True
    
    email_service = TransactionalEmailService()
    
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
            'organization_invitation',
            template_context
        )
        
        # Send test email
        result = await email_service.send_email(
            to_email=test_email,
            subject="[TEST] Hindsight AI Transactional Email Test",
            html_content=html_content,
            text_content=text_content
        )
        
        if result['success']:
            print(f"✅ Test email sent successfully to {test_email}")
            print(f"   Provider: {result.get('provider', 'unknown')}")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            return True
        else:
            print(f"❌ Email sending failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions for transactional email testing."""
    print("\n📋 Transactional Email Setup Instructions:")
    print("\n🎯 Recommended: Resend (Best for new projects)")
    print("1. Sign up at https://resend.com")
    print("2. Get your API key from https://resend.com/api-keys") 
    print("3. Set environment variables:")
    print("   export EMAIL_PROVIDER='resend'")
    print("   export RESEND_API_KEY='re_your_api_key_here'")
    print("   export FROM_EMAIL='noreply@yourdomain.com'")
    print("   export TEST_EMAIL='your-test-email@example.com'")
    
    print("\n📧 Alternative: SendGrid (Industry standard)")
    print("1. Sign up at https://sendgrid.com")
    print("2. Get your API key from https://app.sendgrid.com/settings/api_keys")
    print("3. Set environment variables:")
    print("   export EMAIL_PROVIDER='sendgrid'")
    print("   export SENDGRID_API_KEY='SG.your_api_key_here'")
    print("   export FROM_EMAIL='noreply@yourdomain.com'")
    
    print("\n🔧 Alternative: Mailgun (Developer-focused)")
    print("1. Sign up at https://mailgun.com")
    print("2. Get your API key and domain from https://app.mailgun.com/app/domains")
    print("3. Set environment variables:")
    print("   export EMAIL_PROVIDER='mailgun'")
    print("   export MAILGUN_API_KEY='your_api_key_here'")
    print("   export MAILGUN_DOMAIN='mg.yourdomain.com'")
    print("   export FROM_EMAIL='noreply@yourdomain.com'")
    
    print("\n💡 All providers offer generous free tiers perfect for getting started!")

async def test_all_providers():
    """Test all available providers if configured."""
    print("\n🔄 Testing All Configured Providers...")
    
    providers_to_test = []
    
    # Check which providers are configured
    if os.getenv('RESEND_API_KEY'):
        providers_to_test.append(EmailProvider.RESEND)
    if os.getenv('SENDGRID_API_KEY'):
        providers_to_test.append(EmailProvider.SENDGRID)
    if os.getenv('MAILGUN_API_KEY') and os.getenv('MAILGUN_DOMAIN'):
        providers_to_test.append(EmailProvider.MAILGUN)
    
    if not providers_to_test:
        print("⚠️  No email providers configured for testing")
        return []
    
    results = []
    for provider in providers_to_test:
        print(f"\n--- Testing {provider.value.upper()} ---")
        
        # Create config for this provider
        original_provider = os.getenv('EMAIL_PROVIDER')
        os.environ['EMAIL_PROVIDER'] = provider.value
        
        try:
            config = TransactionalEmailConfig()
            service = TransactionalEmailService(config)
            
            # Test connection
            result = await service.test_connection()
            results.append((provider.value, result['success']))
            
            if result['success']:
                print(f"✅ {provider.value} connection: SUCCESS")
            else:
                print(f"❌ {provider.value} connection: FAILED - {result['error']}")
                
        except Exception as e:
            print(f"❌ {provider.value} error: {e}")
            results.append((provider.value, False))
        
        finally:
            # Restore original provider
            if original_provider:
                os.environ['EMAIL_PROVIDER'] = original_provider
            elif 'EMAIL_PROVIDER' in os.environ:
                del os.environ['EMAIL_PROVIDER']
    
    return results

async def main():
    """Run all transactional email tests."""
    print("🚀 Starting Transactional Email Service Tests\n")
    
    tests = [
        ("Configuration", test_email_configuration()),
        ("Template Rendering", test_email_templates()),
        ("Provider Connection", test_provider_connection()),
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
    
    # Test all providers if multiple are configured
    provider_results = await test_all_providers()
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary:")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    if provider_results:
        print("\n📧 Provider-Specific Results:")
        for provider, success in provider_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {provider.upper()}")
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed < len(results):
        print_setup_instructions()
    else:
        print("\n🎉 All transactional email tests passed! Email system is ready for production.")
        print("\n💡 Benefits of transactional email services:")
        print("   • Built-in deliverability optimization")
        print("   • Automatic spam protection")
        print("   • Email analytics and tracking")
        print("   • Scalable infrastructure")
        print("   • Rate limiting and abuse prevention")

if __name__ == "__main__":
    asyncio.run(main())
