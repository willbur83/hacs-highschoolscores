"""Lovelace card static serving and resource registration.

The dashboard script is not a single long-lived versioned URL. Home Assistant's
service worker stores same-origin files with stale-while-revalidate and ignores
Cache-Control, and a kiosk that fetches the card before this view exists can
keep a 404 or a bad 200 for that exact URL. A reload then revalidates against
the browser HTTP cache and stays on the bad body.

Registration therefore:

- installs the HTTP view during domain setup, before the first data refresh
- publishes one loader URL whose boot token changes every process, so a
  previous failure is not reused after a restart
- serves the built bundle with a content hash; matching hashes are immutable
  and every other response (including 404) is not stored
- migrates an existing Lovelace resource row instead of adding a second one
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from custom_components.high_school_sports_scores.const import DOMAIN, VERSION

if TYPE_CHECKING:
    from aiohttp import web
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_TAG = "high-school-sports-scores-card"
CARD_FILENAME = "high-school-sports-scores-card.js"
CARD_MODULE_FILENAME = "high-school-sports-scores-card.module.js"
LOADER_FILENAME = "high-school-sports-scores-card-loader.js"
WWW_DIR = Path(__file__).resolve().parent / "www"
CARD_PATH = WWW_DIR / CARD_FILENAME
CARD_MODULE_PATH = WWW_DIR / CARD_MODULE_FILENAME
_LOADER_TEMPLATE_PATH = Path(__file__).resolve().parent / "card_loader.js.tpl"
URL_BASE = f"/{DOMAIN}"
_LOVELACE_RESOURCE_RETRY_SECONDS = 1
_MAX_LOVELACE_RESOURCE_WAIT_ATTEMPTS = 30
_LOVELACE_CARD_RESOURCE_TYPE = "js"
_CONTENT_HASH_LENGTH = 16
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
REVALIDATE_CACHE_CONTROL = "no-cache"
NO_STORE_CACHE_CONTROL = "no-store"
_REGISTER_EXCEPTIONS = (
    ImportError,
    ModuleNotFoundError,
    AttributeError,
    RuntimeError,
    KeyError,
    ValueError,
)
_bundle_cache: dict[str, tuple[int, int, bytes, str]] = {}
_loader_template: str | None = None
_view_cls: type | None = None


def card_bundle_available() -> bool:
    """Return whether the built Lovelace card bundle is on disk."""
    return CARD_PATH.is_file()


def bundle_content_hash(path: Path | None = None) -> str:
    """Return a short SHA-256 of a built bundle."""
    _body, digest = read_cached_bundle(path or CARD_PATH)
    return digest


def read_cached_bundle(path: Path) -> tuple[bytes, str]:
    """Read a bundle, reusing bytes when size and mtime are unchanged."""
    stat = path.stat()
    key = str(path)
    cached = _bundle_cache.get(key)
    if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
        return cached[2], cached[3]
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:_CONTENT_HASH_LENGTH]
    _bundle_cache[key] = (stat.st_mtime_ns, stat.st_size, data, digest)
    return data, digest


def card_bundle_url(version: str, content_hash: str) -> str:
    """URL for the built card. The hash changes when the file bytes change."""
    return f"{URL_BASE}/{CARD_FILENAME}?v={version}&h={content_hash}"


def card_loader_url(version: str, boot: str | None = None) -> str:
    """URL for the no-store loader. ``boot`` changes once per Home Assistant process."""
    url = f"{URL_BASE}/{LOADER_FILENAME}?v={version}"
    if boot:
        url = f"{url}&b={boot}"
    return url


def card_resource_paths() -> frozenset[str]:
    """Resource paths this integration owns, including pre-loader URLs."""
    return frozenset(
        {
            f"{URL_BASE}/{CARD_FILENAME}",
            f"{URL_BASE}/{CARD_MODULE_FILENAME}",
            f"{URL_BASE}/{LOADER_FILENAME}",
        }
    )


def bundle_cache_control(*, request_hash: str | None, current_hash: str) -> str:
    """Cache the bundle only when the request names the hash of these exact bytes."""
    if request_hash and request_hash == current_hash:
        return IMMUTABLE_CACHE_CONTROL
    return REVALIDATE_CACHE_CONTROL


def if_none_match(header: str | None, etag: str) -> bool:
    """Return whether ``If-None-Match`` names this strong ETag."""
    if not header:
        return False
    quoted = f'"{etag}"'
    for part in header.split(","):
        candidate = part.strip()
        if candidate in {"*", quoted, etag}:
            return True
    return False


def js_string_literal(value: str) -> str:
    """Escape ``value`` for inclusion inside a double-quoted JavaScript string."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _read_card_loader_template() -> str:
    """Read the loader template from disk. Call this off the event loop."""
    return _LOADER_TEMPLATE_PATH.read_text(encoding="utf-8")


async def async_load_card_loader_template(hass: HomeAssistant) -> str:
    """Read the loader template once, on the executor, and cache it."""
    global _loader_template
    if _loader_template is None:
        _loader_template = await hass.async_add_executor_job(_read_card_loader_template)
    return _loader_template


def render_card_loader_script(
    version: str,
    bundle_url: str,
    *,
    tag: str = CARD_TAG,
) -> str:
    """Fill the cached loader template. The loader fetches ``bundle_url`` and can retry.

    Request handlers must call ``async_load_card_loader_template`` first. The
    synchronous read below is only for callers that are already off the event loop.
    """
    global _loader_template
    if _loader_template is None:
        _loader_template = _read_card_loader_template()
    return (
        _loader_template.replace("@@VERSION@@", js_string_literal(version))
        .replace("@@BUNDLE_URL@@", js_string_literal(bundle_url))
        .replace("@@TAG@@", js_string_literal(tag))
    )


def resource_path_from_url(url: str) -> str:
    """Strip query string from a resource URL."""
    return url.split("?", 1)[0]


def resource_query_value(url: str, key: str) -> str | None:
    """Parse one query parameter from a resource URL."""
    query = parse_qs(urlparse(url).query)
    values = query.get(key)
    if not values:
        return None
    return values[0]


def resource_version_from_url(url: str) -> str | None:
    """Parse ``v`` query parameter from a resource URL."""
    return resource_query_value(url, "v")


def _resource_type(resource: dict[str, Any]) -> str | None:
    """Read the Lovelace resource type from either storage shape."""
    for key in ("type", "res_type"):
        value = resource.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _registration_lock(hass: HomeAssistant) -> asyncio.Lock:
    domain_data = hass.data.setdefault(DOMAIN, {})
    lock = domain_data.get("card_register_lock")
    if isinstance(lock, asyncio.Lock):
        return lock
    lock = asyncio.Lock()
    return domain_data.setdefault("card_register_lock", lock)


def card_boot_token(hass: HomeAssistant) -> str:
    """Return the per-process cache-buster for the loader URL."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    token = domain_data.get("card_boot_token")
    if isinstance(token, str) and token:
        return token
    token = secrets.token_hex(8)
    return domain_data.setdefault("card_boot_token", token)


def _card_view_class() -> type:
    """Build the HTTP view lazily so unit tests can import this module without HA."""
    global _view_cls
    if _view_cls is not None:
        return _view_cls

    from homeassistant.components.http import HomeAssistantView

    class HighSchoolSportsScoresCardView(HomeAssistantView):
        """Serve the card loader and built bundles."""

        url = f"{URL_BASE}/{{filename}}"
        name = f"{DOMAIN}:card_static"
        requires_auth = False
        cors_allowed = True

        async def get(self, request: web.Request, filename: str) -> web.Response:
            """Return one card file, or a no-store 404."""
            return await _async_serve_card_file(request, filename)

    _view_cls = HighSchoolSportsScoresCardView
    return _view_cls


def _response_headers(cache_control: str, etag: str | None = None) -> dict[str, str]:
    headers = {
        "Cache-Control": cache_control,
        "X-Content-Type-Options": "nosniff",
    }
    if cache_control == NO_STORE_CACHE_CONTROL:
        headers["Pragma"] = "no-cache"
        headers["Expires"] = "0"
    if etag:
        headers["ETag"] = f'"{etag}"'
    return headers


def _js_response(body: bytes, cache_control: str, etag: str | None = None) -> web.Response:
    from aiohttp import web

    return web.Response(
        body=body,
        status=200,
        content_type="text/javascript",
        charset="utf-8",
        headers=_response_headers(cache_control, etag),
    )


def _status_response(status: int, cache_control: str, etag: str | None = None) -> web.Response:
    from aiohttp import web

    return web.Response(status=status, headers=_response_headers(cache_control, etag))


async def _async_serve_bundle(request: web.Request, path: Path) -> web.Response:
    hass = request.app["hass"]
    try:
        loaded = await hass.async_add_executor_job(read_cached_bundle, path)
    except OSError:
        _LOGGER.warning("Lovelace card file %s could not be read", path.name)
        return _status_response(404, NO_STORE_CACHE_CONTROL)
    data, digest = loaded
    request_hash = request.query.get("h")
    cache_control = bundle_cache_control(
        request_hash=request_hash if isinstance(request_hash, str) else None,
        current_hash=digest,
    )
    if if_none_match(request.headers.get("If-None-Match"), digest):
        return _status_response(304, cache_control, digest)
    return _js_response(data, cache_control, digest)


async def _async_serve_card_file(request: web.Request, filename: str) -> web.Response:
    """Serve the loader with no-store, or a bundle keyed by its content hash."""
    if filename == LOADER_FILENAME:
        if not CARD_PATH.is_file():
            return _status_response(404, NO_STORE_CACHE_CONTROL)
        hass = request.app["hass"]
        try:
            content_hash = await hass.async_add_executor_job(bundle_content_hash)
            await async_load_card_loader_template(hass)
        except OSError:
            _LOGGER.warning("Lovelace card bundle could not be read for the loader")
            return _status_response(404, NO_STORE_CACHE_CONTROL)
        script = render_card_loader_script(VERSION, card_bundle_url(VERSION, content_hash))
        return _js_response(script.encode("utf-8"), NO_STORE_CACHE_CONTROL)
    if filename == CARD_FILENAME:
        if not CARD_PATH.is_file():
            return _status_response(404, NO_STORE_CACHE_CONTROL)
        return await _async_serve_bundle(request, CARD_PATH)
    if filename == CARD_MODULE_FILENAME and CARD_MODULE_PATH.is_file():
        return await _async_serve_bundle(request, CARD_MODULE_PATH)
    return _status_response(404, NO_STORE_CACHE_CONTROL)


async def _register_static_http_path(hass: HomeAssistant) -> None:
    """Serve card files under /high_school_sports_scores/."""
    try:
        await async_load_card_loader_template(hass)
    except OSError as err:
        _LOGGER.warning("Lovelace card loader template could not be read: %s", err)
        return
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("card_http_view"):
        return
    try:
        hass.http.register_view(_card_view_class()())
    except ValueError as err:
        if "duplicate" not in str(err).lower() and "already" not in str(err).lower():
            raise
        _LOGGER.debug("Lovelace card HTTP view already registered: %s", err)
    domain_data["card_http_view"] = True


async def async_register_card_static(hass: HomeAssistant) -> None:
    """Register the card HTTP view. A missing bundle or HTTP stack does not raise."""
    if not card_bundle_available():
        return
    try:
        await _register_static_http_path(hass)
    except _REGISTER_EXCEPTIONS as err:
        _LOGGER.warning("Optional Lovelace card static path skipped: %s", err)


def _lovelace_resource_mode(lovelace: Any) -> str | None:
    """Return storage/yaml resource mode (HA 2026.9+ uses resource_mode on LovelaceData)."""
    resource_mode = getattr(lovelace, "resource_mode", None)
    if resource_mode is not None:
        return resource_mode
    return getattr(lovelace, "mode", None)


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
        card_loader_url(VERSION),
    )
    return None


async def _async_delete_resource(resources: Any, resource_id: str) -> None:
    delete_item = getattr(resources, "async_delete_item", None)
    if delete_item is None:
        _LOGGER.warning(
            "Could not remove duplicate Lovelace card resource %s; delete it under "
            "Dashboards → Resources",
            resource_id,
        )
        return
    await delete_item(resource_id)


async def _async_register_lovelace_card_resource(
    hass: HomeAssistant, version: str, boot: str
) -> tuple[bool, str | None]:
    """Point the single storage-mode resource at the loader. Returns (written, previous version)."""
    lovelace = await _async_wait_for_storage_lovelace(hass)
    if lovelace is None:
        lovelace_check = hass.data.get("lovelace")
        mode = _lovelace_resource_mode(lovelace_check) if lovelace_check else None
        if mode == "yaml":
            _LOGGER.info(
                "Lovelace YAML mode: add a JavaScript resource (type: js) manually: %s",
                card_loader_url(version),
            )
        return False, None

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
        return False, None

    target_url = card_loader_url(version, boot)
    owned = [
        resource
        for resource in resources.async_items()
        if resource_path_from_url(resource["url"]) in card_resource_paths()
    ]
    if not owned:
        _LOGGER.info("Registering Lovelace card loader %s", target_url)
        await resources.async_create_item(
            {"res_type": _LOVELACE_CARD_RESOURCE_TYPE, "url": target_url},
        )
        return True, None

    primary = owned[0]
    previous_version = resource_version_from_url(primary["url"])
    written = False
    if primary["url"] != target_url or _resource_type(primary) != _LOVELACE_CARD_RESOURCE_TYPE:
        _LOGGER.info("Updating Lovelace card resource to %s", target_url)
        await resources.async_update_item(
            primary["id"],
            {"res_type": _LOVELACE_CARD_RESOURCE_TYPE, "url": target_url},
        )
        written = True
    else:
        _LOGGER.debug("Lovelace card resource already at %s", target_url)

    for extra in owned[1:]:
        _LOGGER.info("Removing duplicate Lovelace card resource %s", extra["url"])
        await _async_delete_resource(resources, extra["id"])
        written = True
    return written, previous_version


def _register_bootstrap_card_script(hass: HomeAssistant, url: str) -> bool:
    """Register the loader for the card picker. Return True when the URL changed."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    previous_url = domain_data.get("picker_module_url")
    if previous_url == url:
        return False

    try:
        from homeassistant.components import frontend

        if previous_url:
            try:
                frontend.remove_extra_js_url(hass, previous_url, es5=False)
            except KeyError:
                pass
        frontend.add_extra_js_url(hass, url, es5=False)
    except KeyError as err:
        _LOGGER.warning(
            "Frontend bootstrap script registration unavailable (%s); "
            "card may be missing until a full UI reload",
            err,
        )
        return False
    except (ImportError, ModuleNotFoundError, AttributeError) as err:
        _LOGGER.warning(
            "Frontend bootstrap script registration skipped: %s",
            err,
        )
        return False

    domain_data["picker_module_url"] = url
    return True


def _async_prompt_browser_reload(hass: HomeAssistant) -> None:
    """Surface a reload hint when card JS registered after the UI tab was opened."""
    from homeassistant.components import persistent_notification
    from homeassistant.helpers import issue_registry as ir

    issue_id = "browser_reload_recommended"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="browser_reload_recommended",
    )

    persistent_notification.async_create(
        hass,
        (
            "The Lovelace card script was registered after this browser tab loaded. "
            "Reload the page once so High School Sports Scores appears in the dashboard. "
            "If a kiosk still shows a red card or a 'did not load' message, clear that "
            "browser's cache for Home Assistant once."
        ),
        title="High School Sports Scores",
        notification_id=f"{DOMAIN}_browser_reload",
    )


async def async_register_frontend(
    hass: HomeAssistant, *, prompt_browser_reload: bool = False
) -> None:
    """Register the card view, storage-mode loader resource, and picker script."""
    if not card_bundle_available():
        _LOGGER.warning(
            "Optional Lovelace card is unavailable (%s missing); "
            "config entries and sensors continue without frontend registration",
            CARD_PATH.name,
        )
        return

    try:
        await _register_static_http_path(hass)
    except _REGISTER_EXCEPTIONS as err:
        _LOGGER.warning(
            "Optional Lovelace card static path skipped: %s",
            err,
        )
        return

    try:
        content_hash = await hass.async_add_executor_job(bundle_content_hash)
    except OSError as err:
        _LOGGER.warning("Lovelace card bundle could not be read (%s); resource not published", err)
        return

    boot = card_boot_token(hass)
    async with _registration_lock(hass):
        written, previous_version = await _async_register_lovelace_card_resource(
            hass, VERSION, boot
        )
        loader_url = card_loader_url(VERSION, boot)
        _register_bootstrap_card_script(hass, loader_url)

    if (
        prompt_browser_reload
        and written
        and previous_version != VERSION
        and hass.config_entries.async_entries(DOMAIN)
    ):
        _async_prompt_browser_reload(hass)

    _LOGGER.debug(
        "Registered Lovelace card view, loader %s, bundle %s",
        loader_url,
        card_bundle_url(VERSION, content_hash),
    )


__all__ = [
    "CARD_FILENAME",
    "CARD_MODULE_FILENAME",
    "CARD_MODULE_PATH",
    "CARD_PATH",
    "CARD_TAG",
    "IMMUTABLE_CACHE_CONTROL",
    "LOADER_FILENAME",
    "NO_STORE_CACHE_CONTROL",
    "REVALIDATE_CACHE_CONTROL",
    "URL_BASE",
    "WWW_DIR",
    "async_register_card_static",
    "async_register_frontend",
    "bundle_cache_control",
    "bundle_content_hash",
    "card_boot_token",
    "card_bundle_available",
    "card_bundle_url",
    "card_loader_url",
    "card_resource_paths",
    "if_none_match",
    "js_string_literal",
    "read_cached_bundle",
    "render_card_loader_script",
    "resource_path_from_url",
    "resource_query_value",
    "resource_version_from_url",
]
