"""Slack adapter - incoming webhook notifications."""

import httpx
import structlog

logger = structlog.get_logger()


async def send_slack_message(
    webhook_url: str,
    text: str,
    blocks: list | None = None,
) -> bool:
    """Send a message via Slack incoming webhook."""
    if not webhook_url:
        logger.debug("slack_skipped_no_url")
        return False

    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("slack_message_sent")
        return True
    except Exception as e:
        logger.error("slack_send_failed", error=str(e))
        return False
