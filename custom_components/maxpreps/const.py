"""Constants for the MaxPreps integration."""

DOMAIN = "maxpreps"

# Sports validated against the shared contests[] parser (Phase 3 §3.4 allowlist).
SUPPORTED_SPORTS: frozenset[str] = frozenset(
    {
        "Football",
        "Baseball",
        "Basketball",
        "Volleyball",
    }
)
