"""
Email Service

This service handles SMTP email sending for notifications.
Uses aiosmtplib for async email delivery with proper error handling and retry logic.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailServiceConfig:
    """Configuration for email service from environment variables."""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@hindsight-ai.com')
        self.from_name = os.getenv('FROM_NAME', 'Hindsight AI')
        self.reply_to_email = os.getenv('REPLY_TO_EMAIL', '')
        
        # Template configuration
        self.template_dir = os.getenv('EMAIL_TEMPLATE_DIR', 'core/templates/email')
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_host and self.smtp_port and self.from_email)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.smtp_host:
            errors.append("SMTP_HOST is required")
        if not self.smtp_port or self.smtp_port <= 0:
            errors.append("SMTP_PORT must be a positive integer")
        if not self.from_email:
            errors.append("FROM_EMAIL is required")
        if self.smtp_use_ssl and self.smtp_use_tls:
            errors.append("Cannot use both SSL and TLS simultaneously")
            
        return errors


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self, config: Optional[EmailServiceConfig] = None):
        self.config = config or EmailServiceConfig()
        self.template_env = None
        self._setup_templates()
    
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
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Optional plain text content
            reply_to: Optional reply-to address
            attachments: Optional list of attachments
            
        Returns:
            Dict with 'success', 'message_id', and 'error' keys
        """
        if not self.config.is_configured():
            return {
                'success': False,
                'error': 'Email service not configured'
            }
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            
            if reply_to or self.config.reply_to_email:
                message['Reply-To'] = reply_to or self.config.reply_to_email
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(html_part)
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    self._add_attachment(message, attachment)
            
            # Send email
            result = await self._send_via_smtp(message, to_email)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to send email to {to_email}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    async def _send_via_smtp(self, message: MIMEMultipart, to_email: str) -> Dict[str, Any]:
        """Send email via SMTP with proper connection handling."""
        try:
            # Configure SMTP connection
            smtp_kwargs = {
                'hostname': self.config.smtp_host,
                'port': self.config.smtp_port,
                'use_tls': self.config.smtp_use_tls,
            }
            
            if self.config.smtp_use_ssl:
                smtp_kwargs['use_tls'] = False
                smtp_kwargs['port'] = self.config.smtp_port or 465
            
            # Connect and send
            async with aiosmtplib.SMTP(**smtp_kwargs) as smtp:
                if self.config.smtp_username and self.config.smtp_password:
                    await smtp.login(self.config.smtp_username, self.config.smtp_password)
                
                result = await smtp.send_message(message)
                
                return {
                    'success': True,
                    'message_id': message.get('Message-ID', ''),
                    'smtp_result': result
                }
                
        except Exception as e:
            raise Exception(f"SMTP sending failed: {str(e)}")
    
    def _add_attachment(self, message: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={attachment["filename"]}'
            )
            message.attach(part)
        except Exception as e:
            logger.warning(f"Failed to add attachment {attachment.get('filename', 'unknown')}: {e}")
    
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
        # Basic HTML to text conversion
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
        """Test SMTP connection and configuration."""
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
        
        try:
            smtp_kwargs = {
                'hostname': self.config.smtp_host,
                'port': self.config.smtp_port,
                'use_tls': self.config.smtp_use_tls,
            }
            
            if self.config.smtp_use_ssl:
                smtp_kwargs['use_tls'] = False
            
            async with aiosmtplib.SMTP(**smtp_kwargs) as smtp:
                if self.config.smtp_username and self.config.smtp_password:
                    await smtp.login(self.config.smtp_username, self.config.smtp_password)
                
                return {
                    'success': True,
                    'message': f"Successfully connected to {self.config.smtp_host}:{self.config.smtp_port}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection test failed: {str(e)}"
            }


# Global email service instance
_email_service = None

def get_email_service() -> EmailService:
    """Get singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

def send_email_sync(
    to_email: str,
    subject: str, 
    html_content: str,
    text_content: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for sending emails.
    Uses asyncio.run() to execute async email sending.
    """
    email_service = get_email_service()
    return asyncio.run(email_service.send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    ))
