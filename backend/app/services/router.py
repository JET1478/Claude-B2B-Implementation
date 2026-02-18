"""Model router service - routes tasks to local 7B or Claude API."""

import json
import time
from pathlib import Path
from typing import Optional

import httpx
import anthropic
import structlog

from app.config import settings
from app.services.budget import BudgetEnforcer, estimate_cost
from app.services.crypto import decrypt_value

logger = structlog.get_logger()

# Load prompt templates from disk
# Check multiple paths: local dev path and Docker mount path
_PROMPTS_CANDIDATES = [
    Path(__file__).parent.parent.parent.parent / "prompts",  # Local dev
    Path("/prompts"),  # Docker mount
]
PROMPTS_DIR = next((p for p in _PROMPTS_CANDIDATES if p.exists()), _PROMPTS_CANDIDATES[0])


def load_prompt_template(template_id: str) -> str:
    """Load a prompt template by ID (filename without extension)."""
    path = PROMPTS_DIR / f"{template_id}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_id} (searched {PROMPTS_DIR})")
    return path.read_text(encoding="utf-8")


class ModelRouter:
    """Routes inference requests to local 7B model or Claude API based on task type."""

    # Tasks suitable for local 7B model
    LOCAL_TASKS = {"classify", "extract", "summarize", "spam_check"}
    # Tasks requiring Claude
    CLAUDE_TASKS = {"draft_reply", "qualify_lead", "generate_questions", "complex_reasoning"}

    def __init__(
        self,
        tenant_id: str,
        anthropic_key_encrypted: Optional[str] = None,
        budget: Optional[BudgetEnforcer] = None,
    ):
        self.tenant_id = tenant_id
        self.budget = budget
        self._anthropic_key = None

        # Resolve API key: tenant BYOK > platform key
        if anthropic_key_encrypted:
            try:
                self._anthropic_key = decrypt_value(anthropic_key_encrypted)
            except Exception:
                logger.error("failed_to_decrypt_api_key", tenant_id=tenant_id)
        if not self._anthropic_key and settings.platform_key_mode:
            self._anthropic_key = settings.platform_anthropic_key

    async def call_local_model(self, prompt: str, task_type: str) -> dict:
        """Call the local 7B model (llama.cpp server)."""
        if not settings.local_model_enabled:
            logger.info("local_model_disabled_using_fallback", task_type=task_type)
            return await self._local_model_fallback(prompt, task_type)

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    settings.local_model_url,
                    json={
                        "prompt": prompt,
                        "n_predict": 512,
                        "temperature": 0.1,
                        "stop": ["</output>", "\n\n---"],
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            content = data.get("content", data.get("text", ""))
            tokens_used = data.get("tokens_predicted", len(content.split()))

            if self.budget:
                self.budget.add_daily_tokens(tokens_used)

            return {
                "content": content,
                "model": "local_7b",
                "tokens": tokens_used,
                "cost": 0.0,
                "duration": round(time.time() - start, 3),
            }
        except Exception as e:
            logger.warning("local_model_call_failed", error=str(e), task_type=task_type)
            return await self._local_model_fallback(prompt, task_type)

    async def _local_model_fallback(self, prompt: str, task_type: str) -> dict:
        """Fallback when local model is unavailable - use Claude with minimal tokens."""
        if self._anthropic_key:
            return await self.call_claude(
                prompt,
                task_type=task_type,
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
            )
        # Ultimate fallback: return a safe default
        logger.warning("no_model_available_returning_default", task_type=task_type)
        return {
            "content": json.dumps({
                "category": "general",
                "priority": "medium",
                "sentiment": "neutral",
                "suggested_team": "general",
                "needs_human": True,
                "confidence": 0.0,
            }),
            "model": "fallback_default",
            "tokens": 0,
            "cost": 0.0,
            "duration": 0.0,
        }

    async def call_claude(
        self,
        prompt: str,
        task_type: str,
        system_prompt: str = "",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
    ) -> dict:
        """Call Claude API."""
        if not self._anthropic_key:
            raise ValueError(f"No Anthropic API key available for tenant {self.tenant_id}")

        # Estimate tokens and check budget
        estimated_input = len(prompt.split()) * 1.3  # rough estimate
        if self.budget:
            self.budget.check_daily_tokens(int(estimated_input + max_tokens))

        start = time.time()
        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)

        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = await client.messages.create(**kwargs)

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = estimate_cost(input_tokens, output_tokens, model)
            content = response.content[0].text

            if self.budget:
                self.budget.add_daily_tokens(input_tokens + output_tokens)
                self.budget.record_success()

            return {
                "content": content,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tokens": input_tokens + output_tokens,
                "cost": cost,
                "duration": round(time.time() - start, 3),
            }
        except Exception as e:
            if self.budget:
                self.budget.record_failure()
            raise

    async def route(
        self,
        prompt: str,
        task_type: str,
        template_id: Optional[str] = None,
        template_vars: Optional[dict] = None,
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> dict:
        """Route a request to the appropriate model based on task type.

        Returns dict with: content, model, tokens, cost, duration
        """
        # Load and format prompt template if specified
        if template_id:
            template = load_prompt_template(template_id)
            prompt = template.format(**(template_vars or {}))

        # Check budget before any call
        if self.budget:
            self.budget.check_all(estimated_tokens=max_tokens)

        # Route to appropriate model
        if task_type in self.LOCAL_TASKS:
            result = await self.call_local_model(prompt, task_type)
        elif task_type in self.CLAUDE_TASKS:
            result = await self.call_claude(prompt, task_type, system_prompt=system_prompt, max_tokens=max_tokens)
        else:
            # Default to Claude for unknown task types
            logger.info("unknown_task_type_routing_to_claude", task_type=task_type)
            result = await self.call_claude(prompt, task_type, system_prompt=system_prompt, max_tokens=max_tokens)

        result["task_type"] = task_type
        result["template_id"] = template_id
        return result
