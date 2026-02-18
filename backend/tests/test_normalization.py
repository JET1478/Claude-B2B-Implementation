"""Tests for payload normalization and parsing."""

import json
import pytest
from app.schemas.webhook import SupportWebhookPayload, LeadWebhookPayload


class TestSupportWebhookNormalization:
    def test_minimal_payload(self):
        payload = SupportWebhookPayload(body="Help me please")
        assert payload.body == "Help me please"
        assert payload.source == "webhook"
        assert payload.subject is None
        assert payload.from_email is None

    def test_full_payload(self):
        payload = SupportWebhookPayload(
            subject="Account issue",
            body="I can't login to my account",
            from_email="user@example.com",
            from_name="Test User",
            external_id="ZEN-123",
            source="zendesk",
            attachments=[{"filename": "screenshot.png", "size": 1024}],
        )
        assert payload.subject == "Account issue"
        assert payload.from_email == "user@example.com"
        assert payload.external_id == "ZEN-123"
        assert len(payload.attachments) == 1

    def test_body_required(self):
        with pytest.raises(Exception):
            SupportWebhookPayload(subject="Test")

    def test_body_max_length(self):
        long_body = "x" * 50001
        with pytest.raises(Exception):
            SupportWebhookPayload(body=long_body)

    def test_body_min_length(self):
        with pytest.raises(Exception):
            SupportWebhookPayload(body="")


class TestLeadWebhookNormalization:
    def test_minimal_payload(self):
        payload = LeadWebhookPayload(name="John Doe", email="john@example.com")
        assert payload.name == "John Doe"
        assert payload.email == "john@example.com"
        assert payload.source == "webhook"
        assert payload.company is None

    def test_full_payload(self):
        payload = LeadWebhookPayload(
            name="Jane Smith",
            email="jane@company.com",
            company="Acme Corp",
            phone="+1-555-0123",
            message="Interested in your product",
            source="website_form",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="q4-campaign",
        )
        assert payload.company == "Acme Corp"
        assert payload.utm_source == "google"

    def test_name_required(self):
        with pytest.raises(Exception):
            LeadWebhookPayload(email="test@test.com")

    def test_email_required(self):
        with pytest.raises(Exception):
            LeadWebhookPayload(name="Test")


class TestClassificationParsing:
    """Test JSON parsing logic used in workers."""

    def test_parse_classification_json(self):
        content = '''Here is the classification:
{"category": "technical", "priority": "high", "sentiment": "negative", "suggested_team": "engineering", "needs_human": false, "confidence": 0.87}'''

        json_str = content[content.index("{"):content.rindex("}") + 1]
        data = json.loads(json_str)
        assert data["category"] == "technical"
        assert data["priority"] == "high"
        assert data["confidence"] == 0.87
        assert data["needs_human"] is False

    def test_parse_lead_extraction_json(self):
        content = '''{"company_size_cue": "enterprise", "intent_classification": "demo", "urgency": "high", "industry": "technology", "spam_score": 0.05, "confidence": 0.92}'''

        data = json.loads(content)
        assert data["company_size_cue"] == "enterprise"
        assert data["spam_score"] == 0.05
        assert data["urgency"] == "high"
