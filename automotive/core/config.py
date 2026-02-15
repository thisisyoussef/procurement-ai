"""Automotive project configuration — reuses shared .env but provides automotive-specific defaults."""

from app.core.config import Settings, get_settings

# Re-export the shared settings — automotive uses the same env vars
# for database, API keys, etc. but can override behavior per-module.
__all__ = ["Settings", "get_settings"]


# Automotive-specific constants (not env-configurable, domain knowledge)
AUTOMOTIVE_PART_CATEGORIES = [
    "stamping",
    "die_casting",
    "injection_molding",
    "cnc_machining",
    "forging",
    "pcba",
    "wiring_harness",
    "rubber_sealing",
    "assembly",
    "other",
]

AUTOMOTIVE_CERTIFICATIONS = [
    "IATF 16949",
    "ISO 9001",
    "ISO 14001",
    "ISO 45001",
    "NADCAP",
    "AS9100",
]

PPAP_LEVELS = ["1", "2", "3", "4", "5"]

URGENCY_LEVELS = ["standard", "expedited", "urgent"]

COMPLEXITY_LEVELS = ["simple", "moderate", "complex"]

QUALIFICATION_STATUSES = ["qualified", "conditional", "disqualified"]

FINANCIAL_RISK_LEVELS = ["low", "moderate", "high", "insufficient_data"]

# Typical tooling cost ranges by part category
TOOLING_ESTIMATES = {
    "stamping": {"low": 50_000, "high": 300_000, "lead_weeks": "12–20"},
    "die_casting": {"low": 100_000, "high": 500_000, "lead_weeks": "16–24"},
    "injection_molding": {"low": 30_000, "high": 200_000, "lead_weeks": "16–20"},
    "cnc_machining": {"low": 2_000, "high": 20_000, "lead_weeks": "2–6"},
    "pcba": {"low": 5_000, "high": 50_000, "lead_weeks": "8–16"},
    "wiring_harness": {"low": 10_000, "high": 50_000, "lead_weeks": "8–12"},
    "forging": {"low": 50_000, "high": 200_000, "lead_weeks": "12–20"},
    "rubber_sealing": {"low": 20_000, "high": 100_000, "lead_weeks": "10–16"},
    "assembly": {"low": 10_000, "high": 100_000, "lead_weeks": "8–16"},
    "other": {"low": 10_000, "high": 200_000, "lead_weeks": "8–20"},
}

# Model tiering for automotive agents
MODEL_TIER_CHEAP = "claude-haiku-4-5-20251001"
MODEL_TIER_BALANCED = "claude-sonnet-4-5-20250929"
