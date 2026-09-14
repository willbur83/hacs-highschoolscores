"""Optional Phase 4 Lovelace card static path and JS registration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from custom_components.high_school_sports_scores.const import DOMAIN, VERSION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "high-school-sports-scores-card.js"
WWW_DIR = Path(__file__).resolve().parent / "www"
CARD_PATH = WWW_DIR / CARD_FILENAME
URL_BASE = f"/{DOMAIN}"
_LOVELACE_RESOURCE_RETRY_SECONDS = 5
_MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS = 60


def card_bundle_available() -> bool:
    """Return whether the built Lovelace card bundle is on disk."""
    return CARD_PATH.is_file()


def module_resource_url(version: str = VERSION) -> str:
    """Versioned Lovelace module URL (storage-mode resource)."""
    return f"{URL_BASE}/{CARD_FILENAME}?v={version}"


def resource_path_from_url(url: str) -> str:
    """Strip query string from a resource URL."""
    return url.split("?", 1)[0]


def resource_version_from_url(url: str) -> str | None:
    """Parse ``v`` query parameter from a resource URL."""
    query = parse_qs(urlparse(url).query)
    values = query.get("v")
    if not values:
        return None
    return values[0]


async def _register_static_http_path(hass: HomeAssistant) -> None:
    """Serve the built card bundle under /high_school_sports_scores/."""
    import importlib

    http = importlib.import_module("homeassistant.components.http")
    await hass.http.async_register_static_paths(
        [http.StaticPathConfig(URL_BASE, WWW_DIR, cache_headers=False)]
    )


async def _async_ensure_resources_loaded(resources: Any) -> bool:
    """Load the Lovelace resource collection before reading or mutating items."""
    if resources.loaded:
        return True
    async_load = getattr(resources, "async_load", None)
    if async_load is None:
        return False
    await async_load()
    resources.loaded = True
    return True


async def _async_register_lovelace_module_resource(hass: HomeAssistant, version: str) -> None:
    """Register the card as a storage-mode Lovelace module resource (not add_extra_js_url)."""
    lovelace = None
    for attempt in range(_MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS):
        lovelace = hass.data.get("lovelace")
        if lovelace is not None:
            break
        if attempt + 1 < _MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS:
            await asyncio.sleep(_LOVELACE_RESOURCE_RETRY_SECONDS)
    if lovelace is None:
        _LOGGER.warning(
            "Lovelace not initialized after waiting; add JavaScript module resource manually: %s",
            module_resource_url(version),
        )
        return

    mode = getattr(lovelace, "mode", None)
    if mode != "storage":
        _LOGGER.info(
            "Lovelace YAML mode: add JavaScript module resource manually: %s",
            module_resource_url(version),
        )
        return

    resources = lovelace.resources
    resources_ready = False
    for attempt in range(_MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS):
        if await _async_ensure_resources_loaded(resources):
            resources_ready = True
            break
        if attempt + 1 < _MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS:
            await asyncio.sleep(_LOVELACE_RESOURCE_RETRY_SECONDS)
    if not resources_ready:
        _LOGGER.warning(
            "Timed out waiting for Lovelace resources to load; "
            "card module not registered automatically"
        )
        return

    target_path = f"{URL_BASE}/{CARD_FILENAME}"
    target_url = module_resource_url(version)

    for resource in resources.async_items():
        if resource_path_from_url(resource["url"]) != target_path:
            continue
        current_version = resource_version_from_url(resource["url"])
        if current_version == version:
            _LOGGER.debug("Lovelace card resource already at version %s", version)
            return
        _LOGGER.info("Updating Lovelace card resource to version %s", version)
        await resources.async_update_item(
            resource["id"],
            {"res_type": "module", "url": target_url},
        )
        return

    _LOGGER.info("Registering Lovelace card module resource version %s", version)
    await resources.async_create_item(
        {"res_type": "module", "url": target_url},
    )


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register static path and Lovelace module resource when the bundle exists."""
    if not card_bundle_available():
        _LOGGER.warning(
            "Optional Phase 4 Lovelace card is unavailable (%s missing); "
            "config entries and sensors continue without frontend registration",
            CARD_PATH.name,
        )
        return

    try:
        await _register_static_http_path(hass)
        await _async_register_lovelace_module_resource(hass, VERSION)
    except (
        ImportError,
        ModuleNotFoundError,
        AttributeError,
        RuntimeError,
        KeyError,
    ) as err:
        _LOGGER.warning(
            "Optional Phase 4 Lovelace card registration skipped: %s",
            err,
        )
        return

    _LOGGER.debug(
        "Registered Lovelace card static path and module resource at %s",
        module_resource_url(VERSION),
    )


__all__ = [
    "CARD_FILENAME",
    "CARD_PATH",
    "URL_BASE",
    "WWW_DIR",
    "async_register_frontend",
    "card_bundle_available",
    "module_resource_url",
    "resource_path_from_url",
    "resource_version_from_url",
]
