"""Constants for the MaxPreps integration."""

from datetime import timedelta

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

# Config entry data keys (stable school identity).
CONF_SCHOOL_ID = "school_id"
CONF_CANONICAL_URL = "canonical_url"
CONF_NAME = "name"
CONF_CITY = "city"
CONF_STATE = "state"
CONF_MASCOT = "mascot"
CONF_MASCOT_URL = "mascot_url"

# Config entry options keys (mutable subscriptions).
CONF_SUBSCRIPTIONS = "subscriptions"
CONF_SPORT = "sport"
CONF_GENDER = "gender"
CONF_LEVEL = "level"

# Coordinator polling (Phase 3 §3.6).
UPDATE_INTERVAL = timedelta(hours=12)

# Config flow form field names.
CONF_QUERY = "query"
CONF_SCHOOL = "school"
