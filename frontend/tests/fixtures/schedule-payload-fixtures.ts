import type { GameAttribute, ProgramSchedulePayload } from "../../src/types";
import {
  FOOTBALL_ENTITY_ID,
  FOOTBALL_PROGRAM_ATTRIBUTES,
} from "./football-program-state";

function footballGame(
  overrides: Partial<GameAttribute> & Pick<GameAttribute, "id" | "date" | "opponent_name">,
): GameAttribute {
  return {
    status: "scheduled",
    home_away: "home",
    season: "Fall",
    ...overrides,
  };
}

const FOOTBALL_GAMES: GameAttribute[] = [
  footballGame({
    id: "game-1",
    date: "2026-08-21T19:30:00",
    opponent_name: "Roswell",
    status: "final",
    team_score: 21,
    opponent_score: 14,
    result: "W",
  }),
  footballGame({
    id: "6f7a550c-040a-4f1c-824e-3d0d3b873cef",
    date: "2026-08-28T19:30:00",
    opponent_name: "Johns Creek",
    status: "final",
    team_score: 54,
    opponent_score: 18,
    result: "W",
  }),
  footballGame({
    id: "30b79240-4c41-4e25-b850-0052d1221fbd",
    date: "2026-09-04T19:30:00",
    opponent_name: "Alpharetta",
    status: "scheduled",
  }),
  footballGame({
    id: "game-4",
    date: "2026-09-11T19:30:00",
    opponent_name: "Cambridge",
    status: "scheduled",
  }),
];

export const FOOTBALL_SCHEDULE_PAYLOAD: ProgramSchedulePayload = {
  schema_version: 1,
  entity_id: FOOTBALL_ENTITY_ID,
  school_id: FOOTBALL_PROGRAM_ATTRIBUTES.school_id!,
  school_name: FOOTBALL_PROGRAM_ATTRIBUTES.school_name!,
  applicable_school_year: "26-27",
  sport: "Football",
  gender: "Boys",
  level: "Varsity",
  display_label: "Boys Varsity Football",
  resolution_status: "resolved",
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "refreshed",
      games: FOOTBALL_GAMES,
    },
  ],
};

export const FOOTBALL_EMPTY_SCHEDULE_PAYLOAD: ProgramSchedulePayload = {
  ...FOOTBALL_SCHEDULE_PAYLOAD,
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "refreshed",
      games: [],
    },
  ],
};

export const FOOTBALL_UNRESOLVED_SCHEDULE_PAYLOAD: ProgramSchedulePayload = {
  ...FOOTBALL_SCHEDULE_PAYLOAD,
  resolution_status: "unresolved",
  terms: [],
};

/** Rollover retention: prior-year games while waiting for applicable year (case A). */
export const FOOTBALL_WAITING_WITH_GAMES_PAYLOAD: ProgramSchedulePayload = {
  ...FOOTBALL_SCHEDULE_PAYLOAD,
  applicable_school_year: "27-28",
  resolution_status: "waiting_for_applicable_year",
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "stale",
      games: FOOTBALL_GAMES,
    },
  ],
};

export const FOOTBALL_WAITING_EMPTY_PAYLOAD: ProgramSchedulePayload = {
  ...FOOTBALL_WAITING_WITH_GAMES_PAYLOAD,
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "stale",
      games: [],
    },
  ],
};

/** Last-good after fetch failure (case B). */
export const FOOTBALL_STALE_RESOLVED_PAYLOAD: ProgramSchedulePayload = {
  ...FOOTBALL_SCHEDULE_PAYLOAD,
  resolution_status: "resolved",
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "stale",
      games: FOOTBALL_GAMES,
    },
  ],
};

const FRESHMAN_FALL_GAMES: GameAttribute[] = [
  {
    id: "fall-game-1",
    date: "2026-09-10T16:00:00",
    status: "scheduled",
    opponent_name: "Chattahoochee",
    home_away: "away",
    season: "Fall",
  },
  {
    id: "fall-game-2",
    date: "2026-09-17T16:00:00",
    status: "scheduled",
    opponent_name: "Northview",
    home_away: "home",
    season: "Fall",
  },
];

const FRESHMAN_SPRING_GAMES: GameAttribute[] = [
  {
    id: "spring-game-1",
    date: "2027-03-05T16:00:00",
    status: "scheduled",
    opponent_name: "Lassiter",
    home_away: "home",
    season: "Spring",
  },
];

/** Backend DTO order: Fall before Spring (not sport-seasons encounter order). */
export const FRESHMAN_SCHEDULE_PAYLOAD: ProgramSchedulePayload = {
  schema_version: 1,
  entity_id: "sensor.centennial_boys_freshman_baseball",
  school_id: FOOTBALL_PROGRAM_ATTRIBUTES.school_id!,
  school_name: FOOTBALL_PROGRAM_ATTRIBUTES.school_name!,
  applicable_school_year: "26-27",
  sport: "Baseball",
  gender: "Boys",
  level: "Freshman",
  display_label: "Boys Freshman Baseball",
  resolution_status: "resolved",
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "refreshed",
      games: FRESHMAN_FALL_GAMES,
    },
    {
      season: "Spring",
      year: "26-27",
      status: "refreshed",
      games: FRESHMAN_SPRING_GAMES,
    },
  ],
};

/** Mixed refreshed + stale terms under resolved (case B, notice once). */
export const FOOTBALL_MIXED_STALE_RESOLVED_PAYLOAD: ProgramSchedulePayload = {
  ...FRESHMAN_SCHEDULE_PAYLOAD,
  resolution_status: "resolved",
  terms: [
    {
      season: "Fall",
      year: "26-27",
      status: "refreshed",
      games: FRESHMAN_FALL_GAMES,
    },
    {
      season: "Spring",
      year: "26-27",
      status: "stale",
      games: FRESHMAN_SPRING_GAMES,
    },
  ],
};

/** Deliberately Spring-first to prove the card does not resort client-side. */
export const FRESHMAN_SPRING_FIRST_PAYLOAD: ProgramSchedulePayload = {
  ...FRESHMAN_SCHEDULE_PAYLOAD,
  terms: [...FRESHMAN_SCHEDULE_PAYLOAD.terms].reverse(),
};
