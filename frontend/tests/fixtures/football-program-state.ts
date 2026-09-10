import type { HassEntityState } from "../../src/types";

/** Centennial Boys Varsity Football attributes from tests/test_sensor.py fixtures. */
export const FOOTBALL_ENTITY_ID =
  "sensor.centennial_boys_varsity_football";

export const FOOTBALL_PROGRAM_ATTRIBUTES = {
  school_id: "52dea55b-3988-4979-b5fd-20376058997f",
  school_name: "Centennial",
  sport: "Football",
  gender: "Boys",
  level: "Varsity",
  year: "26-27",
  display_label: "Boys Varsity Football",
  team_record: "2-0",
  entity_picture:
    "https://image.maxpreps.io/school-mascot/5/2/5/52dea55b-3988-4979-b5fd-20376058997f.gif?version=637514050800000000&width=1024&height=1024",
  last_game: {
    id: "6f7a550c-040a-4f1c-824e-3d0d3b873cef",
    date: "2026-08-28T19:30:00",
    status: "final",
    opponent_name: "Johns Creek",
    home_away: "home",
    opponent_id: "efadaef4-8fb1-469b-b110-218621e68254",
    team_score: 54,
    opponent_score: 18,
    result: "W",
    venue: "Centennial High School",
    game_url:
      "https://www.maxpreps.com/ga/football/game/centennial-roswell-vs-johns-creek/8-28-2026/?c=6f7a550c-040a-4f1c-824e-3d0d3b873cef",
    opponent_logo:
      "https://image.maxpreps.io/school-mascot/e/f/a/efadaef4-8fb1-469b-b110-218621e68254.gif?version=637856054400000000&width=1024&height=1024",
    season: "Fall",
  },
  next_game: {
    id: "30b79240-4c41-4e25-b850-0052d1221fbd",
    date: "2026-09-04T19:30:00",
    status: "scheduled",
    opponent_name: "Alpharetta",
    home_away: "home",
    opponent_id: "6b615161-19a6-4148-aa21-ce63ffd5a68f",
    venue: "Centennial High School",
    game_url:
      "https://www.maxpreps.com/ga/football/game/alpharetta-vs-centennial-roswell/9-4-2026/?c=30b79240-4c41-4e25-b850-0052d1221fbd",
    opponent_logo:
      "https://image.maxpreps.io/school-mascot/6/b/6/6b615161-19a6-4148-aa21-ce63ffd5a68f.gif?version=637514050800000000&width=1024&height=1024",
    season: "Fall",
  },
};

export function footballProgramState(
  overrides: Partial<HassEntityState> = {},
): HassEntityState {
  const { attributes: attributeOverrides, ...restOverrides } = overrides;
  return {
    entity_id: FOOTBALL_ENTITY_ID,
    state: "scheduled",
    attributes: {
      ...FOOTBALL_PROGRAM_ATTRIBUTES,
      ...(attributeOverrides ?? {}),
    },
    ...restOverrides,
  };
}
