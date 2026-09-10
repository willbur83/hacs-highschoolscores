"""High School Sports Scores program sensors backed by the school coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.high_school_sports_scores.const import ATTRIBUTION, CONF_SCHOOL_LOGO_OVERRIDE, DOMAIN
from custom_components.high_school_sports_scores.coordinator import (
    MaxPrepsDataUpdateCoordinator,
    ProgramSnapshot,
)
from custom_components.high_school_sports_scores.program_sensor import (
    find_last_game,
    find_next_game,
    game_attribute,
    program_display_label,
    program_is_available,
    program_native_value,
    program_team_record,
    program_unique_id,
)
from custom_components.high_school_sports_scores.school_logo import resolve_school_entity_picture

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up program sensors for a config entry."""
    coordinator: MaxPrepsDataUpdateCoordinator = entry.runtime_data
    data = coordinator.data
    if data is None:
        return

    async_add_entities(
        HighSchoolSportsScoresProgramSensor(coordinator, program) for program in data.programs
    )


class HighSchoolSportsScoresProgramSensor(CoordinatorEntity[MaxPrepsDataUpdateCoordinator], SensorEntity):
    """One sensor per subscribed school-year program."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: MaxPrepsDataUpdateCoordinator,
        program: ProgramSnapshot,
    ) -> None:
        super().__init__(coordinator)
        self._program_key = (program.sport, program.gender, program.level)
        data = coordinator.data
        assert data is not None
        school = data.school
        self._attr_unique_id = program_unique_id(school.school_id, program)
        self._attr_translation_key = "program"
        self._attr_translation_placeholders = {
            "gender": program.gender,
            "level": program.level,
            "sport": program.sport,
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, school.school_id)},
            name=school.name,
            configuration_url=school.canonical_url,
        )

    @property
    def program(self) -> ProgramSnapshot:
        """Current coordinator snapshot for this subscription."""
        data = self.coordinator.data
        if data is None:
            raise RuntimeError("coordinator data is not available")
        sport, gender, level = self._program_key
        for program in data.programs:
            if (
                program.sport == sport
                and program.gender == gender
                and program.level == level
            ):
                return program
        raise RuntimeError(f"program not found for {self._program_key!r}")

    @property
    def available(self) -> bool:
        return program_is_available(self.program)

    @property
    def entity_picture(self) -> str | None:
        data = self.coordinator.data
        if data is None:
            return None
        return resolve_school_entity_picture(
            mascot_url=data.school.mascot_url,
            logo_override=self.coordinator.config_entry.options.get(
                CONF_SCHOOL_LOGO_OVERRIDE
            ),
            programs=data.programs,
        )

    @property
    def native_value(self) -> str | None:
        if not self.available:
            return None
        return program_native_value(self.program)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if data is None:
            return None

        program = self.program
        attributes: dict[str, Any] = {
            "school_id": data.school.school_id,
            "school_name": data.school.name,
            "sport": program.sport,
            "gender": program.gender,
            "level": program.level,
            "year": data.applicable_school_year,
            "display_label": program_display_label(program),
            "attribution": ATTRIBUTION,
        }

        team_record = program_team_record(program)
        if team_record is not None:
            attributes["team_record"] = team_record

        last_game = find_last_game(program)
        if last_game is not None:
            attributes["last_game"] = game_attribute(last_game)

        next_game = find_next_game(program)
        if next_game is not None:
            attributes["next_game"] = game_attribute(next_game)

        return attributes
