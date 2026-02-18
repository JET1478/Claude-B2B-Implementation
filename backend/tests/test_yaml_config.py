"""Tests for YAML configuration validation."""

import yaml
import pytest
from pathlib import Path


SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"


class TestSupportConfig:
    def test_load_support_yaml(self):
        path = SAMPLES_DIR / "support.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)
        assert "routing" in config
        assert "autosend" in config

    def test_support_routing_structure(self):
        path = SAMPLES_DIR / "support.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)

        routing = config["routing"]
        assert "team_map" in routing
        assert "sla_hours" in routing
        assert "escalate_confidence_below" in routing

        # Verify team map has expected categories
        team_map = routing["team_map"]
        assert "billing" in team_map
        assert "technical" in team_map

    def test_support_autosend_defaults(self):
        path = SAMPLES_DIR / "support.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)

        autosend = config["autosend"]
        assert autosend["enabled"] is False  # MUST default to false
        assert autosend["confidence_threshold"] >= 0.85

    def test_support_sla_hours_valid(self):
        path = SAMPLES_DIR / "support.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)

        sla = config["routing"]["sla_hours"]
        assert sla["critical"] < sla["high"]
        assert sla["high"] < sla["medium"]
        assert sla["medium"] < sla["low"]


class TestSalesConfig:
    def test_load_sales_yaml(self):
        path = SAMPLES_DIR / "sales.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)
        assert "qualification" in config
        assert "autosend" in config

    def test_sales_qualification_structure(self):
        path = SAMPLES_DIR / "sales.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)

        qual = config["qualification"]
        assert "qualified_threshold" in qual
        assert "spam_threshold" in qual
        assert qual["spam_threshold"] > 0.5  # Reasonable spam threshold

    def test_sales_autosend_defaults(self):
        path = SAMPLES_DIR / "sales.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)

        autosend = config["autosend"]
        assert autosend["enabled"] is False

    def test_sales_followup_structure(self):
        path = SAMPLES_DIR / "sales.yaml"
        with open(path) as f:
            config = yaml.safe_load(f)

        followup = config["follow_up"]
        assert followup["enabled"] is True
        assert followup["max_follow_ups"] > 0


class TestYAMLSafety:
    """Ensure YAML configs don't contain dangerous patterns."""

    def test_no_yaml_injection(self):
        """Verify safe_load handles safely."""
        dangerous = "!!python/object/apply:os.system ['echo pwned']"
        # yaml.safe_load should not execute this
        result = yaml.safe_load(dangerous)
        assert result is not None  # parsed as string, not executed

    def test_invalid_yaml_handled(self):
        """Verify invalid YAML is caught gracefully."""
        invalid = "routing:\n  team_map:\n    billing: [unclosed"
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(invalid)
