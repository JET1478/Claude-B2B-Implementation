"""Budget enforcement service - per-tenant token/cost/rate limits + circuit breakers."""

import time
from datetime import datetime, date

import redis as redis_lib
import structlog

from app.config import settings

logger = structlog.get_logger()

_redis: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    global _redis
    if _redis is None:
        _redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis


class BudgetExceededError(Exception):
    def __init__(self, reason: str, limit_type: str):
        self.reason = reason
        self.limit_type = limit_type
        super().__init__(reason)


class CircuitOpenError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class BudgetEnforcer:
    """Enforces per-tenant rate limits, daily quotas, and circuit breakers."""

    # Circuit breaker settings
    FAILURE_THRESHOLD = 5  # failures before circuit opens
    CIRCUIT_TIMEOUT = 300  # seconds before half-open retry

    def __init__(self, tenant_id: str, max_runs_per_day: int, max_tokens_per_day: int, max_items_per_minute: int):
        self.tenant_id = tenant_id
        self.max_runs_per_day = max_runs_per_day
        self.max_tokens_per_day = max_tokens_per_day
        self.max_items_per_minute = max_items_per_minute
        self.r = get_redis()

    def _day_key(self, metric: str) -> str:
        today = date.today().isoformat()
        return f"budget:{self.tenant_id}:{metric}:{today}"

    def _minute_key(self) -> str:
        minute = datetime.utcnow().strftime("%Y%m%d%H%M")
        return f"rate:{self.tenant_id}:items:{minute}"

    def _circuit_key(self) -> str:
        return f"circuit:{self.tenant_id}"

    def check_circuit_breaker(self) -> None:
        """Raise if circuit is open."""
        key = self._circuit_key()
        data = self.r.hgetall(key)
        if not data:
            return
        state = data.get("state", "closed")
        if state == "open":
            opened_at = float(data.get("opened_at", 0))
            if time.time() - opened_at > self.CIRCUIT_TIMEOUT:
                # Half-open: allow one attempt
                self.r.hset(key, "state", "half-open")
                return
            raise CircuitOpenError(
                f"Circuit breaker open for tenant {self.tenant_id}. "
                f"Too many failures. Retry after {self.CIRCUIT_TIMEOUT}s."
            )

    def record_failure(self) -> None:
        """Record a failure; open circuit if threshold exceeded."""
        key = self._circuit_key()
        failures = self.r.hincrby(key, "failures", 1)
        self.r.expire(key, self.CIRCUIT_TIMEOUT * 2)
        if failures >= self.FAILURE_THRESHOLD:
            self.r.hset(key, mapping={"state": "open", "opened_at": str(time.time())})
            logger.warning("circuit_breaker_opened", tenant_id=self.tenant_id, failures=failures)

    def record_success(self) -> None:
        """Reset circuit breaker on success."""
        key = self._circuit_key()
        self.r.delete(key)

    def check_rate_limit(self) -> None:
        """Check items-per-minute rate limit."""
        key = self._minute_key()
        current = int(self.r.get(key) or 0)
        if current >= self.max_items_per_minute:
            raise BudgetExceededError(
                f"Rate limit exceeded: {current}/{self.max_items_per_minute} items this minute",
                "rate_limit"
            )

    def increment_rate(self) -> None:
        key = self._minute_key()
        pipe = self.r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 120)  # expire after 2 minutes
        pipe.execute()

    def check_daily_runs(self) -> None:
        """Check daily run quota."""
        key = self._day_key("runs")
        current = int(self.r.get(key) or 0)
        if current >= self.max_runs_per_day:
            raise BudgetExceededError(
                f"Daily run limit exceeded: {current}/{self.max_runs_per_day}",
                "daily_runs"
            )

    def increment_daily_runs(self) -> None:
        key = self._day_key("runs")
        pipe = self.r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400 * 2)  # expire after 2 days
        pipe.execute()

    def check_daily_tokens(self, estimated_tokens: int = 0) -> None:
        """Check daily token quota."""
        key = self._day_key("tokens")
        current = int(self.r.get(key) or 0)
        if current + estimated_tokens > self.max_tokens_per_day:
            raise BudgetExceededError(
                f"Daily token limit would be exceeded: {current}+{estimated_tokens}/{self.max_tokens_per_day}",
                "daily_tokens"
            )

    def add_daily_tokens(self, tokens: int) -> None:
        key = self._day_key("tokens")
        pipe = self.r.pipeline()
        pipe.incrby(key, tokens)
        pipe.expire(key, 86400 * 2)
        pipe.execute()

    def check_all(self, estimated_tokens: int = 0) -> None:
        """Run all budget checks. Raises on any violation."""
        self.check_circuit_breaker()
        self.check_rate_limit()
        self.check_daily_runs()
        self.check_daily_tokens(estimated_tokens)

    def get_usage(self) -> dict:
        """Get current usage stats for this tenant."""
        return {
            "runs_today": int(self.r.get(self._day_key("runs")) or 0),
            "tokens_today": int(self.r.get(self._day_key("tokens")) or 0),
            "max_runs_per_day": self.max_runs_per_day,
            "max_tokens_per_day": self.max_tokens_per_day,
        }


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate cost in USD for a model call."""
    # Pricing per 1M tokens (approximate)
    pricing = {
        "local_7b": {"input": 0.0, "output": 0.0},  # Self-hosted, no per-token cost
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    }
    rates = pricing.get(model, pricing["claude-sonnet-4-20250514"])
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return round(cost, 6)
