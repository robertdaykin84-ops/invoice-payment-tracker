"""
Email Notification Service for Client Onboarding

Sends SMTP email notifications for key workflow events.
Supports demo mode when SMTP is not configured.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM = os.environ.get('SMTP_FROM', 'Client Onboarding <noreply@example.com>')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'

# Recipient Configuration
MLRO_EMAIL = os.environ.get('NOTIFICATION_MLRO_EMAIL', '')
BOARD_EMAIL = os.environ.get('NOTIFICATION_BOARD_EMAIL', '')
COMPLIANCE_EMAIL = os.environ.get('NOTIFICATION_COMPLIANCE_EMAIL', '')

# Demo mode - activated when SMTP not configured
DEMO_MODE = not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

# Store sent emails in demo mode for testing
_demo_sent_emails: List[Dict] = []


def _send_smtp(to: List[str], subject: str, html_body: str, text_body: str = None) -> Dict[str, Any]:
    """
    Send email via SMTP.

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        html_body: HTML email content
        text_body: Plain text fallback (optional)

    Returns:
        Dict with status and message
    """
    if not to:
        return {'status': 'skipped', 'message': 'No recipients specified'}

    # Filter out empty recipients
    recipients = [r for r in to if r]
    if not recipients:
        return {'status': 'skipped', 'message': 'No valid recipients'}

    if DEMO_MODE:
        # Log and store for testing
        email_record = {
            'to': recipients,
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'sent_at': datetime.now().isoformat(),
            'demo_mode': True
        }
        _demo_sent_emails.append(email_record)

        logger.info(f"[DEMO] Email would be sent:")
        logger.info(f"  To: {', '.join(recipients)}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  Body preview: {html_body[:200]}...")

        return {
            'status': 'demo',
            'message': 'Email logged in demo mode (not actually sent)',
            'recipients': recipients
        }

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM
        msg['To'] = ', '.join(recipients)

        # Add plain text part
        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))

        # Add HTML part
        msg.attach(MIMEText(html_body, 'html'))

        # Connect and send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, recipients, msg.as_string())

        logger.info(f"Email sent to {', '.join(recipients)}: {subject}")
        return {
            'status': 'success',
            'message': 'Email sent successfully',
            'recipients': recipients
        }

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {e}")
        return {
            'status': 'error',
            'message': f'SMTP error: {str(e)}',
            'recipients': recipients
        }
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            'status': 'error',
            'message': f'Error: {str(e)}',
            'recipients': recipients
        }


def get_demo_sent_emails() -> List[Dict]:
    """Get list of emails sent in demo mode (for testing)."""
    return _demo_sent_emails.copy()


def clear_demo_sent_emails():
    """Clear demo sent emails (for testing)."""
    _demo_sent_emails.clear()
