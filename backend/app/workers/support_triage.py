"""Support triage workflow worker task.

Pipeline:
1. Normalize ticket payload
2. 7B classify: category, priority, sentiment, team, needs_human
3. Claude draft: reply + internal notes + recommended action
4. Apply routing rules (from YAML config)
5. Notify via Slack
6. Optionally auto-send reply if autosend + confidence above threshold
"""

import json
import uuid
import time
import yaml
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.ticket import Ticket
from app.models.run import Run
from app.workers.base import (
    get_sync_session, load_tenant, update_run_status,
    create_audit_entry, create_model_router, run_async, logger,
)

import structlog

logger = structlog.get_logger()


def process_support_ticket(tenant_id: str, ticket_id: str, run_id: str):
    """Main entry point for support triage worker task."""
    session = get_sync_session()
    start_time = time.time()

    try:
        # Mark run as running
        update_run_status(session, run_id, "running", started_at=datetime.utcnow(), current_step="init")

        # Load tenant and ticket
        tenant = load_tenant(session, tenant_id)
        result = session.execute(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id)))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        router = create_model_router(tenant)
        steps_completed = []

        # --- Step 1: Classify with 7B ---
        update_run_status(session, run_id, "running", current_step="classify")
        ticket.status = "processing"
        session.commit()

        classify_result = run_async(_classify_ticket(router, ticket))
        _apply_classification(session, ticket, classify_result)
        steps_completed.append({"step": "classify", "model": classify_result["model"], "tokens": classify_result["tokens"]})

        create_audit_entry(
            session, tenant_id, run_id,
            action="classified", workflow="support_triage", step="classify",
            model_used=classify_result["model"],
            prompt_template_id="support_classify_v1",
            input_tokens=classify_result.get("input_tokens"),
            output_tokens=classify_result.get("output_tokens"),
            estimated_cost_usd=classify_result["cost"],
            input_summary=f"Subject: {ticket.subject}",
            output_summary=f"Cat: {ticket.category}, Pri: {ticket.priority}, Sent: {ticket.sentiment}",
            reason_code="auto_classify",
        )

        # --- Step 2: Draft reply with Claude ---
        update_run_status(session, run_id, "running", current_step="draft")

        draft_result = run_async(_draft_reply(router, ticket, tenant))
        _apply_draft(session, ticket, draft_result)
        steps_completed.append({"step": "draft", "model": draft_result["model"], "tokens": draft_result["tokens"]})

        create_audit_entry(
            session, tenant_id, run_id,
            action="draft_generated", workflow="support_triage", step="draft",
            model_used=draft_result["model"],
            prompt_template_id="support_draft_v1",
            input_tokens=draft_result.get("input_tokens"),
            output_tokens=draft_result.get("output_tokens"),
            estimated_cost_usd=draft_result["cost"],
            input_summary=f"Ticket body length: {len(ticket.body)} chars",
            output_summary=f"Draft length: {len(ticket.draft_reply or '')} chars",
            reason_code="auto_draft",
        )

        # --- Step 3: Apply routing rules ---
        update_run_status(session, run_id, "running", current_step="route")
        _apply_routing_rules(session, ticket, tenant)
        steps_completed.append({"step": "route", "model": None, "tokens": 0})

        # --- Step 4: Notify ---
        update_run_status(session, run_id, "running", current_step="notify")
        if tenant.slack_webhook_url:
            run_async(_notify_slack(tenant, ticket))
        steps_completed.append({"step": "notify", "model": None, "tokens": 0})

        # --- Step 5: Auto-send check ---
        auto_sent = False
        if (tenant.autosend_enabled and
                ticket.classification_confidence and
                ticket.classification_confidence >= tenant.confidence_threshold and
                not ticket.needs_human):
            update_run_status(session, run_id, "running", current_step="autosend")
            # In production, would call email adapter here
            auto_sent = True
            ticket.reply_sent = True
            ticket.status = "sent"
            create_audit_entry(
                session, tenant_id, run_id,
                action="email_sent", workflow="support_triage", step="autosend",
                reason_code="confidence_above_threshold",
                metadata={"confidence": ticket.classification_confidence},
            )
        else:
            ticket.status = "draft_ready"

        session.commit()
        steps_completed.append({"step": "autosend_check", "auto_sent": auto_sent})

        # --- Finalize run ---
        duration = round(time.time() - start_time, 3)
        total_claude_input = sum(s.get("input_tokens", 0) or 0 for s in steps_completed if s.get("model") and "claude" in str(s.get("model", "")))
        total_claude_output = sum(s.get("output_tokens", 0) or 0 for s in steps_completed if s.get("model") and "claude" in str(s.get("model", "")))

        update_run_status(
            session, run_id, "completed",
            completed_at=datetime.utcnow(),
            duration_seconds=duration,
            steps_completed=steps_completed,
            current_step="done",
            ticket_id=uuid.UUID(ticket_id),
        )

        logger.info("support_triage_completed",
                     tenant_id=tenant_id, ticket_id=ticket_id,
                     duration=duration, category=ticket.category)

    except Exception as e:
        logger.error("support_triage_failed",
                     tenant_id=tenant_id, ticket_id=ticket_id, error=str(e))
        update_run_status(session, run_id, "failed",
                          error_message=str(e)[:1000],
                          completed_at=datetime.utcnow(),
                          duration_seconds=round(time.time() - start_time, 3))
        create_audit_entry(
            session, tenant_id, run_id,
            action="error", workflow="support_triage", step="pipeline",
            reason_code="pipeline_error",
            output_summary=str(e)[:500],
        )
        raise
    finally:
        session.close()


async def _classify_ticket(router, ticket: Ticket) -> dict:
    """Classify ticket using 7B model."""
    prompt = f"""Analyze this support ticket and classify it. Return JSON only.

Subject: {ticket.subject or 'N/A'}
From: {ticket.from_email or 'Unknown'}
Body: {ticket.body[:2000]}

Return this exact JSON structure:
{{
  "category": "<billing|technical|account|feature_request|bug_report|general>",
  "priority": "<low|medium|high|critical>",
  "sentiment": "<positive|neutral|negative>",
  "suggested_team": "<billing|engineering|support|sales|management>",
  "needs_human": <true|false>,
  "confidence": <0.0 to 1.0>
}}
</output>"""

    return await router.route(prompt, task_type="classify")


async def _draft_reply(router, ticket: Ticket, tenant) -> dict:
    """Generate draft reply using Claude."""
    system_prompt = """You are a professional customer support assistant. Generate helpful, empathetic replies.
Be concise but thorough. If information is missing, note what questions to ask.
Never make promises about timelines or features without authorization.
Always maintain a professional and friendly tone."""

    prompt = f"""Draft a reply for this support ticket.

Subject: {ticket.subject or 'N/A'}
From: {ticket.from_name or ticket.from_email or 'Customer'}
Category: {ticket.category or 'General'}
Priority: {ticket.priority or 'Medium'}
Sentiment: {ticket.sentiment or 'Neutral'}

Customer Message:
{ticket.body[:3000]}

Provide your response in this JSON format:
{{
  "draft_reply": "<the email reply to send to the customer>",
  "internal_notes": "<notes for the support team>",
  "recommended_action": "<next step: respond|escalate|close|follow_up>",
  "follow_up_questions": ["<question 1 if info is missing>", "<question 2>"]
}}"""

    return await router.route(prompt, task_type="draft_reply", system_prompt=system_prompt, max_tokens=1024)


def _apply_classification(session, ticket: Ticket, result: dict):
    """Parse classification result and update ticket."""
    try:
        content = result["content"]
        # Try to parse JSON from the response
        if "{" in content:
            json_str = content[content.index("{"):content.rindex("}") + 1]
            data = json.loads(json_str)
            ticket.category = data.get("category", "general")
            ticket.priority = data.get("priority", "medium")
            ticket.sentiment = data.get("sentiment", "neutral")
            ticket.suggested_team = data.get("suggested_team", "support")
            ticket.needs_human = data.get("needs_human", True)
            ticket.classification_confidence = data.get("confidence", 0.5)
            ticket.classification_raw = data
        else:
            ticket.category = "general"
            ticket.priority = "medium"
            ticket.needs_human = True
            ticket.classification_confidence = 0.0
    except (json.JSONDecodeError, ValueError):
        ticket.category = "general"
        ticket.priority = "medium"
        ticket.needs_human = True
        ticket.classification_confidence = 0.0
    session.commit()


def _apply_draft(session, ticket: Ticket, result: dict):
    """Parse draft result and update ticket."""
    try:
        content = result["content"]
        if "{" in content:
            json_str = content[content.index("{"):content.rindex("}") + 1]
            data = json.loads(json_str)
            ticket.draft_reply = data.get("draft_reply", content)
            ticket.internal_notes = data.get("internal_notes", "")
            ticket.recommended_action = data.get("recommended_action", "respond")
            ticket.follow_up_questions = data.get("follow_up_questions", [])
        else:
            ticket.draft_reply = content
            ticket.recommended_action = "respond"
    except (json.JSONDecodeError, ValueError):
        ticket.draft_reply = result["content"]
        ticket.recommended_action = "respond"
    session.commit()


def _apply_routing_rules(session, ticket: Ticket, tenant):
    """Apply YAML-configured routing rules."""
    config = {}
    if tenant.support_config_yaml:
        try:
            config = yaml.safe_load(tenant.support_config_yaml) or {}
        except yaml.YAMLError:
            pass

    routing = config.get("routing", {})

    # Team assignment
    team_map = routing.get("team_map", {})
    if ticket.category and ticket.category in team_map:
        ticket.assigned_team = team_map[ticket.category]
    else:
        ticket.assigned_team = ticket.suggested_team or "support"

    # Tags from config
    auto_tags = routing.get("auto_tags", {})
    tags = []
    if ticket.priority in auto_tags.get("priority", {}):
        tags.extend(auto_tags["priority"][ticket.priority])
    if ticket.sentiment in auto_tags.get("sentiment", {}):
        tags.extend(auto_tags["sentiment"][ticket.sentiment])
    ticket.tags = tags

    # SLA timer
    sla_hours = routing.get("sla_hours", {})
    hours = sla_hours.get(ticket.priority or "medium", 24)
    ticket.sla_due_at = datetime.utcnow() + timedelta(hours=hours)

    # Escalation rules
    escalate_threshold = routing.get("escalate_confidence_below", 0.5)
    if (ticket.classification_confidence or 0) < escalate_threshold:
        ticket.needs_human = True
        ticket.status = "escalated"
        tags.append("auto-escalated")
        ticket.tags = tags

    session.commit()


async def _notify_slack(tenant, ticket: Ticket):
    """Send Slack notification for new ticket."""
    from app.services.notifications import send_slack_notification, format_support_notification
    text, blocks = format_support_notification({
        "subject": ticket.subject,
        "from_email": ticket.from_email,
        "priority": ticket.priority,
        "category": ticket.category,
        "sentiment": ticket.sentiment,
        "body": ticket.body,
    })
    await send_slack_notification(tenant.slack_webhook_url, text, blocks=blocks)
