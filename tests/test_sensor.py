"""Program sensor tests using fixture transport only."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from tests.device_registry_compat import async_get_device_for_config_entry

from custom_components.high_school_sports_scores.const import (
    ATTRIBUTION,
    CONF_GENDER,
    CONF_LEVEL,
    CONF_MASCOT_URL,
    CONF_SCHOOL_LOGO_OVERRIDE,
    CONF_SPORT,
    DOMAIN,
)
from custom_components.high_school_sports_scores.coordinator import (
    ProgramResolutionStatus,
    ProgramSnapshot,
    TermRefreshStatus,
    TermSnapshot,
)
from custom_components.high_school_sports_scores.models import Game, GameStatus, HomeAway, Schedule, TeamSeason
from custom_components.high_school_sports_scores.program_sensor import (
    find_last_game,
    find_next_game,
    game_attribute,
    iter_program_games,
    program_is_available,
    program_native_value,
    program_unique_id,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.helpers.coordinator_test_helpers import centennial_entry
from tests.test_coordinator import (
    FRESHMAN_BASEBALL_FALL_ID,
    FRESHMAN_BASEBALL_SPRING_ID,
    FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
    FRESHMAN_BASEBALL_SUBSCRIPTION,
    FOOTBALL_SUBSCRIPTION,
    UNRESOLVED_SUBSCRIPTION,
    CoordinatorTestTransport,
    coordinator_client,
    frozen_applicable_date,
)
from tests.test_search import CENTENNIAL_ROSWELL_ID, CENTENNIAL_ROSWELL_MASCOT_URL, CENTENNIAL_ROSWELL_URL

VARSITY_BASEBALL_SUBSCRIPTION = {
    CONF_SPORT: "Baseball",
    CONF_GENDER: "Boys",
    CONF_LEVEL: "Varsity",
}

THREE_PROGRAM_SUBSCRIPTIONS = [
    FOOTBALL_SUBSCRIPTION,
    VARSITY_BASEBALL_SUBSCRIPTION,
    FRESHMAN_BASEBALL_SUBSCRIPTION,
]


def _game(
    *,
    game_id: str,
    when: datetime,
    status: GameStatus,
    opponent: str = "Opponent",
) -> Game:
    return Game(
        id=game_id,
        date=when,
        status=status,
        team_name="Centennial",
        opponent_name=opponent,
        home_away=HomeAway.HOME,
    )


def _term_with_games(
    team_season: TeamSeason,
    games: list[Game],
    *,
    status: TermRefreshStatus = TermRefreshStatus.REFRESHED,
) -> TermSnapshot:
    return TermSnapshot(
        team_season=team_season,
        schedule=Schedule(team_season=team_season, games=games),
        status=status,
        error_type=None,
        error_message=None,
        last_success_at=datetime(2026, 9, 2, 12, 0, 0),
    )


def _program_snapshot(
    *,
    sport: str,
    gender: str,
    level: str,
    terms: tuple[TermSnapshot, ...],
    resolution_status: ProgramResolutionStatus = ProgramResolutionStatus.RESOLVED,
) -> ProgramSnapshot:
    return ProgramSnapshot(
        sport=sport,
        gender=gender,
        level=level,
        resolution_status=resolution_status,
        terms=terms,
    )


@pytest.fixture
async def three_program_entry(
    hass,
    enable_custom_integrations,
    coordinator_client,
    frozen_applicable_date,
):
    entry = centennial_entry(THREE_PROGRAM_SUBSCRIPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


def _sensor_entities(hass, entry):
    registry = er.async_get(hass)
    return [
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "sensor"
    ]


@pytest.mark.asyncio
async def test_three_programs_create_three_sensors(three_program_entry, hass) -> None:
    entities = _sensor_entities(hass, three_program_entry)
    assert len(entities) == 3

    unique_ids = {entity.unique_id for entity in entities}
    assert unique_ids == {
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Baseball",
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball",
    }


@pytest.mark.asyncio
async def test_device_identifiers_and_school_configuration_url(
    three_program_entry, hass
) -> None:
    device_registry = dr.async_get(hass)
    device = async_get_device_for_config_entry(
        device_registry,
        (DOMAIN, CENTENNIAL_ROSWELL_ID),
        three_program_entry.entry_id,
    )
    assert device is not None
    assert device.name == "Centennial"
    assert str(device.configuration_url) == CENTENNIAL_ROSWELL_URL

    for entity in _sensor_entities(hass, three_program_entry):
        assert entity.device_id == device.id


@pytest.mark.asyncio
async def test_unique_id_excludes_provider_churn_fields(three_program_entry, hass) -> None:
    freshman = next(
        entity
        for entity in _sensor_entities(hass, three_program_entry)
        if entity.unique_id.endswith(":Freshman:Baseball")
    )
    forbidden = (
        FRESHMAN_BASEBALL_FALL_ID,
        FRESHMAN_BASEBALL_SPRING_ID,
        "Fall",
        "Spring",
        "26-27",
        "freshman/fall",
        "freshman/",
    )
    for token in forbidden:
        assert token not in freshman.unique_id


@pytest.mark.asyncio
async def test_freshman_baseball_unique_id_stable_after_term_metadata_refresh(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    entry = centennial_entry([FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    transport = CoordinatorTestTransport()
    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=__import__(
            "custom_components.high_school_sports_scores.async_client", fromlist=["AsyncMaxPrepsClient"]
        ).AsyncMaxPrepsClient(transport),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities_before = _sensor_entities(hass, entry)
    assert len(entities_before) == 1
    unique_id_before = entities_before[0].unique_id

    coordinator = entry.runtime_data
    program = coordinator.data.programs[0]
    mutated_terms = []
    for index, term in enumerate(program.terms):
        team_season = term.team_season
        assert team_season is not None
        mutated_terms.append(
            TermSnapshot(
                team_season=TeamSeason(
                    school_id=team_season.school_id,
                    sport_season_id=f"mutated-ssid-{index}",
                    canonical_url=f"https://example.com/mutated-{index}/",
                    sport=team_season.sport,
                    gender=team_season.gender,
                    level=team_season.level,
                    year="99-00",
                    season="Winter" if index == 0 else "Summer",
                ),
                schedule=term.schedule,
                status=term.status,
                error_type=term.error_type,
                error_message=term.error_message,
                last_success_at=term.last_success_at,
            )
        )
    coordinator.data = coordinator.data.__class__(
        school=coordinator.data.school,
        applicable_school_year=coordinator.data.applicable_school_year,
        programs=(
            ProgramSnapshot(
                sport=program.sport,
                gender=program.gender,
                level=program.level,
                resolution_status=program.resolution_status,
                terms=tuple(mutated_terms),
            ),
        ),
        refreshed_at=coordinator.data.refreshed_at,
    )
    coordinator.async_update_listeners()

    entities_after = _sensor_entities(hass, entry)
    assert len(entities_after) == 1
    assert entities_after[0].unique_id == unique_id_before
    assert entities_after[0].unique_id == (
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball"
    )


def _state_for_unique_id(hass, entry, unique_id: str):
    entity = next(
        item for item in _sensor_entities(hass, entry) if item.unique_id == unique_id
    )
    state = hass.states.get(entity.entity_id)
    assert state is not None
    return state


@pytest.mark.asyncio
async def test_state_is_compact_not_schedule_json(three_program_entry, hass) -> None:
    state = _state_for_unique_id(
        hass,
        three_program_entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert state is not None
    assert state.state in {"scheduled", "final", "unknown"}
    with pytest.raises(json.JSONDecodeError):
        json.loads(state.state)


@pytest.mark.asyncio
async def test_football_last_and_next_from_fixture(three_program_entry, hass) -> None:
    state = _state_for_unique_id(
        hass,
        three_program_entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert state is not None
    assert state.state == "scheduled"

    last_game = state.attributes["last_game"]
    next_game = state.attributes["next_game"]
    assert last_game["status"] == "final"
    assert next_game["status"] == "scheduled"
    assert "T" in last_game["date"] and "+" not in last_game["date"]
    assert "T" in next_game["date"] and "+" not in next_game["date"]
    assert datetime.fromisoformat(last_game["date"]) < datetime.fromisoformat(
        next_game["date"]
    )


def test_last_game_is_latest_final_across_terms() -> None:
    fall = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="fall-id",
        canonical_url="https://example.com/fall/",
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        year="26-27",
        season="Fall",
    )
    spring = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="spring-id",
        canonical_url="https://example.com/spring/",
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        year="26-27",
        season="Spring",
    )
    program = _program_snapshot(
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        terms=(
            _term_with_games(
                fall,
                [_game(game_id="fall-final", when=datetime(2026, 3, 1), status=GameStatus.FINAL)],
            ),
            _term_with_games(
                spring,
                [
                    _game(
                        game_id="spring-final",
                        when=datetime(2026, 5, 1),
                        status=GameStatus.FINAL,
                    )
                ],
            ),
        ),
    )

    last = find_last_game(program)
    assert last is not None
    assert last.game.id == "spring-final"
    assert last.season == "Spring"


def test_next_game_is_earliest_scheduled_across_terms() -> None:
    fall = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="fall-id",
        canonical_url="https://example.com/fall/",
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        year="26-27",
        season="Fall",
    )
    spring = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="spring-id",
        canonical_url="https://example.com/spring/",
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        year="26-27",
        season="Spring",
    )
    program = _program_snapshot(
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        terms=(
            _term_with_games(
                fall,
                [
                    _game(
                        game_id="fall-next",
                        when=datetime(2026, 2, 1),
                        status=GameStatus.SCHEDULED,
                    )
                ],
            ),
            _term_with_games(
                spring,
                [
                    _game(
                        game_id="spring-next",
                        when=datetime(2026, 4, 1),
                        status=GameStatus.SCHEDULED,
                    )
                ],
            ),
        ),
    )

    nxt = find_next_game(program)
    assert nxt is not None
    assert nxt.game.id == "fall-next"
    assert nxt.season == "Fall"


def test_deleted_games_never_participate() -> None:
    team_season = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="one-id",
        canonical_url="https://example.com/one/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
    )
    program = _program_snapshot(
        sport="Football",
        gender="Boys",
        level="Varsity",
        terms=(
            _term_with_games(
                team_season,
                [
                    _game(
                        game_id="deleted",
                        when=datetime(2099, 1, 1),
                        status=GameStatus.DELETED,
                    ),
                    _game(
                        game_id="final",
                        when=datetime(2026, 1, 1),
                        status=GameStatus.FINAL,
                    ),
                ],
            ),
        ),
    )

    assert [ref.game.id for ref in iter_program_games(program)] == ["final"]
    assert find_last_game(program).game.id == "final"


def test_unknown_status_not_used_for_last_or_next() -> None:
    team_season = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="one-id",
        canonical_url="https://example.com/one/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
    )
    program = _program_snapshot(
        sport="Football",
        gender="Boys",
        level="Varsity",
        terms=(
            _term_with_games(
                team_season,
                [
                    _game(
                        game_id="unknown-only",
                        when=datetime(2020, 1, 1),
                        status=GameStatus.UNKNOWN,
                    )
                ],
            ),
        ),
    )

    assert find_last_game(program) is None
    assert find_next_game(program) is None
    assert program_native_value(program) == "unknown"


def test_scheduled_past_date_still_next_without_wall_clock() -> None:
    """Provider-naive ordering only; scheduled games are not filtered by ``now()``."""
    team_season = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="one-id",
        canonical_url="https://example.com/one/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
    )
    program = _program_snapshot(
        sport="Football",
        gender="Boys",
        level="Varsity",
        terms=(
            _term_with_games(
                team_season,
                [
                    _game(
                        game_id="past-scheduled",
                        when=datetime(2000, 1, 1),
                        status=GameStatus.SCHEDULED,
                    ),
                    _game(
                        game_id="older-final",
                        when=datetime(1999, 1, 1),
                        status=GameStatus.FINAL,
                    ),
                ],
            ),
        ),
    )

    nxt = find_next_game(program)
    assert nxt is not None
    assert nxt.game.id == "past-scheduled"
    assert program_native_value(program) == "scheduled"


@pytest.mark.asyncio
async def test_unresolved_program_sensor_unavailable(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    entry = centennial_entry([UNRESOLVED_SUBSCRIPTION])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entities = _sensor_entities(hass, entry)
    assert len(entities) == 1
    state = hass.states.get(entities[0].entity_id)
    assert state.state == "unavailable"


@pytest.mark.asyncio
async def test_whole_freshman_program_failure_leaves_football_available(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    from custom_components.high_school_sports_scores.async_client import AsyncMaxPrepsClient
    from tests.test_coordinator import (
        FRESHMAN_BASEBALL_FALL_SCHEDULE_URL,
        FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
    )

    transport = CoordinatorTestTransport(
        fail_urls=frozenset(
            {
                FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
                FRESHMAN_BASEBALL_FALL_SCHEDULE_URL,
            }
        )
    )
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=AsyncMaxPrepsClient(transport),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entities = _sensor_entities(hass, entry)
    assert len(entities) == 2

    football_state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    freshman_state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball",
    )
    assert football_state.state in {"scheduled", "final", "unknown"}
    assert freshman_state.state == "unavailable"


@pytest.mark.asyncio
async def test_one_freshman_term_error_keeps_entity_and_football_available(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    from custom_components.high_school_sports_scores.async_client import AsyncMaxPrepsClient
    from tests.test_coordinator import FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL

    transport = CoordinatorTestTransport(
        fail_urls=frozenset({FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL})
    )
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)
    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=AsyncMaxPrepsClient(transport),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entities = _sensor_entities(hass, entry)
    assert len(entities) == 2
    freshman = next(
        entity for entity in entities if entity.unique_id.endswith(":Freshman:Baseball")
    )
    assert freshman.unique_id == f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball"

    freshman_state = hass.states.get(freshman.entity_id)
    football_state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert freshman_state.state != "unavailable"
    assert football_state.state != "unavailable"


def test_program_unique_id_formula() -> None:
    program = ProgramSnapshot(
        sport="Baseball",
        gender="Boys",
        level="Freshman",
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=(),
    )
    assert program_unique_id(CENTENNIAL_ROSWELL_ID, program) == (
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball"
    )


def test_unresolved_program_not_available() -> None:
    program = ProgramSnapshot(
        sport="Football",
        gender="Girls",
        level="Varsity",
        resolution_status=ProgramResolutionStatus.UNRESOLVED,
        terms=(),
    )
    assert program_is_available(program) is False


@pytest.mark.asyncio
async def test_stale_last_good_term_keeps_sensor_available(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Stale retained last-good schedule data keeps the program sensor available."""
    from custom_components.high_school_sports_scores.async_client import AsyncMaxPrepsClient

    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.high_school_sports_scores.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        failing_transport = CoordinatorTestTransport(
            fail_urls=frozenset({FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL})
        )
        failing_client = AsyncMaxPrepsClient(failing_transport)
        with patch(
            "custom_components.high_school_sports_scores.client_factory.create_async_client",
            return_value=failing_client,
        ):
            await entry.runtime_data.async_refresh()
            await hass.async_block_till_done()

    entities = _sensor_entities(hass, entry)
    assert len(entities) == 1
    state = hass.states.get(entities[0].entity_id)
    assert state.state != "unavailable"


@pytest.mark.asyncio
async def test_football_attributes_include_attribution(three_program_entry, hass) -> None:
    state = _state_for_unique_id(
        hass,
        three_program_entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert state.attributes["attribution"] == ATTRIBUTION


@pytest.mark.asyncio
async def test_program_sensors_share_school_entity_picture_from_mascot_url(
    three_program_entry, hass
) -> None:
    pictures = [
        hass.states.get(entity.entity_id).attributes.get("entity_picture")
        for entity in _sensor_entities(hass, three_program_entry)
    ]
    assert len(pictures) == 3
    assert all(picture == CENTENNIAL_ROSWELL_MASCOT_URL for picture in pictures)
    assert CENTENNIAL_ROSWELL_ID in CENTENNIAL_ROSWELL_MASCOT_URL


@pytest.mark.asyncio
async def test_entity_picture_uses_schedule_team_logo_without_entry_mascot_url(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CENTENNIAL_ROSWELL_ID,
        data={
            "school_id": CENTENNIAL_ROSWELL_ID,
            "canonical_url": CENTENNIAL_ROSWELL_URL,
            "name": "Centennial",
        },
        options={"subscriptions": [FOOTBALL_SUBSCRIPTION]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    picture = state.attributes.get("entity_picture")
    assert picture is not None
    assert CENTENNIAL_ROSWELL_ID in picture
    assert state.state != "unavailable"


@pytest.mark.asyncio
async def test_user_logo_override_wins_over_automatic_mascot_url(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    override = "/local/centennial-knights.png"
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CENTENNIAL_ROSWELL_ID,
        data={
            "school_id": CENTENNIAL_ROSWELL_ID,
            "canonical_url": CENTENNIAL_ROSWELL_URL,
            "name": "Centennial",
            CONF_MASCOT_URL: CENTENNIAL_ROSWELL_MASCOT_URL,
        },
        options={
            "subscriptions": [FOOTBALL_SUBSCRIPTION],
            CONF_SCHOOL_LOGO_OVERRIDE: override,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert state.attributes.get("entity_picture") == override


@pytest.mark.asyncio
async def test_sensors_available_without_any_logo_sources(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CENTENNIAL_ROSWELL_ID,
        data={
            "school_id": CENTENNIAL_ROSWELL_ID,
            "canonical_url": CENTENNIAL_ROSWELL_URL,
            "name": "Centennial",
        },
        options={"subscriptions": [FOOTBALL_SUBSCRIPTION]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data
    stripped_programs = []
    for program in coordinator.data.programs:
        stripped_terms = []
        for term in program.terms:
            if term.schedule is None:
                stripped_terms.append(term)
                continue
            team_season = term.schedule.team_season
            stripped_terms.append(
                TermSnapshot(
                    team_season=term.team_season,
                    schedule=Schedule(team_season=team_season, games=term.schedule.games),
                    status=term.status,
                    error_type=term.error_type,
                    error_message=term.error_message,
                    last_success_at=term.last_success_at,
                )
            )
        stripped_programs.append(
            ProgramSnapshot(
                sport=program.sport,
                gender=program.gender,
                level=program.level,
                resolution_status=program.resolution_status,
                terms=tuple(stripped_terms),
            )
        )
    coordinator.data = coordinator.data.__class__(
        school=coordinator.data.school.__class__(
            school_id=coordinator.data.school.school_id,
            canonical_url=coordinator.data.school.canonical_url,
            name=coordinator.data.school.name,
        ),
        applicable_school_year=coordinator.data.applicable_school_year,
        programs=tuple(stripped_programs),
        refreshed_at=coordinator.data.refreshed_at,
    )
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert state.attributes.get("entity_picture") is None
    assert state.state != "unavailable"


@pytest.mark.asyncio
async def test_user_override_applies_when_no_automatic_logo_sources(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    override = "https://example.com/fallback-school.png"
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CENTENNIAL_ROSWELL_ID,
        data={
            "school_id": CENTENNIAL_ROSWELL_ID,
            "canonical_url": CENTENNIAL_ROSWELL_URL,
            "name": "Centennial",
        },
        options={
            "subscriptions": [FOOTBALL_SUBSCRIPTION],
            CONF_SCHOOL_LOGO_OVERRIDE: override,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data
    stripped_programs = []
    for program in coordinator.data.programs:
        stripped_terms = []
        for term in program.terms:
            if term.schedule is None:
                stripped_terms.append(term)
                continue
            team_season = term.schedule.team_season
            stripped_terms.append(
                TermSnapshot(
                    team_season=term.team_season,
                    schedule=Schedule(team_season=team_season, games=term.schedule.games),
                    status=term.status,
                    error_type=term.error_type,
                    error_message=term.error_message,
                    last_success_at=term.last_success_at,
                )
            )
        stripped_programs.append(
            ProgramSnapshot(
                sport=program.sport,
                gender=program.gender,
                level=program.level,
                resolution_status=program.resolution_status,
                terms=tuple(stripped_terms),
            )
        )
    coordinator.data = coordinator.data.__class__(
        school=coordinator.data.school.__class__(
            school_id=coordinator.data.school.school_id,
            canonical_url=coordinator.data.school.canonical_url,
            name=coordinator.data.school.name,
        ),
        applicable_school_year=coordinator.data.applicable_school_year,
        programs=tuple(stripped_programs),
        refreshed_at=coordinator.data.refreshed_at,
    )
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    state = _state_for_unique_id(
        hass,
        entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    assert state.attributes.get("entity_picture") == override
    assert state.state != "unavailable"


@pytest.mark.asyncio
async def test_football_game_attributes_include_opponent_logo(three_program_entry, hass) -> None:
    state = _state_for_unique_id(
        hass,
        three_program_entry,
        f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football",
    )
    next_game = state.attributes["next_game"]
    assert next_game["opponent_name"] == "Alpharetta"
    assert next_game["opponent_logo"].startswith("https://")
    assert "6b615161-19a6-4148-aa21-ce63ffd5a68f" in next_game["opponent_logo"]


def test_game_attribute_includes_opponent_logo_when_present() -> None:
    from custom_components.high_school_sports_scores.program_sensor import ProgramGameRef

    game = Game(
        id="g1",
        date=datetime(2026, 1, 1),
        status=GameStatus.SCHEDULED,
        team_name="Centennial",
        opponent_name="Alpharetta",
        home_away=HomeAway.HOME,
        opponent_logo="https://example.com/opponent.gif",
    )
    data = game_attribute(ProgramGameRef(game=game, season="Fall"))
    assert data["opponent_logo"] == "https://example.com/opponent.gif"
