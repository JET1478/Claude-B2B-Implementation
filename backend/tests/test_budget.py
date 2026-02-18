"""Tests for budget enforcement service."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.budget import BudgetEnforcer, BudgetExceededError, CircuitOpenError, estimate_cost


class TestBudgetEnforcer:
    """Test budget enforcement with mocked Redis."""

    def setup_method(self):
        self.mock_redis = MagicMock()
        self.enforcer = BudgetEnforcer(
            tenant_id="test-tenant",
            max_runs_per_day=100,
            max_tokens_per_day=50000,
            max_items_per_minute=5,
        )
        self.enforcer.r = self.mock_redis

    def test_check_rate_limit_under(self):
        self.mock_redis.get.return_value = "3"
        self.enforcer.check_rate_limit()  # Should not raise

    def test_check_rate_limit_exceeded(self):
        self.mock_redis.get.return_value = "5"
        with pytest.raises(BudgetExceededError) as exc:
            self.enforcer.check_rate_limit()
        assert "rate_limit" == exc.value.limit_type

    def test_check_daily_runs_under(self):
        self.mock_redis.get.return_value = "50"
        self.enforcer.check_daily_runs()  # Should not raise

    def test_check_daily_runs_exceeded(self):
        self.mock_redis.get.return_value = "100"
        with pytest.raises(BudgetExceededError) as exc:
            self.enforcer.check_daily_runs()
        assert "daily_runs" == exc.value.limit_type

    def test_check_daily_tokens_under(self):
        self.mock_redis.get.return_value = "10000"
        self.enforcer.check_daily_tokens(estimated_tokens=1000)  # Should not raise

    def test_check_daily_tokens_exceeded(self):
        self.mock_redis.get.return_value = "49500"
        with pytest.raises(BudgetExceededError) as exc:
            self.enforcer.check_daily_tokens(estimated_tokens=1000)
        assert "daily_tokens" == exc.value.limit_type

    def test_circuit_breaker_closed(self):
        self.mock_redis.hgetall.return_value = {}
        self.enforcer.check_circuit_breaker()  # Should not raise

    def test_circuit_breaker_open(self):
        import time
        self.mock_redis.hgetall.return_value = {
            "state": "open",
            "opened_at": str(time.time()),
            "failures": "5",
        }
        with pytest.raises(CircuitOpenError):
            self.enforcer.check_circuit_breaker()

    def test_circuit_breaker_half_open_after_timeout(self):
        import time
        self.mock_redis.hgetall.return_value = {
            "state": "open",
            "opened_at": str(time.time() - 400),  # Past timeout
            "failures": "5",
        }
        self.enforcer.check_circuit_breaker()  # Should not raise (half-open)

    def test_record_failure_opens_circuit(self):
        self.mock_redis.hincrby.return_value = 5
        self.enforcer.record_failure()
        self.mock_redis.hset.assert_called_once()

    def test_record_success_resets_circuit(self):
        self.enforcer.record_success()
        self.mock_redis.delete.assert_called_once()

    def test_increment_rate(self):
        pipe = MagicMock()
        self.mock_redis.pipeline.return_value = pipe
        self.enforcer.increment_rate()
        pipe.incr.assert_called_once()
        pipe.expire.assert_called_once()
        pipe.execute.assert_called_once()

    def test_get_usage(self):
        self.mock_redis.get.side_effect = lambda k: "25" if "runs" in k else "12000"
        usage = self.enforcer.get_usage()
        assert usage["runs_today"] == 25
        assert usage["tokens_today"] == 12000
        assert usage["max_runs_per_day"] == 100


class TestCostEstimation:
    def test_local_model_free(self):
        cost = estimate_cost(1000, 500, "local_7b")
        assert cost == 0.0

    def test_claude_sonnet_cost(self):
        cost = estimate_cost(1000, 500, "claude-sonnet-4-20250514")
        # input: 1000 * 3.0 / 1M = 0.003, output: 500 * 15.0 / 1M = 0.0075
        assert cost == pytest.approx(0.0105, abs=0.001)

    def test_claude_haiku_cost(self):
        cost = estimate_cost(1000, 500, "claude-haiku-4-5-20251001")
        # input: 1000 * 0.80 / 1M = 0.0008, output: 500 * 4.0 / 1M = 0.002
        assert cost == pytest.approx(0.0028, abs=0.001)
