"""Config flow for MaxPreps (stub for Slice 0)."""

from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class MaxPrepsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MaxPreps."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        return self.async_abort(reason="not_implemented")
