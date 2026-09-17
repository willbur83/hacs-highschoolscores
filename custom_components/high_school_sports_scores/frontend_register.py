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
CARD_MODULE_FILENAME = "high-school-sports-scores-card.module.js"
WWW_DIR = Path(__file__).resolve().parent / "www"
CARD_PATH = WWW_DIR / CARD_FILENAME
CARD_MODULE_PATH = WWW_DIR / CARD_MODULE_FILENAME
URL_BASE = f"/{DOMAIN}"
_LOVELACE_RESOURCE_RETRY_SECONDS = 1
_MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS = 30
_LOVELACE_CARD_RESOURCE_TYPE = "js"


def card_bundle_available() -> bool:
    """Return whether the built Lovelace card bundles are on disk."""
    return CARD_PATH.is_file() and CARD_MODULE_PATH.is_file()


def module_resource_url(version: str = VERSION) -> str:
    """Versioned Lovelace card IIFE URL (storage-mode ``js`` resource)."""
    return f"{URL_BASE}/{CARD_FILENAME}?v={version}"


def picker_module_url(version: str = VERSION) -> str:
    """Versioned ES module URL for ``add_extra_js_url`` (modern HA frontend)."""
    return f"{URL_BASE}/{CARD_MODULE_FILENAME}?v={version}"


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


def _lovelace_resource_mode(lovelace: Any) -> str | None:
    """Return storage/yaml resource mode (HA 2026.9+ uses resource_mode on LovelaceData)."""
    resource_mode = getattr(lovelace, "resource_mode", None)
    if resource_mode is not None:
        return resource_mode
    return getattr(lovelace, "mode", None)


async def _async_wait_for_storage_lovelace(hass: HomeAssistant) -> Any | None:
    """Wait until Lovelace is in storage mode, or give up on YAML mode / timeout."""
    for attempt in range(_MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS):
        lovelace = hass.data.get("lovelace")
        if lovelace is not None:
            mode = _lovelace_resource_mode(lovelace)
            if mode == "storage":
                return lovelace
            if mode == "yaml":
                return None
        if attempt + 1 < _MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS:
            await asyncio.sleep(_LOVELACE_RESOURCE_RETRY_SECONDS)
    _LOGGER.warning(
        "Lovelace storage mode not ready after waiting; add JavaScript resource manually: %s",
        module_resource_url(VERSION),
    )
    return None


async def _async_register_lovelace_card_resource(hass: HomeAssistant, version: str) -> None:
    """Register the IIFE bundle as a storage-mode Lovelace ``js`` resource."""
    lovelace = await _async_wait_for_storage_lovelace(hass)
    if lovelace is None:
        lovelace_check = hass.data.get("lovelace")
        mode = _lovelace_resource_mode(lovelace_check) if lovelace_check else None
        if mode == "yaml":
            _LOGGER.info(
                "Lovelace YAML mode: add JavaScript resource manually: %s",
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
            "card script not registered automatically"
        )
        return

    target_path = f"{URL_BASE}/{CARD_FILENAME}"
    target_url = module_resource_url(version)

    for resource in resources.async_items():
        if resource_path_from_url(resource["url"]) != target_path:
            continue
        current_version = resource_version_from_url(resource["url"])
        current_type = resource.get("type")
        if current_version == version and current_type == _LOVELACE_CARD_RESOURCE_TYPE:
            _LOGGER.debug("Lovelace card resource already at version %s", version)
            return
        _LOGGER.info("Updating Lovelace card resource to version %s", version)
        await resources.async_update_item(
            resource["id"],
            {"res_type": _LOVELACE_CARD_RESOURCE_TYPE, "url": target_url},
        )
        return

    _LOGGER.info("Registering Lovelace card resource version %s", version)
    await resources.async_create_item(
        {"res_type": _LOVELACE_CARD_RESOURCE_TYPE, "url": target_url},
    )


def _register_bootstrap_card_script(hass: HomeAssistant, version: str) -> None:
    """Register picker module for modern browsers (``latestJS`` skips es5 extras)."""
    url = picker_module_url(version)
    try:
        from homeassistant.components import frontend

        frontend.add_extra_js_url(hass, url, es5=False)
    except KeyError as err:
        _LOGGER.warning(
            "Frontend bootstrap script registration unavailable (%s); "
            "card may be missing until a full UI reload",
            err,
        )
    except (ImportError, ModuleNotFoundError, AttributeError) as err:
        _LOGGER.warning(
            "Frontend bootstrap script registration skipped: %s",
            err,
        )


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register static path and Lovelace card script when the bundle exists."""
    if not card_bundle_available():
        _LOGGER.warning(
            "Optional Phase 4 Lovelace card is unavailable (%s missing); "
            "config entries and sensors continue without frontend registration",
            CARD_PATH.name,
        )
        return

    try:
        await _register_static_http_path(hass)
    except (
        ImportError,
        ModuleNotFoundError,
        AttributeError,
        RuntimeError,
        KeyError,
    ) as err:
        _LOGGER.warning(
            "Optional Phase 4 Lovelace card static path skipped: %s",
            err,
        )
        return

    await _async_register_lovelace_card_resource(hass, VERSION)
    _register_bootstrap_card_script(hass, VERSION)

    _LOGGER.debug(
        "Registered Lovelace card static path, js resource %s, picker module %s",
        module_resource_url(VERSION),
        picker_module_url(VERSION),
    )


__all__ = [
    "CARD_FILENAME",
    "CARD_MODULE_FILENAME",
    "CARD_MODULE_PATH",
    "CARD_PATH",
    "URL_BASE",
    "WWW_DIR",
    "async_register_frontend",
    "card_bundle_available",
    "module_resource_url",
    "picker_module_url",
    "resource_path_from_url",
    "resource_version_from_url",
]
