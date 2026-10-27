"""Lovelace card registration helpers and storage-mode resource wiring."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant

from custom_components.high_school_sports_scores import async_setup
from custom_components.high_school_sports_scores.const import VERSION
from custom_components.high_school_sports_scores.frontend_register import (
    _lovelace_resource_mode,
    async_register_frontend,
    card_loader_url,
)

_BOOT = "deadbeefcafebabe"
_HASH = "abc123def456ab12"
_REGISTER = "custom_components.high_school_sports_scores.frontend_register"


@contextmanager
def _patched_registration():
    """Bundle reads and HTTP registration stay offline and deterministic."""
    with (
        patch(f"{_REGISTER}.card_bundle_available", return_value=True),
        patch(f"{_REGISTER}._register_static_http_path", new_callable=AsyncMock) as static_path,
        patch(f"{_REGISTER}.bundle_content_hash", return_value=_HASH),
        patch(f"{_REGISTER}.card_boot_token", return_value=_BOOT),
        patch(f"{_REGISTER}._LOVELACE_RESOURCE_RETRY_SECONDS", 0),
    ):
        yield static_path


def _storage_lovelace(hass: HomeAssistant, items: list[dict] | None = None) -> MagicMock:
    resources = MagicMock()
    resources.loaded = True
    resources.async_items.return_value = items or []
    resources.async_create_item = AsyncMock()
    resources.async_update_item = AsyncMock()
    resources.async_delete_item = AsyncMock()
    lovelace = MagicMock()
    lovelace.resource_mode = "storage"
    lovelace.resources = resources
    hass.data["lovelace"] = lovelace
    return resources


def test_lovelace_resource_mode_uses_resource_mode_on_ha_2026_9() -> None:
    legacy = MagicMock()
    legacy.resource_mode = "storage"
    legacy.mode = "yaml"
    assert _lovelace_resource_mode(legacy) == "storage"

    older = MagicMock(spec=[])
    older.mode = "storage"
    assert _lovelace_resource_mode(older) == "storage"


@pytest.mark.asyncio
async def test_static_view_registers_before_lovelace_resources(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """The card URL is served as soon as the integration sets up, not after startup."""
    with _patched_registration() as static_path:
        assert await async_setup(hass, {})

    static_path.assert_awaited()


@pytest.mark.asyncio
async def test_async_setup_waits_for_lovelace_storage_mode(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Registration waits until Lovelace mode is storage, not only until hass.data exists."""

    class _Lovelace:
        def __init__(self) -> None:
            self.resources = MagicMock()
            self.resources.loaded = True
            self.resources.async_items.return_value = []
            self.resources.async_create_item = AsyncMock()
            self._modes = iter([None, "storage"])

        @property
        def resource_mode(self) -> str | None:
            return next(self._modes)

    lovelace = _Lovelace()
    hass.data["lovelace"] = lovelace

    with _patched_registration():
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    lovelace.resources.async_create_item.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_setup_creates_lovelace_loader_resource(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Storage-mode Lovelace gets one js loader, also injected for the card picker."""
    resources = _storage_lovelace(hass)
    loader_url = card_loader_url(VERSION, _BOOT)

    with (
        _patched_registration(),
        patch("homeassistant.components.frontend.add_extra_js_url") as mock_extra_js,
    ):
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    resources.async_create_item.assert_awaited_once_with(
        {"res_type": "js", "url": loader_url}
    )
    resources.async_update_item.assert_not_called()
    mock_extra_js.assert_called_once_with(hass, loader_url, es5=False)


@pytest.mark.asyncio
async def test_async_setup_migrates_legacy_js_resource(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """An existing card.js row is updated in place when the loader URL changes."""
    existing_id = "abc123"
    resources = _storage_lovelace(
        hass,
        [
            {
                "id": existing_id,
                "url": "/high_school_sports_scores/high-school-sports-scores-card.js?v=0.1.0-beta.1",
                "type": "js",
            }
        ],
    )

    with _patched_registration():
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    resources.async_create_item.assert_not_called()
    resources.async_delete_item.assert_not_called()
    resources.async_update_item.assert_awaited_once_with(
        existing_id,
        {"res_type": "js", "url": card_loader_url(VERSION, _BOOT)},
    )


@pytest.mark.asyncio
async def test_async_setup_migrates_legacy_module_resource_and_drops_duplicate(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """A module.js row and a second card row become one loader resource."""
    resources = _storage_lovelace(
        hass,
        [
            {
                "id": "module-row",
                "url": "/high_school_sports_scores/high-school-sports-scores-card.module.js?v=0.1.0-beta.11&b=1",
                "type": "module",
            },
            {
                "id": "js-row",
                "url": "/high_school_sports_scores/high-school-sports-scores-card.js?v=0.1.0-beta.11",
                "res_type": "js",
            },
        ],
    )

    with _patched_registration():
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    resources.async_create_item.assert_not_called()
    resources.async_update_item.assert_awaited_once_with(
        "module-row",
        {"res_type": "js", "url": card_loader_url(VERSION, _BOOT)},
    )
    resources.async_delete_item.assert_awaited_once_with("js-row")


@pytest.mark.asyncio
async def test_matching_loader_url_is_not_rewritten(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    resources = _storage_lovelace(
        hass,
        [
            {
                "id": "current",
                "url": card_loader_url(VERSION, _BOOT),
                "type": "js",
            }
        ],
    )

    with _patched_registration():
        assert await async_setup(hass, {})
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    resources.async_create_item.assert_not_called()
    resources.async_update_item.assert_not_called()
    resources.async_delete_item.assert_not_called()


@pytest.mark.asyncio
async def test_prompt_browser_reload_after_first_resource_create(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Creating the resource while the UI is already open asks for one reload."""
    _storage_lovelace(hass)

    with (
        _patched_registration(),
        patch("homeassistant.components.frontend.add_extra_js_url"),
        patch("homeassistant.components.persistent_notification.async_create") as mock_notify,
        patch("homeassistant.helpers.issue_registry.async_create_issue") as mock_issue,
        patch.object(hass.config_entries, "async_entries", return_value=[MagicMock()]),
    ):
        await async_register_frontend(hass, prompt_browser_reload=True)
        await hass.async_block_till_done()

    mock_notify.assert_called_once()
    mock_issue.assert_called_once()


@pytest.mark.asyncio
async def test_boot_token_refresh_does_not_prompt(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """A restart changes the boot token but the installed version did not."""
    _storage_lovelace(
        hass,
        [
            {
                "id": "current",
                "url": card_loader_url(VERSION, "previousboot"),
                "type": "js",
            }
        ],
    )

    with (
        _patched_registration(),
        patch("homeassistant.components.frontend.add_extra_js_url"),
        patch("homeassistant.components.persistent_notification.async_create") as mock_notify,
        patch.object(hass.config_entries, "async_entries", return_value=[MagicMock()]),
    ):
        await async_register_frontend(hass, prompt_browser_reload=True)
        await hass.async_block_till_done()

    mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_version_change_while_ui_is_open_prompts(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    _storage_lovelace(
        hass,
        [
            {
                "id": "old",
                "url": card_loader_url("0.1.0-beta.11", "previousboot"),
                "type": "js",
            }
        ],
    )

    with (
        _patched_registration(),
        patch("homeassistant.components.frontend.add_extra_js_url"),
        patch("homeassistant.components.persistent_notification.async_create") as mock_notify,
        patch("homeassistant.helpers.issue_registry.async_create_issue"),
        patch.object(hass.config_entries, "async_entries", return_value=[MagicMock()]),
    ):
        await async_register_frontend(hass, prompt_browser_reload=True)
        await hass.async_block_till_done()

    mock_notify.assert_called_once()
