"""Optional Phase 4 Lovelace card static path and JS registration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from custom_components.high_school_sports_scores.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "high-school-sports-scores-card.js"
WWW_DIR = Path(__file__).resolve().parent / "www"
CARD_PATH = WWW_DIR / CARD_FILENAME
URL_BASE = f"/{DOMAIN}"
_FRONTEND_EXTRA_MODULE_URL_KEY = "frontend_extra_module_url"


def _is_uninitialized_frontend_keyerror(err: KeyError) -> bool:
    """True when HA frontend is not initialized (e.g. phacc harness)."""
    return err.args == (_FRONTEND_EXTRA_MODULE_URL_KEY,)


def card_bundle_available() -> bool:
    """Return whether the built Lovelace card bundle is on disk."""
    return CARD_PATH.is_file()


async def _register_bundle_paths_and_js(hass: HomeAssistant) -> None:
    """Register static paths and Lovelace JS when http/frontend are importable."""
    import importlib

    # Dynamic import: optional http/frontend registration without manifest deps
    # (declaring them breaks pytest-homeassistant-custom-component; hassfest would
    # otherwise require dependencies for static homeassistant.components.* imports).
    http = importlib.import_module("homeassistant.components.http")
    await hass.http.async_register_static_paths(
        [http.StaticPathConfig(URL_BASE, WWW_DIR, cache_headers=False)]
    )

    frontend = importlib.import_module("homeassistant.components.frontend")
    frontend.add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILENAME}")


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the built card bundle when present; otherwise log and skip."""
    if not card_bundle_available():
        _LOGGER.warning(
            "Optional Phase 4 Lovelace card is unavailable (%s missing); "
            "config entries and sensors continue without frontend registration",
            CARD_PATH.name,
        )
        return

    try:
        await _register_bundle_paths_and_js(hass)
    except (
        ImportError,
        ModuleNotFoundError,
        AttributeError,
        RuntimeError,
        KeyError,
    ) as err:
        if isinstance(err, KeyError) and not _is_uninitialized_frontend_keyerror(err):
            raise
        _LOGGER.warning(
            "Optional Phase 4 Lovelace card registration skipped "
            "(Home Assistant frontend/http unavailable): %s",
            err,
        )
        return

    _LOGGER.debug(
        "Registered Phase 4 Lovelace card at %s/%s",
        URL_BASE,
        CARD_FILENAME,
    )


__all__ = [
    "CARD_FILENAME",
    "CARD_PATH",
    "URL_BASE",
    "WWW_DIR",
    "async_register_frontend",
    "card_bundle_available",
]
