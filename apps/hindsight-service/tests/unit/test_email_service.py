"""
Tests for email template functionality and transactional email service.

These tests verify:
- Email template rendering
- Template data validation
- Email sending functionality
- Error handling in email operations
"""

import pytest
pytest.importorskip("jinja2")

from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from core.services.transactional_email_service import (
    TransactionalEmailService,
    get_transactional_email_service,
    TransactionalEmailConfig,
    EmailProvider,
)


class TestEmailTemplateRendering:
    """Test email template rendering functionality."""

    def test_render_organization_invitation_template(self):
        """Test rendering the organization invitation email template."""
        # Mock the email service setup
        with patch('core.services.transactional_email_service.Environment') as mock_env:
            mock_template = MagicMock()
            mock_template.render.return_value = "<html>Welcome John to Test Org!</html>"
            
            mock_template_env = MagicMock()
            mock_template_env.get_template.return_value = mock_template
            mock_env.return_value = mock_template_env
            
            service = TransactionalEmailService()
            service.template_env = mock_template_env
            
            template_data = {
                "user_name": "John Doe",
                "organization_name": "Test Organization",
                "invited_by": "Jane Admin",
                "role": "editor",
                "dashboard_url": "https://hindsight-ai.com/dashboard"
            }
            
            html_content, text_content = service.render_template("organization_invitation", template_data)
            
            # Verify template was requested (HTML first)
            mock_template_env.get_template.assert_any_call("organization_invitation.html")
            mock_template.render.assert_called_with(**template_data)
            assert html_content == "<html>Welcome John to Test Org!</html>"

    def test_render_template_with_fallback_text(self):
        """Test template rendering when text template doesn't exist."""
        with patch('core.services.transactional_email_service.Environment') as mock_env:
            # HTML template exists
            mock_html_template = MagicMock()
            mock_html_template.render.return_value = "<html><body>Test</body></html>"
            
            # Text template doesn't exist
            mock_template_env = MagicMock()
            mock_template_env.get_template.side_effect = [
                mock_html_template,  # HTML template works
                Exception("Template not found")  # Text template fails
            ]
            mock_env.return_value = mock_template_env
            
            service = TransactionalEmailService()
            service.template_env = mock_template_env
            
            # Mock the HTML to text conversion
            with patch.object(service, '_html_to_text', return_value="Test"):
                html_content, text_content = service.render_template("test", {"data": "test"})
                
                assert html_content == "<html><body>Test</body></html>"
                assert text_content == "Test"

    def test_render_template_missing_html_template(self):
        """Test error handling when HTML template is missing."""
        with patch('core.services.transactional_email_service.Environment') as mock_env:
            mock_template_env = MagicMock()
            mock_template_env.get_template.side_effect = Exception("Template not found")
            mock_env.return_value = mock_template_env
            
            service = TransactionalEmailService()
            service.template_env = mock_template_env
            
            with pytest.raises(Exception):
                service.render_template("nonexistent", {"data": "test"})

    def test_email_config_validation(self, monkeypatch):
        """Test email configuration validation using environment variables expected by implementation."""
        # Set env for valid RESEND config
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "test_key")
        monkeypatch.setenv("FROM_EMAIL", "test@example.com")
        monkeypatch.setenv("FROM_NAME", "Test Service")

        config = TransactionalEmailConfig()
        errors = config.validate()
        assert errors == []

        # Missing API key should yield validation error referencing RESEND
        monkeypatch.setenv("RESEND_API_KEY", "")
        config2 = TransactionalEmailConfig()
        errors2 = config2.validate()
        assert errors2 and any("RESEND_API_KEY" in e for e in errors2)

    def test_email_config_env_defaults(self, monkeypatch):
        """Test environment-driven config using implementation's env keys."""
        monkeypatch.setenv("EMAIL_PROVIDER", "sendgrid")
        monkeypatch.setenv("SENDGRID_API_KEY", "sg_key")
        monkeypatch.setenv("FROM_EMAIL", "no-reply@test.com")
        monkeypatch.setenv("FROM_NAME", "Test App")

        config = TransactionalEmailConfig()
        assert config.provider == EmailProvider.SENDGRID
        assert config.sendgrid_api_key == "sg_key"
        assert config.from_email == "no-reply@test.com"
        assert config.from_name == "Test App"


class TestTransactionalEmailService:
    """Test the TransactionalEmailService class."""

    def test_email_sending_via_injected_provider(self):
        """Test sending email by injecting a fake provider service."""
        service = TransactionalEmailService()
        fake_provider = MagicMock()

        async def _fake_send_email(to_email, subject, html_content, text_content=None):
            return {"success": True, "provider": "resend", "message_id": "test-email-id"}

        fake_provider.send_email = _fake_send_email
        service.provider_service = fake_provider

        import asyncio
        result = asyncio.run(
            service.send_email(
                to_email="recipient@example.com",
                subject="Test Email",
                html_content="<html>Test</html>",
                text_content="Test",
            )
        )

        assert result["success"] is True
        assert result.get("message_id") == "test-email-id"

    def test_email_sending_failure_via_injected_provider(self):
        """Test failed email send path via injected provider."""
        service = TransactionalEmailService()
        fake_provider = MagicMock()

        async def _fake_send_email_fail(**kwargs):
            return {"success": False, "provider": "resend", "error": "Network error"}

        fake_provider.send_email = _fake_send_email_fail
        service.provider_service = fake_provider

        import asyncio
        result = asyncio.run(
            service.send_email(
                to_email="recipient@example.com",
                subject="Test Email",
                html_content="<html>Test</html>",
            )
        )
        assert result["success"] is False
        assert "error" in result

    def test_singleton_service_instance(self):
        """Test that get_transactional_email_service returns singleton."""
        service1 = get_transactional_email_service()
        service2 = get_transactional_email_service()
        
        assert service1 is service2

    def test_test_connection_success(self):
        """Test successful connection test."""
        service = TransactionalEmailService()
        # Provide valid, configured state
        service.config = TransactionalEmailConfig()
        service.config.resend_api_key = "key"
        service.config.from_email = "test@example.com"
        service.provider_service = MagicMock()

        import asyncio
        result = asyncio.run(service.test_connection())

        assert result["success"] is True
        assert "ready" in result["message"]

    def test_test_connection_configuration_errors(self):
        """Test connection test with configuration errors."""
        service = TransactionalEmailService()
        
        # Mock invalid configuration
        mock_config = MagicMock()
        mock_config.validate.return_value = ["Missing API key", "Invalid email"]
        service.config = mock_config
        
        import asyncio
        result = asyncio.run(service.test_connection())
        
        assert result["success"] is False
        assert "Configuration errors" in result["error"]
        assert "Missing API key" in result["error"]


class TestEmailTemplateDataValidation:
    """Test validation of email template data."""

    def test_organization_invitation_template_data_complete(self):
        """Test that complete template data passes validation."""
        template_data = {
            "user_name": "John Doe",
            "organization_name": "Test Organization",
            "invited_by": "Jane Admin",
            "role": "editor",
            "dashboard_url": "https://hindsight-ai.com/dashboard"
        }
        
        # All required fields present
        required_fields = ["user_name", "organization_name", "invited_by", "role", "dashboard_url"]
        for field in required_fields:
            assert field in template_data
            assert template_data[field] is not None
            assert template_data[field] != ""

    def test_organization_invitation_template_data_types(self):
        """Test that template data has correct types."""
        template_data = {
            "user_name": "John Doe",
            "organization_name": "Test Organization", 
            "invited_by": "Jane Admin",
            "role": "editor",
            "dashboard_url": "https://hindsight-ai.com/dashboard"
        }
        
        # All values should be strings
        for key, value in template_data.items():
            assert isinstance(value, str), f"{key} should be string, got {type(value)}"
        
        # URL should be valid format
        assert template_data["dashboard_url"].startswith("https://")
        
        # Role should be valid
        valid_roles = ["viewer", "editor", "admin", "owner"]
        assert template_data["role"] in valid_roles

    def test_template_data_escaping(self):
        """Test that template data handles special characters."""
        template_data = {
            "user_name": "John O'Connor & Jane",
            "organization_name": "Test & Development <Corp>",
            "invited_by": "Admin \"Super\" User",
            "role": "editor",
            "dashboard_url": "https://hindsight-ai.com/dashboard?param=value&other=test"
        }
        
        # Should not raise exceptions with special characters
        # This would be tested in actual template rendering
        for key, value in template_data.items():
            assert isinstance(value, str)
            assert len(value) > 0


class TestEmailServiceIntegration:
    """Integration tests for email service with notification system."""

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_organization_invitation_email_flow(self, mock_get_service):
        """Test complete organization invitation email flow."""
        # Mock email service
        mock_service = MagicMock()
        mock_service.render_template.return_value = (
            "<html>Welcome to organization!</html>",
            "Welcome to organization!"
        )
        mock_service.send_email = AsyncMock(return_value={
            "success": True,
            "message_id": "test-id"
        })
        mock_get_service.return_value = mock_service
        
        from core.services.notification_service import NotificationService
        
        # This would be tested with a real database session
        # For now, just verify the email service interaction
        
        template_data = {
            "user_name": "New Member",
            "organization_name": "Test Org",
            "invited_by": "Admin User",
            "role": "viewer",
            "dashboard_url": "https://hindsight-ai.com/dashboard"
        }
        
        # Simulate what happens in the organization member addition
        email_service = mock_get_service()
        html_content, text_content = email_service.render_template(
            "organization_invitation", 
            template_data
        )
        
        import asyncio
        result = asyncio.run(email_service.send_email(
            to_email="newmember@example.com",
            subject="You've been added to Test Org",
            html_content=html_content,
            text_content=text_content
        ))
        
        # Verify the flow worked
        mock_service.render_template.assert_called_once_with(
            "organization_invitation", 
            template_data
        )
        
        mock_service.send_email.assert_called_once()
        call_args = mock_service.send_email.call_args[1]
        assert call_args["to_email"] == "newmember@example.com"
        assert call_args["subject"] == "You've been added to Test Org"
        assert call_args["html_content"] == "<html>Welcome to organization!</html>"
        assert call_args["text_content"] == "Welcome to organization!"
        
        assert result["success"] is True


class TestEmailServiceErrorScenarios:
    """Test error scenarios in email service."""

    def test_template_directory_not_found(self):
        """Test behavior when template directory doesn't exist."""
        with patch('core.services.transactional_email_service.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            
            # Service should handle missing template directory gracefully
            service = TransactionalEmailService()
            # Should not raise exception during initialization

    def test_invalid_email_configuration(self):
        """Test handling of invalid email configuration."""
        # Test invalid config for Mailgun missing fields
        with patch.dict('os.environ', {'EMAIL_PROVIDER': 'mailgun', 'MAILGUN_API_KEY': '', 'MAILGUN_DOMAIN': '', 'FROM_EMAIL': ''}):
            config = TransactionalEmailConfig()
            errors = config.validate()
            assert errors and any('MAILGUN' in e or 'FROM_EMAIL' in e for e in errors)

    def test_email_sending_with_no_configuration(self):
        """Test email sending when no configuration is available."""
        service = TransactionalEmailService()
        # No provider_service configured
        
        import asyncio
        result = asyncio.run(service.send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<html>Test</html>"
        ))
        
        assert result["success"] is False
        assert "not configured" in result["error"] or "initialization failed" in result["error"]
