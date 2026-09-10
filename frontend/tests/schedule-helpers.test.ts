import { describe, expect, it } from "vitest";

import {
  classifySchedulePayload,
  deriveVenueRecordBreakdown,
  formatScheduleMonthDay,
  formatScheduleResultColumn,
  resolveScheduleNotice,
  scheduleRowDateContainsWeekday,
} from "../src/schedule-helpers";
import type { GameAttribute, ProgramSchedulePayload } from "../src/types";
import {
  FOOTBALL_MIXED_STALE_RESOLVED_PAYLOAD,
  FOOTBALL_SCHEDULE_PAYLOAD,
  FOOTBALL_STALE_RESOLVED_PAYLOAD,
  FOOTBALL_WAITING_EMPTY_PAYLOAD,
  FOOTBALL_WAITING_WITH_GAMES_PAYLOAD,
} from "./fixtures/schedule-payload-fixtures";

function payloadWithGames(games: GameAttribute[]): ProgramSchedulePayload {
  return {
    schema_version: 1,
    entity_id: "sensor.test",
    school_id: "school",
    school_name: "Test",
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
        games,
      },
    ],
  };
}

describe("schedule-helpers", () => {
  it("formats compact month/day without weekday or year", () => {
    expect(formatScheduleMonthDay("2026-09-11T19:30:00")).toBe("Sep 11");
    expect(scheduleRowDateContainsWeekday("Sep 11")).toBe(false);
  });

  it("derives venue breakdown only from classified final games", () => {
    const payload = payloadWithGames([
      {
        id: "home-win",
        date: "2026-08-28T19:30:00",
        status: "final",
        opponent_name: "Johns Creek",
        home_away: "home",
        team_score: 54,
        opponent_score: 18,
        result: "W",
      },
      {
        id: "away-loss",
        date: "2026-09-01T19:30:00",
        status: "final",
        opponent_name: "Roswell",
        home_away: "away",
        team_score: 10,
        opponent_score: 14,
        result: "L",
      },
      {
        id: "scheduled",
        date: "2026-09-04T19:30:00",
        status: "scheduled",
        opponent_name: "Alpharetta",
        home_away: "home",
      },
    ]);

    expect(deriveVenueRecordBreakdown(payload)).toBe("Home 1-0 | Away 0-1");
  });

  it("omits breakdown when no usable final games exist", () => {
    const payload = payloadWithGames([
      {
        id: "missing-result",
        date: "2026-08-28T19:30:00",
        status: "final",
        opponent_name: "Johns Creek",
        home_away: "home",
        team_score: 54,
        opponent_score: 18,
      },
      {
        id: "scheduled",
        date: "2026-09-04T19:30:00",
        status: "scheduled",
        opponent_name: "Alpharetta",
        home_away: "home",
      },
    ]);

    expect(deriveVenueRecordBreakdown(payload)).toBeNull();
  });

  it("keeps scheduled result time separate from the date cell", () => {
    const game: GameAttribute = {
      id: "next",
      date: "2026-09-04T19:30:00",
      status: "scheduled",
      opponent_name: "Alpharetta",
      home_away: "home",
    };

    expect(formatScheduleMonthDay(game.date)).toBe("Sep 4");
    expect(formatScheduleResultColumn(game)).toBe("7:30 PM");
  });

  it("classifies waiting with zero games as waiting, not ready", () => {
    const body = classifySchedulePayload(FOOTBALL_WAITING_EMPTY_PAYLOAD);
    expect(body.kind).toBe("waiting");
    expect(resolveScheduleNotice(FOOTBALL_WAITING_EMPTY_PAYLOAD)).toBeNull();
  });

  it("returns rollover notice for waiting_for_applicable_year with retained games", () => {
    const notice = resolveScheduleNotice(FOOTBALL_WAITING_WITH_GAMES_PAYLOAD);
    expect(notice?.kind).toBe("rollover");
    expect(notice?.message).toContain("27-28");
    expect(notice?.message).not.toContain("Schedule refresh failed");
    expect(classifySchedulePayload(FOOTBALL_WAITING_WITH_GAMES_PAYLOAD).kind).toBe("ready");
  });

  it("returns stale-last-good notice for resolved payload with stale term games", () => {
    const notice = resolveScheduleNotice(FOOTBALL_STALE_RESOLVED_PAYLOAD);
    expect(notice?.kind).toBe("stale-last-good");
    expect(notice?.message).toContain("Schedule refresh failed");
    expect(notice?.message).not.toContain("prior school-year");
  });

  it("prefers rollover notice when waiting payload also has stale terms", () => {
    const notice = resolveScheduleNotice(FOOTBALL_WAITING_WITH_GAMES_PAYLOAD);
    expect(notice?.kind).toBe("rollover");
    expect(notice?.message).not.toContain("Schedule refresh failed");
  });

  it("returns one stale-last-good notice for mixed refreshed and stale terms", () => {
    expect(resolveScheduleNotice(FOOTBALL_MIXED_STALE_RESOLVED_PAYLOAD)?.kind).toBe(
      "stale-last-good",
    );
  });

  it("returns no notice for all-refreshed resolved schedule", () => {
    expect(resolveScheduleNotice(FOOTBALL_SCHEDULE_PAYLOAD)).toBeNull();
  });
});
