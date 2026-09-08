"""Config flow for MaxPreps school search and sport subscriptions."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.helpers import selector

from custom_components.maxpreps import client_factory
from custom_components.maxpreps.coordinator import school_from_entry
from custom_components.maxpreps.const import (
    CONF_CANONICAL_URL,
    CONF_CITY,
    CONF_GENDER,
    CONF_LEVEL,
    CONF_MASCOT,
    CONF_MASCOT_URL,
    CONF_NAME,
    CONF_QUERY,
    CONF_SCHOOL,
    CONF_SCHOOL_ID,
    CONF_SPORT,
    CONF_STATE,
    CONF_SUBSCRIPTIONS,
    DOMAIN,
)
from custom_components.maxpreps.exceptions import MaxPrepsError
from custom_components.maxpreps.models import School, TeamSeason
from custom_components.maxpreps.programs import SchoolYearProgram, group_school_year_programs
from custom_components.maxpreps.school_year import applicable_school_year
from custom_components.maxpreps import school_year
from custom_components.maxpreps.selection import team_seasons_for_applicable_year

_LOGGER = logging.getLogger(__name__)

_SUBSCRIPTION_KEY_SEP = "\x1e"


def _format_school_location(school: School) -> str:
    if school.city and school.state:
        return f"{school.city}, {school.state}"
    if school.state:
        return school.state
    if school.city:
        return school.city
    return "Location unavailable"


def _format_school_label(school: School) -> str:
    label = f"{school.name} | {_format_school_location(school)}"
    if school.mascot:
        label = f"{label} · {school.mascot}"
    return label


def _subscription_key(program: SchoolYearProgram) -> str:
    return _SUBSCRIPTION_KEY_SEP.join((program.sport, program.gender, program.level))


def _subscription_key_from_parts(sport: str, gender: str, level: str) -> str:
    return _SUBSCRIPTION_KEY_SEP.join((sport, gender, level))


def _subscription_key_from_dict(subscription: dict[str, str]) -> str:
    return _subscription_key_from_parts(
        subscription[CONF_SPORT],
        subscription[CONF_GENDER],
        subscription[CONF_LEVEL],
    )


def _unresolved_program_label(subscription: dict[str, str], applicable_year: str) -> str:
    """Picker label when a configured subscription has no applicable-year provider rows."""
    return (
        f"{subscription[CONF_GENDER]} {subscription[CONF_LEVEL]} "
        f"{subscription[CONF_SPORT]} (waiting for {applicable_year})"
    )


def _build_subscription_options(
    hass: Any,
    team_seasons: list[TeamSeason],
    configured_subscriptions: list[dict[str, str]],
) -> dict[str, str]:
    """Union of discoverable programs and configured subscriptions for the picker."""
    local_date = school_year.homeassistant_local_date(hass)
    applicable_year = applicable_school_year(local_date)
    programs = _config_flow_programs(hass, team_seasons)
    options: dict[str, str] = {
        _subscription_key(program): program.display_label for program in programs
    }
    for subscription in configured_subscriptions:
        key = _subscription_key_from_dict(subscription)
        if key not in options:
            options[key] = _unresolved_program_label(subscription, applicable_year)
    return options


def _subscriptions_from_selected_keys(
    selected_keys: list[str],
    subscription_options: dict[str, str],
) -> tuple[list[dict[str, str]] | None, str | None]:
    """Validate picker output and return persisted subscription dicts."""
    if not selected_keys:
        return None, "required"
    subscriptions: list[dict[str, str]] = []
    for key in selected_keys:
        if key not in subscription_options:
            return None, "invalid"
        sport, gender, level = key.split(_SUBSCRIPTION_KEY_SEP, maxsplit=2)
        subscriptions.append(
            {
                CONF_SPORT: sport,
                CONF_GENDER: gender,
                CONF_LEVEL: level,
            }
        )
    return subscriptions, None


def _config_flow_programs(
    hass: Any, team_seasons: list[TeamSeason]
) -> list[SchoolYearProgram]:
    """Return one allowlisted program per (sport, gender, level) for the applicable year."""
    local_date = school_year.homeassistant_local_date(hass)
    applicable_year = applicable_school_year(local_date)
    filtered = team_seasons_for_applicable_year(team_seasons, applicable_year)
    return group_school_year_programs(filtered)


class MaxPrepsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MaxPreps."""

    VERSION = 1

    def __init__(self) -> None:
        self._search_results: dict[str, School] = {}
        self._selected_school: School | None = None
        self._subscription_options: dict[str, SchoolYearProgram] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle short-name school search."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = str(user_input.get(CONF_QUERY, "")).strip()
            if not query:
                errors[CONF_QUERY] = "required"
            else:
                try:
                    client = client_factory.create_async_client(self.hass)
                    schools = await client.search_schools(query)
                except MaxPrepsError:
                    errors["base"] = "search_failed"
                except Exception:  # noqa: BLE001 — hide transport surprises from the UI
                    _LOGGER.exception("Unexpected error during MaxPreps school search")
                    errors["base"] = "search_failed"
                else:
                    if not schools:
                        errors["base"] = "no_results"
                    else:
                        self._search_results = {
                            school.school_id: school for school in schools
                        }
                        return await self.async_step_school()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_QUERY): selector.TextSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_school(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Pick one school from the search results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            school_id = user_input.get(CONF_SCHOOL)
            school = (
                self._search_results.get(school_id) if school_id is not None else None
            )
            if school is None:
                errors[CONF_SCHOOL] = "invalid"
            else:
                await self.async_set_unique_id(school.school_id)
                self._abort_if_unique_id_configured()

                try:
                    client = client_factory.create_async_client(self.hass)
                    team_seasons = await client.get_school_teams(school)
                    programs = _config_flow_programs(self.hass, team_seasons)
                except MaxPrepsError:
                    errors["base"] = "school_load_failed"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Unexpected error loading MaxPreps school programs"
                    )
                    errors["base"] = "school_load_failed"
                else:
                    if not programs:
                        return self.async_abort(reason="no_supported_sports")

                    self._selected_school = school
                    self._subscription_options = {
                        _subscription_key(program): program for program in programs
                    }
                    return await self.async_step_subscriptions()

        school_options = [
            selector.SelectOptionDict(
                value=school.school_id,
                label=_format_school_label(school),
            )
            for school in self._search_results.values()
        ]

        return self.async_show_form(
            step_id="school",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCHOOL): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=school_options,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_subscriptions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Subscribe to one or more supported programs."""
        errors: dict[str, str] = {}
        school = self._selected_school

        if school is None:
            return await self.async_step_user()

        if user_input is not None:
            selected_keys = user_input.get(CONF_SUBSCRIPTIONS)
            if not isinstance(selected_keys, list):
                errors[CONF_SUBSCRIPTIONS] = "invalid"
            else:
                option_labels = {
                    key: program.display_label
                    for key, program in self._subscription_options.items()
                }
                subscriptions, error = _subscriptions_from_selected_keys(
                    selected_keys, option_labels
                )
                if error is not None:
                    errors[CONF_SUBSCRIPTIONS] = error
                elif subscriptions is not None:
                    data: dict[str, Any] = {
                        CONF_SCHOOL_ID: school.school_id,
                        CONF_CANONICAL_URL: school.canonical_url,
                        CONF_NAME: school.name,
                    }
                    if school.city is not None:
                        data[CONF_CITY] = school.city
                    if school.state is not None:
                        data[CONF_STATE] = school.state
                    if school.mascot is not None:
                        data[CONF_MASCOT] = school.mascot
                    if school.mascot_url is not None:
                        data[CONF_MASCOT_URL] = school.mascot_url

                    return self.async_create_entry(
                        title=school.name,
                        data=data,
                        options={CONF_SUBSCRIPTIONS: subscriptions},
                    )

        subscription_options = [
            selector.SelectOptionDict(
                value=key,
                label=program.display_label,
            )
            for key, program in self._subscription_options.items()
        ]

        return self.async_show_form(
            step_id="subscriptions",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SUBSCRIPTIONS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=subscription_options,
                            mode=selector.SelectSelectorMode.LIST,
                            multiple=True,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MaxPrepsOptionsFlow:
        """Return the options flow handler."""
        return MaxPrepsOptionsFlow()


class MaxPrepsOptionsFlow(OptionsFlowWithReload):
    """Edit sport subscriptions on an existing school config entry."""

    def __init__(self) -> None:
        self._subscription_options: dict[str, str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show current subscriptions and allow add/remove."""
        errors: dict[str, str] = {}
        entry = self.config_entry
        configured = list(entry.options.get(CONF_SUBSCRIPTIONS, []))

        if user_input is not None:
            selected_keys = user_input.get(CONF_SUBSCRIPTIONS)
            if not isinstance(selected_keys, list):
                errors[CONF_SUBSCRIPTIONS] = "invalid"
            else:
                subscriptions, error = _subscriptions_from_selected_keys(
                    selected_keys, self._subscription_options
                )
                if error is not None:
                    errors[CONF_SUBSCRIPTIONS] = error
                elif subscriptions is not None:
                    return self.async_create_entry(
                        data={CONF_SUBSCRIPTIONS: subscriptions},
                    )

        try:
            school = school_from_entry(entry)
            client = client_factory.create_async_client(self.hass)
            team_seasons = await client.get_school_teams(school)
            self._subscription_options = _build_subscription_options(
                self.hass, team_seasons, configured
            )
        except MaxPrepsError:
            errors["base"] = "school_load_failed"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error loading MaxPreps school programs")
            errors["base"] = "school_load_failed"

        subscription_options = [
            selector.SelectOptionDict(value=key, label=label)
            for key, label in self._subscription_options.items()
        ]
        suggested = {
            CONF_SUBSCRIPTIONS: [
                _subscription_key_from_dict(subscription) for subscription in configured
            ]
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_SUBSCRIPTIONS): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=subscription_options,
                                mode=selector.SelectSelectorMode.LIST,
                                multiple=True,
                            )
                        ),
                    }
                ),
                suggested,
            ),
            errors=errors,
        )
