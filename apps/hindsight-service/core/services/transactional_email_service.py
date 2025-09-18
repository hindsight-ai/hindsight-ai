"""
Transactional Email Service

This service integrates with transactional email providers like Resend, SendGrid, and Mailgun
for reliable, secure, and scalable email delivery with built-in deliverability, security,
and analytics.

Supports:
- Resend (recommended for new projects)
- SendGrid (industry standard)
- Mailgun (developer-focused)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailProvider(Enum):
    """Supported email service providers."""
    RESEND = "resend"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"

class TransactionalEmailConfig:
    """Configuration for transactional email services."""
    
    def __init__(self):
        # Provider selection
        self.provider = EmailProvider(os.getenv('EMAIL_PROVIDER', 'resend').lower())
        
        # Common settings
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@hindsight-ai.com')
        self.from_name = os.getenv('FROM_NAME', 'Hindsight AI')
        self.reply_to_email = os.getenv('REPLY_TO_EMAIL', '')
        
        # Provider-specific API keys
        self.resend_api_key = os.getenv('RESEND_API_KEY', '')
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY', '')
        self.mailgun_api_key = os.getenv('MAILGUN_API_KEY', '')
        self.mailgun_domain = os.getenv('MAILGUN_DOMAIN', '')
        
        # Template configuration
        self.template_dir = os.getenv('EMAIL_TEMPLATE_DIR', 'core/templates/email')
        
        # Rate limiting
        self.rate_limit_per_hour = int(os.getenv('EMAIL_RATE_LIMIT_HOUR', '100'))
        self.rate_limit_per_day = int(os.getenv('EMAIL_RATE_LIMIT_DAY', '1000'))
    
    def is_configured(self) -> bool:
        """Check if the selected provider is properly configured."""
        if self.provider == EmailProvider.RESEND:
            return bool(self.resend_api_key and self.from_email)
        elif self.provider == EmailProvider.SENDGRID:
            return bool(self.sendgrid_api_key and self.from_email)
        elif self.provider == EmailProvider.MAILGUN:
            return bool(self.mailgun_api_key and self.mailgun_domain and self.from_email)
        return False
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.from_email:
            errors.append("FROM_EMAIL is required")
        
        if self.provider == EmailProvider.RESEND:
            if not self.resend_api_key:
                errors.append("RESEND_API_KEY is required for Resend provider")
        elif self.provider == EmailProvider.SENDGRID:
            if not self.sendgrid_api_key:
                errors.append("SENDGRID_API_KEY is required for SendGrid provider")
        elif self.provider == EmailProvider.MAILGUN:
            if not self.mailgun_api_key:
                errors.append("MAILGUN_API_KEY is required for Mailgun provider")
            if not self.mailgun_domain:
                errors.append("MAILGUN_DOMAIN is required for Mailgun provider")
        else:
            errors.append(f"Unknown email provider: {self.provider.value}")
        
        return errors

class ResendEmailService:
    """Email service implementation for Resend."""
    
    def __init__(self, config: TransactionalEmailConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup Resend client."""
        try:
            import resend
            resend.api_key = self.config.resend_api_key
            self.client = resend
        except ImportError:
            logger.error("Resend library not installed. Install with: pip install resend")
            raise
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via Resend."""
        try:
            email_data = {
                "from": f"{self.config.from_name} <{self.config.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            
            if text_content:
                email_data["text"] = text_content
            
            if self.config.reply_to_email:
                email_data["reply_to"] = self.config.reply_to_email
            
            result = self.client.Emails.send(email_data)
            
            return {
                'success': True,
                'provider': 'resend',
                'message_id': result['id'],
                'provider_response': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'provider': 'resend',
                'error': str(e)
            }

class SendGridEmailService:
    """Email service implementation for SendGrid."""
    
    def __init__(self, config: TransactionalEmailConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup SendGrid client."""
        try:
            from sendgrid import SendGridAPIClient
            self.client = SendGridAPIClient(api_key=self.config.sendgrid_api_key)
        except ImportError:
            logger.error("SendGrid library not installed. Install with: pip install sendgrid")
            raise
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid."""
        try:
            from sendgrid.helpers.mail import Mail, From, To, Subject, HtmlContent, PlainTextContent
            
            from_email = From(self.config.from_email, self.config.from_name)
            to_email_obj = To(to_email)
            subject_obj = Subject(subject)
            html_content_obj = HtmlContent(html_content)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email_obj,
                subject=subject_obj,
                html_content=html_content_obj
            )
            
            if text_content:
                mail.plain_text_content = PlainTextContent(text_content)
            
            if self.config.reply_to_email:
                mail.reply_to = self.config.reply_to_email
            
            response = self.client.send(mail)
            
            return {
                'success': True,
                'provider': 'sendgrid',
                'message_id': response.headers.get('X-Message-Id', ''),
                'status_code': response.status_code,
                'provider_response': response.headers
            }
            
        except Exception as e:
            return {
                'success': False,
                'provider': 'sendgrid',
                'error': str(e)
            }

class MailgunEmailService:
    """Email service implementation for Mailgun."""
    
    def __init__(self, config: TransactionalEmailConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup Mailgun client."""
        try:
            import requests
            self.requests = requests
            self.base_url = f"https://api.mailgun.net/v3/{self.config.mailgun_domain}"
        except ImportError:
            logger.error("Requests library not found")
            raise
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via Mailgun."""
        try:
            data = {
                "from": f"{self.config.from_name} <{self.config.from_email}>",
                "to": to_email,
                "subject": subject,
                "html": html_content,
            }
            
            if text_content:
                data["text"] = text_content
            
            if self.config.reply_to_email:
                data["h:Reply-To"] = self.config.reply_to_email
            
            response = self.requests.post(
                f"{self.base_url}/messages",
                auth=("api", self.config.mailgun_api_key),
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'provider': 'mailgun',
                    'message_id': result.get('id', ''),
                    'provider_response': result
                }
            else:
                return {
                    'success': False,
                    'provider': 'mailgun',
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
            
        except Exception as e:
            return {
                'success': False,
                'provider': 'mailgun',
                'error': str(e)
            }

class TransactionalEmailService:
    """Main transactional email service that delegates to provider implementations."""
    
    def __init__(self, config: Optional[TransactionalEmailConfig] = None):
        self.config = config or TransactionalEmailConfig()
        self.provider_service = None
        self.template_env = None
        self._setup_provider()
        self._setup_templates()
    
    def _setup_provider(self):
        """Setup the email provider service."""
        if not self.config.is_configured():
            logger.warning("Email service not configured")
            return
        
        try:
            if self.config.provider == EmailProvider.RESEND:
                self.provider_service = ResendEmailService(self.config)
                logger.info("Initialized Resend email service")
            elif self.config.provider == EmailProvider.SENDGRID:
                self.provider_service = SendGridEmailService(self.config)
                logger.info("Initialized SendGrid email service")
            elif self.config.provider == EmailProvider.MAILGUN:
                self.provider_service = MailgunEmailService(self.config)
                logger.info("Initialized Mailgun email service")
            else:
                logger.error(f"Unknown email provider: {self.config.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize email provider {self.config.provider}: {e}")
    
    def _setup_templates(self):
        """Setup Jinja2 template environment."""
        template_path = Path(self.config.template_dir)
        if template_path.exists():
            self.template_env = Environment(loader=FileSystemLoader(str(template_path)))
        else:
            logger.warning(f"Email template directory not found: {template_path}")
            self.template_env = Environment(loader=FileSystemLoader('.'))
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an email via the configured transactional email service.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Optional plain text content
            
        Returns:
            Dict with 'success', 'provider', 'message_id', and 'error' keys
        """
        if not self.provider_service:
            return {
                'success': False,
                'error': 'Email service not configured or initialization failed'
            }
        
        try:
            logger.info(f"Sending email to {to_email} via {self.config.provider.value}")
            
            result = await self.provider_service.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if result['success']:
                logger.info(f"Email sent successfully to {to_email} via {result['provider']}")
            else:
                logger.error(f"Email sending failed: {result['error']}")
            
            return result
            
        except Exception as e:
            error_msg = f"Email service error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render email template with context.
        
        Returns:
            Tuple of (html_content, text_content)
        """
        if not self.template_env:
            raise Exception("Template environment not configured")
        
        try:
            # Try to load HTML template
            html_template = self.template_env.get_template(f"{template_name}.html")
            html_content = html_template.render(**context)
            
            # Try to load text template (optional)
            text_content = ""
            try:
                text_template = self.template_env.get_template(f"{template_name}.txt")
                text_content = text_template.render(**context)
            except:
                # Generate basic text content from HTML if no text template
                text_content = self._html_to_text(html_content)
            
            return html_content, text_content
            
        except Exception as e:
            raise Exception(f"Template rendering failed for {template_name}: {str(e)}")
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to basic text content."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test email service configuration and connectivity."""
        if not self.config.is_configured():
            return {
                'success': False,
                'error': 'Email service not configured'
            }
        
        validation_errors = self.config.validate()
        if validation_errors:
            return {
                'success': False,
                'error': f"Configuration errors: {', '.join(validation_errors)}"
            }
        
        if not self.provider_service:
            return {
                'success': False,
                'error': 'Email provider service not initialized'
            }
        
        return {
            'success': True,
            'provider': self.config.provider.value,
            'message': f"Email service configured and ready ({self.config.provider.value})"
        }

# Global email service instance
_email_service = None

def get_transactional_email_service() -> TransactionalEmailService:
    """Get singleton transactional email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = TransactionalEmailService()
    return _email_service
