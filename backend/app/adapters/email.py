"""Email adapter - SMTP send/draft support."""

import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
import structlog

from app.config import settings

logger = structlog.get_logger()


async def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    from_email: str | None = None,
    smtp_config: dict | None = None,
) -> bool:
    """Send an email via SMTP.

    Args:
        to_email: Recipient address
        subject: Email subject
        body_html: HTML body content
        from_email: Sender address (defaults to smtp_user)
        smtp_config: Optional per-tenant SMTP config override
    """
    config = smtp_config or {}
    host = config.get("host", settings.smtp_host)
    port = config.get("port", settings.smtp_port)
    user = config.get("user", settings.smtp_user)
    password = config.get("password", settings.smtp_password)
    use_tls = config.get("use_tls", settings.smtp_use_tls)
    sender = from_email or user

    if not host or host == "localhost":
        logger.info("email_draft_mode_smtp_not_configured",
                     to=to_email, subject=subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=user,
            password=password,
            use_tls=use_tls,
        )
        logger.info("email_sent", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", error=str(e), to=to_email)
        return False


def get_tenant_smtp_config(smtp_config_json: str | None) -> dict | None:
    """Parse tenant SMTP config from JSON string."""
    if not smtp_config_json:
        return None
    try:
        return json.loads(smtp_config_json)
    except (json.JSONDecodeError, TypeError):
        return None
