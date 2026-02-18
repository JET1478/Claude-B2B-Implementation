"""Notification service - Slack webhook + internal logging."""

import json

import httpx
import structlog

logger = structlog.get_logger()


async def send_slack_notification(
    webhook_url: str,
    text: str,
    channel: str | None = None,
    blocks: list | None = None,
) -> bool:
    """Send a notification via Slack incoming webhook."""
    if not webhook_url:
        logger.info("slack_notification_skipped_no_webhook")
        return False

    payload: dict = {"text": text}
    if channel:
        payload["channel"] = channel
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("slack_notification_sent", text=text[:100])
        return True
    except Exception as e:
        logger.error("slack_notification_failed", error=str(e))
        return False


def format_support_notification(ticket_data: dict) -> tuple[str, list]:
    """Format a support ticket notification for Slack."""
    text = f"New support ticket: {ticket_data.get('subject', 'No subject')}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "New Support Ticket"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*From:* {ticket_data.get('from_email', 'Unknown')}"},
                {"type": "mrkdwn", "text": f"*Priority:* {ticket_data.get('priority', 'Pending')}"},
                {"type": "mrkdwn", "text": f"*Category:* {ticket_data.get('category', 'Pending')}"},
                {"type": "mrkdwn", "text": f"*Sentiment:* {ticket_data.get('sentiment', 'Pending')}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Subject:* {ticket_data.get('subject', 'No subject')}\n{ticket_data.get('body', '')[:200]}..."}
        },
    ]
    return text, blocks


def format_lead_notification(lead_data: dict) -> tuple[str, list]:
    """Format a lead notification for Slack."""
    text = f"New lead: {lead_data.get('name', 'Unknown')} from {lead_data.get('company', 'Unknown')}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "New Sales Lead"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Name:* {lead_data.get('name', 'Unknown')}"},
                {"type": "mrkdwn", "text": f"*Company:* {lead_data.get('company', 'Unknown')}"},
                {"type": "mrkdwn", "text": f"*Email:* {lead_data.get('email', 'Unknown')}"},
                {"type": "mrkdwn", "text": f"*Score:* {lead_data.get('score', 'Pending')}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Message:* {lead_data.get('message', 'No message')[:200]}"}
        },
    ]
    return text, blocks
