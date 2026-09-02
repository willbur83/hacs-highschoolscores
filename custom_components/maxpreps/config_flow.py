"""Config flow for MaxPreps school search and sport subscriptions."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from custom_components.maxpreps import client_factory
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
            if not selected_keys:
                errors[CONF_SUBSCRIPTIONS] = "required"
            elif not isinstance(selected_keys, list):
                errors[CONF_SUBSCRIPTIONS] = "invalid"
            else:
                subscriptions: list[dict[str, str]] = []
                for key in selected_keys:
                    program = self._subscription_options.get(key)
                    if program is None:
                        errors[CONF_SUBSCRIPTIONS] = "invalid"
                        break
                    subscriptions.append(
                        {
                            CONF_SPORT: program.sport,
                            CONF_GENDER: program.gender,
                            CONF_LEVEL: program.level,
                        }
                    )
                else:
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
