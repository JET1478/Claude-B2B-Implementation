"""Tests for model router service."""

import pytest
from pathlib import Path


class TestPromptTemplates:
    """Verify prompt templates exist and are valid."""

    PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

    def test_support_classify_template_exists(self):
        path = self.PROMPTS_DIR / "support_classify_v1.txt"
        assert path.exists()
        content = path.read_text()
        assert "category" in content
        assert "priority" in content
        assert "sentiment" in content

    def test_support_draft_template_exists(self):
        path = self.PROMPTS_DIR / "support_draft_v1.txt"
        assert path.exists()
        content = path.read_text()
        assert "draft_reply" in content
        assert "recommended_action" in content

    def test_lead_extract_template_exists(self):
        path = self.PROMPTS_DIR / "lead_extract_v1.txt"
        assert path.exists()
        content = path.read_text()
        assert "company_size_cue" in content
        assert "spam_score" in content

    def test_lead_qualify_template_exists(self):
        path = self.PROMPTS_DIR / "lead_qualify_v1.txt"
        assert path.exists()
        content = path.read_text()
        assert "qualification_summary" in content
        assert "follow_up_questions" in content

    def test_templates_have_format_placeholders(self):
        """All templates should have {variable} placeholders."""
        for path in self.PROMPTS_DIR.glob("*.txt"):
            content = path.read_text()
            assert "{" in content, f"Template {path.name} has no placeholders"


class TestModelRouterTaskRouting:
    """Test task routing logic (without actual API calls)."""

    def test_local_tasks(self):
        from app.services.router import ModelRouter
        local_tasks = ModelRouter.LOCAL_TASKS
        assert "classify" in local_tasks
        assert "extract" in local_tasks
        assert "summarize" in local_tasks

    def test_claude_tasks(self):
        from app.services.router import ModelRouter
        claude_tasks = ModelRouter.CLAUDE_TASKS
        assert "draft_reply" in claude_tasks
        assert "qualify_lead" in claude_tasks
        assert "generate_questions" in claude_tasks

    def test_no_overlap(self):
        from app.services.router import ModelRouter
        overlap = ModelRouter.LOCAL_TASKS & ModelRouter.CLAUDE_TASKS
        assert len(overlap) == 0, f"Tasks appear in both local and claude: {overlap}"
