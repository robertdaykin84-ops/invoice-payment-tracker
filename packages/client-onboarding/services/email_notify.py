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
from html import escape
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


# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="border-bottom: 3px solid #0d6efd; padding-bottom: 15px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 20px; color: #212529;">Client Onboarding System</h1>
    </div>

    {content}

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d;">
        <p>This is an automated notification from the Client Onboarding System.</p>
        <p>CONFIDENTIAL: This email may contain sensitive compliance information.</p>
    </div>
</body>
</html>
"""

TEMPLATES = {
    'edd_triggered': {
        'subject': '[ALERT] EDD Required - {sponsor_name}',
        'content': """
        <div style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 15px; margin-bottom: 20px;">
            <strong style="color: #856404;">⚠️ Enhanced Due Diligence Required</strong>
        </div>

        <h2 style="color: #212529; font-size: 18px;">Risk Assessment Alert</h2>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 140px; color: #6c757d;">Client:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>{sponsor_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Fund:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{fund_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Risk Score:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong style="color: {risk_color};">{risk_score} ({risk_rating})</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Approval Level:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{approval_level}</td>
            </tr>
        </table>

        <h3 style="font-size: 14px; color: #495057;">Risk Factors:</h3>
        <ul style="margin: 0; padding-left: 20px;">
            {risk_factors}
        </ul>

        <div style="margin-top: 25px;">
            <a href="{app_url}/onboarding/{onboarding_id}/phase/4" style="display: inline-block; background-color: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Review in System</a>
        </div>
        """
    },

    'approval_required': {
        'subject': '[ACTION] Approval Required - {sponsor_name}',
        'content': """
        <div style="background-color: #cfe2ff; border: 1px solid #0d6efd; border-radius: 4px; padding: 15px; margin-bottom: 20px;">
            <strong style="color: #084298;">📋 Approval Required</strong>
        </div>

        <h2 style="color: #212529; font-size: 18px;">Onboarding Pending {approval_level} Approval</h2>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 140px; color: #6c757d;">Client:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>{sponsor_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Fund:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{fund_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Risk Rating:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong style="color: {risk_color};">{risk_rating}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">EDD Required:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{edd_required}</td>
            </tr>
        </table>

        <p>Screening has been completed and this onboarding requires <strong>{approval_level}</strong> approval before proceeding.</p>

        <div style="margin-top: 25px;">
            <a href="{app_url}/onboarding/{onboarding_id}/phase/6" style="display: inline-block; background-color: #198754; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Review &amp; Approve</a>
        </div>
        """
    },

    'screening_complete': {
        'subject': '[INFO] Screening Complete - {sponsor_name}',
        'content': """
        <h2 style="color: #212529; font-size: 18px;">Screening Completed</h2>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 140px; color: #6c757d;">Client:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>{sponsor_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Fund:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{fund_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Entities Screened:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{screened_count}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Risk Score:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong style="color: {risk_color};">{risk_score} ({risk_rating})</strong></td>
            </tr>
        </table>

        <h3 style="font-size: 14px; color: #495057;">Summary:</h3>
        <ul style="margin: 0; padding-left: 20px;">
            <li>Clear: {clear_count}</li>
            <li>Review Required: {review_count}</li>
            <li>Hits: {hits_count}</li>
        </ul>

        <div style="margin-top: 25px;">
            <a href="{app_url}/onboarding/{onboarding_id}/phase/4" style="display: inline-block; background-color: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Results</a>
        </div>
        """
    },

    'phase_completed': {
        'subject': '[INFO] Phase {phase_num} Complete - {sponsor_name}',
        'content': """
        <h2 style="color: #212529; font-size: 18px;">Onboarding Progress Update</h2>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 140px; color: #6c757d;">Client:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>{sponsor_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Fund:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{fund_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Completed Phase:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Phase {phase_num}: {phase_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Next Phase:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">Phase {next_phase_num}: {next_phase_name}</td>
            </tr>
        </table>

        <div style="margin-top: 25px;">
            <a href="{app_url}/onboarding/{onboarding_id}/phase/{next_phase_num}" style="display: inline-block; background-color: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Continue Onboarding</a>
        </div>
        """
    },

    'onboarding_approved': {
        'subject': '[SUCCESS] Onboarding Approved - {sponsor_name}',
        'content': """
        <div style="background-color: #d1e7dd; border: 1px solid #198754; border-radius: 4px; padding: 15px; margin-bottom: 20px;">
            <strong style="color: #0f5132;">✓ Onboarding Approved</strong>
        </div>

        <h2 style="color: #212529; font-size: 18px;">Client Onboarding Complete</h2>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 140px; color: #6c757d;">Client:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>{sponsor_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Fund:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{fund_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Approved By:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{approved_by}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Date:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{approval_date}</td>
            </tr>
        </table>

        <p>The client onboarding has been approved and is ready for commercial engagement.</p>
        """
    },

    'onboarding_rejected': {
        'subject': '[REJECTED] Onboarding Declined - {sponsor_name}',
        'content': """
        <div style="background-color: #f8d7da; border: 1px solid #dc3545; border-radius: 4px; padding: 15px; margin-bottom: 20px;">
            <strong style="color: #842029;">✗ Onboarding Rejected</strong>
        </div>

        <h2 style="color: #212529; font-size: 18px;">Client Onboarding Declined</h2>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 140px; color: #6c757d;">Client:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>{sponsor_name}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Fund:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{fund_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Rejected By:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{rejected_by}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #6c757d;">Date:</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{rejection_date}</td>
            </tr>
        </table>

        <h3 style="font-size: 14px; color: #495057;">Reason:</h3>
        <p style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{rejection_reason}</p>
        """
    }
}


def _format_risk_factors(factors: list) -> str:
    """Safely format risk factors as HTML list items."""
    if not factors:
        return '<li>See full assessment in system</li>'
    return ''.join(f'<li>{escape(str(factor))}</li>' for factor in factors)


def _render_template(template_name: str, **kwargs) -> tuple:
    """
    Render an email template with the given variables.

    All string values are HTML-escaped to prevent XSS attacks.

    Returns:
        Tuple of (subject, html_body)
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")

    template = TEMPLATES[template_name]

    # HTML-escape all string values to prevent XSS
    escaped_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            escaped_kwargs[key] = escape(value)
        else:
            escaped_kwargs[key] = value

    # Add default values
    escaped_kwargs.setdefault('app_url', escape(os.environ.get('APP_URL', 'http://localhost:5000')))
    escaped_kwargs.setdefault('risk_color', '#212529')

    # Set risk color based on rating
    if kwargs.get('risk_rating'):
        rating = kwargs['risk_rating'].lower()
        if rating == 'high':
            escaped_kwargs['risk_color'] = '#dc3545'
        elif rating == 'medium':
            escaped_kwargs['risk_color'] = '#ffc107'
        else:
            escaped_kwargs['risk_color'] = '#198754'

    subject = template['subject'].format(**escaped_kwargs)
    content = template['content'].format(**escaped_kwargs)
    html_body = BASE_TEMPLATE.format(content=content)

    return subject, html_body


# =============================================================================
# NOTIFICATION FUNCTIONS
# =============================================================================

def notify_edd_triggered(
    onboarding: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    additional_recipients: List[str] = None
) -> Dict[str, Any]:
    """
    Send notification when EDD is triggered.

    Args:
        onboarding: Onboarding record dict
        risk_assessment: Risk assessment result dict
        additional_recipients: Extra email addresses to notify
    """
    recipients = [MLRO_EMAIL]
    if additional_recipients:
        recipients.extend(additional_recipients)

    # Build risk factors list
    factors = risk_assessment.get('factors', {})
    risk_factors_html = ''
    for key, factor in factors.items():
        if factor.get('score', 0) > 0:
            risk_factors_html += f"<li>{key.replace('_', ' ').title()}: {factor.get('reason', 'N/A')}</li>"

    if not risk_factors_html:
        risk_factors_html = '<li>See full assessment in system</li>'

    subject, html_body = _render_template(
        'edd_triggered',
        sponsor_name=onboarding.get('sponsor_name', 'Unknown'),
        fund_name=onboarding.get('fund_name', 'Unknown'),
        onboarding_id=onboarding.get('onboarding_id', 'N/A'),
        risk_score=round(risk_assessment.get('score', 0)),
        risk_rating=risk_assessment.get('rating', 'unknown').upper(),
        approval_level=risk_assessment.get('approval_level', 'N/A').upper(),
        risk_factors=risk_factors_html
    )

    return _send_smtp(recipients, subject, html_body)


def notify_approval_required(
    onboarding: Dict[str, Any],
    risk_assessment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send notification when approval is required.

    Args:
        onboarding: Onboarding record dict
        risk_assessment: Risk assessment result dict
    """
    approval_level = risk_assessment.get('approval_level', 'compliance')

    recipients = []
    if approval_level in ['mlro', 'board']:
        recipients.append(MLRO_EMAIL)
    if approval_level == 'board':
        recipients.append(BOARD_EMAIL)

    if not recipients:
        return {'status': 'skipped', 'message': 'No approval notification needed for compliance level'}

    subject, html_body = _render_template(
        'approval_required',
        sponsor_name=onboarding.get('sponsor_name', 'Unknown'),
        fund_name=onboarding.get('fund_name', 'Unknown'),
        onboarding_id=onboarding.get('onboarding_id', 'N/A'),
        risk_rating=risk_assessment.get('rating', 'unknown').upper(),
        edd_required='Yes' if risk_assessment.get('edd_required') else 'No',
        approval_level=approval_level.upper()
    )

    return _send_smtp(recipients, subject, html_body)


def notify_screening_complete(
    onboarding: Dict[str, Any],
    screening_results: List[Dict],
    risk_assessment: Dict[str, Any],
    analyst_email: str = None
) -> Dict[str, Any]:
    """
    Send notification when screening is complete.

    Args:
        onboarding: Onboarding record dict
        screening_results: List of screening result dicts
        risk_assessment: Risk assessment result dict
        analyst_email: Email of assigned analyst
    """
    recipients = [analyst_email] if analyst_email else [COMPLIANCE_EMAIL]

    # Calculate counts
    clear_count = sum(1 for r in screening_results if r.get('risk_level') == 'clear')
    review_count = sum(1 for r in screening_results if r.get('risk_level') in ['review', 'medium'])
    hits_count = sum(1 for r in screening_results if r.get('risk_level') in ['high', 'critical'])

    subject, html_body = _render_template(
        'screening_complete',
        sponsor_name=onboarding.get('sponsor_name', 'Unknown'),
        fund_name=onboarding.get('fund_name', 'Unknown'),
        onboarding_id=onboarding.get('onboarding_id', 'N/A'),
        screened_count=len(screening_results),
        risk_score=round(risk_assessment.get('score', 0)),
        risk_rating=risk_assessment.get('rating', 'unknown').upper(),
        clear_count=clear_count,
        review_count=review_count,
        hits_count=hits_count
    )

    return _send_smtp(recipients, subject, html_body)


def notify_phase_completed(
    onboarding: Dict[str, Any],
    phase_num: int,
    phase_name: str,
    next_phase_num: int = None,
    next_phase_name: str = None,
    analyst_email: str = None
) -> Dict[str, Any]:
    """
    Send notification when a phase is completed.

    Args:
        onboarding: Onboarding record dict
        phase_num: Completed phase number
        phase_name: Completed phase name
        next_phase_num: Next phase number
        next_phase_name: Next phase name
        analyst_email: Email of assigned analyst
    """
    recipients = [analyst_email] if analyst_email else [COMPLIANCE_EMAIL]

    # Default next phase info
    if next_phase_num is None:
        next_phase_num = phase_num + 1
    if next_phase_name is None:
        phase_names = {
            1: 'Enquiry', 2: 'Sponsor', 3: 'Fund', 4: 'Screening',
            5: 'EDD', 6: 'Approval', 7: 'Commercial', 8: 'Complete'
        }
        next_phase_name = phase_names.get(next_phase_num, 'Next Step')

    subject, html_body = _render_template(
        'phase_completed',
        sponsor_name=onboarding.get('sponsor_name', 'Unknown'),
        fund_name=onboarding.get('fund_name', 'Unknown'),
        onboarding_id=onboarding.get('onboarding_id', 'N/A'),
        phase_num=phase_num,
        phase_name=phase_name,
        next_phase_num=next_phase_num,
        next_phase_name=next_phase_name
    )

    return _send_smtp(recipients, subject, html_body)


def notify_onboarding_decision(
    onboarding: Dict[str, Any],
    approved: bool,
    decided_by: str = 'System',
    reason: str = None,
    notify_sponsor: bool = False,
    sponsor_email: str = None
) -> Dict[str, Any]:
    """
    Send notification when onboarding is approved or rejected.

    Args:
        onboarding: Onboarding record dict
        approved: True if approved, False if rejected
        decided_by: Name of person who made the decision
        reason: Rejection reason (if rejected)
        notify_sponsor: Whether to notify the sponsor
        sponsor_email: Sponsor's email address
    """
    recipients = [COMPLIANCE_EMAIL, MLRO_EMAIL]
    if notify_sponsor and sponsor_email:
        recipients.append(sponsor_email)

    template_name = 'onboarding_approved' if approved else 'onboarding_rejected'
    decision_date = datetime.now().strftime('%d %B %Y at %H:%M')

    kwargs = {
        'sponsor_name': onboarding.get('sponsor_name', 'Unknown'),
        'fund_name': onboarding.get('fund_name', 'Unknown'),
        'onboarding_id': onboarding.get('onboarding_id', 'N/A'),
    }

    if approved:
        kwargs['approved_by'] = decided_by
        kwargs['approval_date'] = decision_date
    else:
        kwargs['rejected_by'] = decided_by
        kwargs['rejection_date'] = decision_date
        kwargs['rejection_reason'] = reason or 'No reason provided'

    subject, html_body = _render_template(template_name, **kwargs)

    return _send_smtp(recipients, subject, html_body)