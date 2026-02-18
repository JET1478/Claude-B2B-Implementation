"""Lead qualification workflow worker task.

Pipeline:
1. Normalize lead payload
2. 7B extract: company size, intent, urgency, industry, spam score
3. Claude qualify: summary + follow-up questions + next step
4. CRM adapter: create/update contact + deal
5. Generate email draft(s)
6. Notify via Slack
"""

import json
import uuid
import time
import yaml
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.lead import Lead
from app.models.run import Run
from app.workers.base import (
    get_sync_session, load_tenant, update_run_status,
    create_audit_entry, create_model_router, run_async, logger,
)

import structlog

logger = structlog.get_logger()


def process_lead(tenant_id: str, lead_id: str, run_id: str):
    """Main entry point for lead qualification worker task."""
    session = get_sync_session()
    start_time = time.time()

    try:
        update_run_status(session, run_id, "running", started_at=datetime.utcnow(), current_step="init")

        tenant = load_tenant(session, tenant_id)
        result = session.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
        lead = result.scalar_one_or_none()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        router = create_model_router(tenant)
        steps_completed = []

        # --- Step 1: Extract with 7B ---
        update_run_status(session, run_id, "running", current_step="extract")
        lead.status = "processing"
        session.commit()

        extract_result = run_async(_extract_lead_info(router, lead))
        _apply_extraction(session, lead, extract_result)
        steps_completed.append({"step": "extract", "model": extract_result["model"], "tokens": extract_result["tokens"]})

        create_audit_entry(
            session, tenant_id, run_id,
            action="lead_extracted", workflow="lead_qualify", step="extract",
            model_used=extract_result["model"],
            prompt_template_id="lead_extract_v1",
            input_tokens=extract_result.get("input_tokens"),
            output_tokens=extract_result.get("output_tokens"),
            estimated_cost_usd=extract_result["cost"],
            input_summary=f"Lead: {lead.name}, Company: {lead.company}",
            output_summary=f"Intent: {lead.intent_classification}, Urgency: {lead.urgency}, Spam: {lead.spam_score}",
        )

        # Check spam score - skip rest of pipeline if too spammy
        if lead.spam_score and lead.spam_score > 0.8:
            lead.status = "disqualified"
            session.commit()
            create_audit_entry(
                session, tenant_id, run_id,
                action="lead_disqualified", workflow="lead_qualify", step="spam_check",
                reason_code="high_spam_score",
                extra_data={"spam_score": lead.spam_score},
            )
            update_run_status(session, run_id, "completed",
                              completed_at=datetime.utcnow(),
                              duration_seconds=round(time.time() - start_time, 3),
                              steps_completed=steps_completed,
                              lead_id=uuid.UUID(lead_id))
            return

        # --- Step 2: Qualify with Claude ---
        update_run_status(session, run_id, "running", current_step="qualify")

        qualify_result = run_async(_qualify_lead(router, lead, tenant))
        _apply_qualification(session, lead, qualify_result)
        steps_completed.append({"step": "qualify", "model": qualify_result["model"], "tokens": qualify_result["tokens"]})

        create_audit_entry(
            session, tenant_id, run_id,
            action="lead_qualified", workflow="lead_qualify", step="qualify",
            model_used=qualify_result["model"],
            prompt_template_id="lead_qualify_v1",
            input_tokens=qualify_result.get("input_tokens"),
            output_tokens=qualify_result.get("output_tokens"),
            estimated_cost_usd=qualify_result["cost"],
            input_summary=f"Lead: {lead.name}",
            output_summary=f"Score: {lead.score}, Next: {lead.suggested_next_step}",
        )

        # --- Step 3: CRM update ---
        update_run_status(session, run_id, "running", current_step="crm")
        crm_result = run_async(_update_crm(tenant, lead))
        if crm_result:
            steps_completed.append({"step": "crm", "contact_id": lead.crm_contact_id, "deal_id": lead.crm_deal_id})
            create_audit_entry(
                session, tenant_id, run_id,
                action="crm_updated", workflow="lead_qualify", step="crm",
                reason_code="hubspot_sync",
                extra_data={"contact_id": lead.crm_contact_id, "deal_id": lead.crm_deal_id},
            )
            session.commit()

        # --- Step 4: Generate email drafts ---
        update_run_status(session, run_id, "running", current_step="email_drafts")
        draft_result = run_async(_generate_email_drafts(router, lead, tenant))
        _apply_email_drafts(session, lead, draft_result)
        steps_completed.append({"step": "email_drafts", "model": draft_result["model"], "tokens": draft_result["tokens"]})

        # --- Step 5: Notify ---
        update_run_status(session, run_id, "running", current_step="notify")
        if tenant.slack_webhook_url:
            run_async(_notify_slack(tenant, lead))
        steps_completed.append({"step": "notify"})

        # --- Finalize ---
        lead.status = "qualified"
        lead.follow_up_scheduled_at = datetime.utcnow() + timedelta(hours=24)
        session.commit()

        duration = round(time.time() - start_time, 3)
        update_run_status(
            session, run_id, "completed",
            completed_at=datetime.utcnow(),
            duration_seconds=duration,
            steps_completed=steps_completed,
            current_step="done",
            lead_id=uuid.UUID(lead_id),
        )

        logger.info("lead_qualification_completed",
                     tenant_id=tenant_id, lead_id=lead_id, duration=duration, score=lead.score)

    except Exception as e:
        logger.error("lead_qualification_failed",
                     tenant_id=tenant_id, lead_id=lead_id, error=str(e))
        update_run_status(session, run_id, "failed",
                          error_message=str(e)[:1000],
                          completed_at=datetime.utcnow(),
                          duration_seconds=round(time.time() - start_time, 3))
        create_audit_entry(
            session, tenant_id, run_id,
            action="error", workflow="lead_qualify", step="pipeline",
            reason_code="pipeline_error",
            output_summary=str(e)[:500],
        )
        raise
    finally:
        session.close()


async def _extract_lead_info(router, lead: Lead) -> dict:
    """Extract structured info from lead using 7B model."""
    prompt = f"""Analyze this sales lead and extract structured information. Return JSON only.

Name: {lead.name}
Email: {lead.email}
Company: {lead.company or 'N/A'}
Phone: {lead.phone or 'N/A'}
Message: {lead.message or 'N/A'}
Source: {lead.source}

Return this exact JSON structure:
{{
  "company_size_cue": "<startup|smb|mid|enterprise|unknown>",
  "intent_classification": "<purchase|demo|pricing|partnership|support|general|spam>",
  "urgency": "<low|medium|high>",
  "industry": "<technology|finance|healthcare|retail|manufacturing|other>",
  "spam_score": <0.0 to 1.0, where 1.0 is definitely spam>,
  "confidence": <0.0 to 1.0>
}}
</output>"""

    return await router.route(prompt, task_type="extract")


async def _qualify_lead(router, lead: Lead, tenant) -> dict:
    """Qualify lead using Claude."""
    system_prompt = """You are a B2B sales qualification assistant. Analyze leads objectively.
Score leads 0-100 based on: company fit, intent clarity, urgency, and engagement potential.
Be specific in follow-up questions. Suggest concrete next steps."""

    prompt = f"""Qualify this sales lead.

Name: {lead.name}
Email: {lead.email}
Company: {lead.company or 'N/A'}
Message: {lead.message or 'N/A'}
Company Size: {lead.company_size_cue or 'Unknown'}
Intent: {lead.intent_classification or 'Unknown'}
Urgency: {lead.urgency or 'Unknown'}
Industry: {lead.industry or 'Unknown'}

Provide your response in this JSON format:
{{
  "qualification_summary": "<2-3 sentence summary of lead quality and potential>",
  "score": <0-100 lead score>,
  "follow_up_questions": ["<specific question 1>", "<specific question 2>", "<specific question 3>"],
  "suggested_next_step": "<call|demo|email|disqualify>",
  "reasoning": "<why this score and next step>"
}}"""

    return await router.route(prompt, task_type="qualify_lead", system_prompt=system_prompt, max_tokens=768)


async def _update_crm(tenant, lead: Lead) -> bool:
    """Create/update CRM contact and deal."""
    from app.adapters.crm import CRMAdapter

    crm = CRMAdapter(
        hubspot_key_encrypted=tenant.hubspot_api_key_encrypted,
    )

    if not crm.is_configured:
        return False

    # Create contact
    contact_result = await crm.create_contact({
        "name": lead.name,
        "email": lead.email,
        "company": lead.company,
        "phone": lead.phone,
    })

    if contact_result:
        lead.crm_contact_id = contact_result.get("id")

        # Create deal
        deal_result = await crm.create_deal({
            "deal_name": f"Lead: {lead.company or lead.name}",
            "summary": lead.qualification_summary or "",
            "stage": "qualifiedtobuy" if (lead.score or 0) >= 50 else "appointmentscheduled",
        }, contact_id=lead.crm_contact_id)

        if deal_result:
            lead.crm_deal_id = deal_result.get("id")

    return True


async def _generate_email_drafts(router, lead: Lead, tenant) -> dict:
    """Generate follow-up email drafts using Claude."""
    prompt = f"""Generate 2 follow-up email drafts for this qualified lead.

Lead: {lead.name} ({lead.email})
Company: {lead.company or 'N/A'}
Interest: {lead.intent_classification or 'General'}
Qualification: {lead.qualification_summary or 'N/A'}
Suggested Next Step: {lead.suggested_next_step or 'Email'}
Follow-up Questions: {json.dumps(lead.follow_up_questions or [])}

Generate 2 emails:
1. Initial outreach (warm, professional, references their inquiry)
2. Follow-up (sent 3 days later if no reply, shorter, adds value)

Return JSON:
{{
  "emails": [
    {{"subject": "<subject 1>", "body": "<html body 1>"}},
    {{"subject": "<subject 2>", "body": "<html body 2>"}}
  ]
}}"""

    return await router.route(prompt, task_type="draft_reply", max_tokens=1024)


def _apply_extraction(session, lead: Lead, result: dict):
    """Parse extraction result and update lead."""
    try:
        content = result["content"]
        if "{" in content:
            json_str = content[content.index("{"):content.rindex("}") + 1]
            data = json.loads(json_str)
            lead.company_size_cue = data.get("company_size_cue", "unknown")
            lead.intent_classification = data.get("intent_classification", "general")
            lead.urgency = data.get("urgency", "medium")
            lead.industry = data.get("industry", "other")
            lead.spam_score = data.get("spam_score", 0.0)
            lead.extraction_confidence = data.get("confidence", 0.5)
            lead.extraction_raw = data
        else:
            lead.company_size_cue = "unknown"
            lead.intent_classification = "general"
            lead.urgency = "medium"
            lead.spam_score = 0.0
            lead.extraction_confidence = 0.0
    except (json.JSONDecodeError, ValueError):
        lead.company_size_cue = "unknown"
        lead.intent_classification = "general"
        lead.urgency = "medium"
        lead.spam_score = 0.0
        lead.extraction_confidence = 0.0
    session.commit()


def _apply_qualification(session, lead: Lead, result: dict):
    """Parse qualification result and update lead."""
    try:
        content = result["content"]
        if "{" in content:
            json_str = content[content.index("{"):content.rindex("}") + 1]
            data = json.loads(json_str)
            lead.qualification_summary = data.get("qualification_summary", "")
            lead.score = data.get("score", 50)
            lead.follow_up_questions = data.get("follow_up_questions", [])
            lead.suggested_next_step = data.get("suggested_next_step", "email")
        else:
            lead.qualification_summary = content
            lead.score = 50
            lead.suggested_next_step = "email"
    except (json.JSONDecodeError, ValueError):
        lead.qualification_summary = result["content"]
        lead.score = 50
        lead.suggested_next_step = "email"
    session.commit()


def _apply_email_drafts(session, lead: Lead, result: dict):
    """Parse email draft result and update lead."""
    try:
        content = result["content"]
        if "{" in content:
            json_str = content[content.index("{"):content.rindex("}") + 1]
            data = json.loads(json_str)
            lead.email_drafts = data.get("emails", [])
        else:
            lead.email_drafts = [{"subject": "Follow-up", "body": content}]
    except (json.JSONDecodeError, ValueError):
        lead.email_drafts = [{"subject": "Follow-up", "body": result["content"]}]
    session.commit()


async def _notify_slack(tenant, lead: Lead):
    """Send Slack notification for new qualified lead."""
    from app.services.notifications import send_slack_notification, format_lead_notification
    text, blocks = format_lead_notification({
        "name": lead.name,
        "company": lead.company,
        "email": lead.email,
        "score": lead.score,
        "message": lead.message,
    })
    await send_slack_notification(tenant.slack_webhook_url, text, blocks=blocks)
