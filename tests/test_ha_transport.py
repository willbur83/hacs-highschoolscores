"""Home Assistant wiring smoke tests for the async transport."""

from __future__ import annotations

import pytest

pytest.importorskip("homeassistant")

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.maxpreps.async_transport import AiohttpTransport
from custom_components.maxpreps.ha_transport import create_ha_transport


@pytest.mark.asyncio
async def test_create_ha_transport_uses_shared_session(
    hass, enable_custom_integrations: None
) -> None:
    """HA factory returns a transport backed by the shared client session."""
    transport = create_ha_transport(hass)
    shared = async_get_clientsession(hass)

    assert isinstance(transport, AiohttpTransport)
    assert transport._session is shared
