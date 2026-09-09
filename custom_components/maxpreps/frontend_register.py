"""Optional Phase 4 Lovelace card static path and JS registration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from custom_components.maxpreps.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "maxpreps-card.js"
WWW_DIR = Path(__file__).resolve().parent / "www"
CARD_PATH = WWW_DIR / CARD_FILENAME
URL_BASE = f"/{DOMAIN}"


def card_bundle_available() -> bool:
    """Return whether the built Lovelace card bundle is on disk."""
    return CARD_PATH.is_file()


async def _register_bundle_paths_and_js(hass: HomeAssistant) -> None:
    """Register static paths and Lovelace JS when http/frontend are importable."""
    from homeassistant.components.http import StaticPathConfig

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, WWW_DIR, cache_headers=False)]
    )

    from homeassistant.components import frontend

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
    except (ImportError, ModuleNotFoundError, AttributeError, RuntimeError) as err:
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
