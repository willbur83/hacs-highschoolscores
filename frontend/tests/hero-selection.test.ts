import { describe, expect, it } from "vitest";

import { naiveIsoToLocalMs, selectHeroGame } from "../src/hero-selection";
import type { GameAttribute } from "../src/types";
import { FOOTBALL_PROGRAM_ATTRIBUTES } from "./fixtures/football-program-state";

const lastGame = FOOTBALL_PROGRAM_ATTRIBUTES.last_game as GameAttribute;
const nextGame = FOOTBALL_PROGRAM_ATTRIBUTES.next_game as GameAttribute;

function localDate(
  year: number,
  month: number,
  day: number,
  hour = 12,
  minute = 0,
): Date {
  return new Date(year, month - 1, day, hour, minute, 0);
}

describe("selectHeroGame", () => {
  it("chooses last_game when it is temporally closer to now", () => {
    const now = localDate(2026, 8, 30);
    const selection = selectHeroGame(lastGame, nextGame, now);
    expect(selection?.heroRole).toBe("last");
    expect(selection?.hero.opponent_name).toBe("Johns Creek");
    expect(selection?.secondaryRole).toBe("next");
  });

  it("chooses next_game once it becomes temporally closer", () => {
    const now = localDate(2026, 9, 2);
    const selection = selectHeroGame(lastGame, nextGame, now);
    expect(selection?.heroRole).toBe("next");
    expect(selection?.hero.opponent_name).toBe("Alpharetta");
    expect(selection?.secondaryRole).toBe("last");
  });

  it("handles football-like wide gaps naturally", () => {
    const now = localDate(2026, 9, 1);
    const selection = selectHeroGame(lastGame, nextGame, now);
    expect(selection?.heroRole).toBe("next");
  });

  it("handles basketball-like short intervals naturally", () => {
    const shortLast: GameAttribute = {
      ...lastGame,
      id: "short-last",
      date: "2026-09-08T19:00:00",
      opponent_name: "Northview",
    };
    const shortNext: GameAttribute = {
      ...nextGame,
      id: "short-next",
      date: "2026-09-10T19:00:00",
      opponent_name: "Southview",
    };
    const now = localDate(2026, 9, 9);
    const selection = selectHeroGame(shortLast, shortNext, now);
    expect(selection?.heroRole).toBe("last");
    const later = localDate(2026, 9, 9, 19, 1);
    const laterSelection = selectHeroGame(shortLast, shortNext, later);
    expect(laterSelection?.heroRole).toBe("next");
  });

  it("uses only last_game when next is absent", () => {
    const selection = selectHeroGame(lastGame, undefined, localDate(2026, 9, 9));
    expect(selection?.heroRole).toBe("last");
    expect(selection?.secondary).toBeNull();
  });

  it("uses only next_game when last is absent", () => {
    const selection = selectHeroGame(undefined, nextGame, localDate(2026, 9, 9));
    expect(selection?.heroRole).toBe("next");
    expect(selection?.secondary).toBeNull();
  });

  it("prefers last_game when distances are exactly equal", () => {
    const equalLast: GameAttribute = {
      ...lastGame,
      date: "2026-09-09T18:00:00",
    };
    const equalNext: GameAttribute = {
      ...nextGame,
      date: "2026-09-11T18:00:00",
    };
    const now = localDate(2026, 9, 10, 18, 0);
    const selection = selectHeroGame(equalLast, equalNext, now);
    expect(selection?.heroRole).toBe("last");
  });

  it("prefers the valid-dated game when the other date is malformed", () => {
    const badLast: GameAttribute = { ...lastGame, date: "not-a-date" };
    const selection = selectHeroGame(badLast, nextGame, localDate(2026, 9, 9));
    expect(selection?.heroRole).toBe("next");

    const badNext: GameAttribute = { ...nextGame, date: "2026-13-40T99:99:99" };
    const other = selectHeroGame(lastGame, badNext, localDate(2026, 9, 9));
    expect(other?.heroRole).toBe("last");
  });

  it("falls back deterministically when both dates are malformed", () => {
    const badLast: GameAttribute = { ...lastGame, date: "" };
    const badNext: GameAttribute = { ...nextGame, date: "bad" };
    const selection = selectHeroGame(badLast, badNext, localDate(2026, 9, 9));
    expect(selection?.heroRole).toBe("last");
    expect(selection?.secondaryRole).toBe("next");
  });

  it("returns null when neither game exists", () => {
    expect(selectHeroGame(undefined, undefined, localDate(2026, 9, 9))).toBeNull();
  });
});

describe("naiveIsoToLocalMs", () => {
  it("rejects timezone-qualified strings", () => {
    expect(naiveIsoToLocalMs("2026-09-04T19:30:00Z")).toBeNull();
    expect(naiveIsoToLocalMs("2026-09-04T19:30:00-04:00")).toBeNull();
  });
});
