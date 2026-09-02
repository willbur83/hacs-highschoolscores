"""Constants for the MaxPreps integration."""

DOMAIN = "maxpreps"

# Keep in sync with manifest.json "version".
VERSION = "0.0.0"

INTEGRATION_REPO_URL = "https://github.com/willbur83/hacs-highschoolscores"
USER_AGENT = f"HomeAssistant-MaxPreps/{VERSION} (+{INTEGRATION_REPO_URL})"

# Production async transport limits (Phase 3 §3.5).
REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 5 * 1024 * 1024

# Sports validated against the shared contests[] parser (Phase 3 §3.4 allowlist).
SUPPORTED_SPORTS: frozenset[str] = frozenset(
    {
        "Football",
        "Baseball",
        "Basketball",
        "Volleyball",
    }
)
