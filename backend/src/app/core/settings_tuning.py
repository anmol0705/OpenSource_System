"""Tuning constants for agent behavior — thresholds, iteration caps,
model tier assignments, cost ceilings. These are DELIBERATE ENGINEERING
DECISIONS, not secrets or environment config — hence a typed Python
module here, not .env or JSON. Changing a value requires understanding
the tradeoff (see comments on each), not just editing a number blind.
"""

# Investigator (Phase 4/5)
INVESTIGATION_CONFIDENCE_THRESHOLD = 0.75  # below this, keep investigating
MAX_INVESTIGATION_ITERATIONS = 5  # hard stop regardless of confidence —
# protects against a runaway loop and cost

# Implementer (Phase 6)
MAX_IMPLEMENTATION_ITERATIONS = 4
ALLOWED_TEST_COMMANDS = ["python -m pytest", "pytest"]  # allowlist, not
# blocklist — nothing else may run,
# regardless of what generates it

# Cost governance (Phase 6)
DEFAULT_MAX_RUN_COST_USD = 0.50
