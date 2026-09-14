import { describe, expect, it } from "vitest";

import {
  buildCollapsedHeaderTitle,
  buildMatchupLayout,
  buildSecondaryStripContent,
  DEFAULT_CARD_GRID_OPTIONS,
  formatCardDateLine,
  formatFinalStatusLine,
  formatMatchupVenueLabel,
  formatNextGameStrip,
  formatUpcomingStatusLine,
  hashNameToHue,
  scoreOutcomes,
  teamMonogram,
} from "../src/card-helpers";
import { FOOTBALL_PROGRAM_ATTRIBUTES } from "./fixtures/football-program-state";

describe("formatCardDateLine", () => {
  it("formats a single row without year", () => {
    expect(formatCardDateLine("2026-09-04T19:30:00")).toBe(
      "FRIDAY - Sep 4 - 7:30 PM",
    );
  });
});

describe("DEFAULT_CARD_GRID_OPTIONS", () => {
  it("uses automatic vertical sizing for Sections", () => {
    expect(DEFAULT_CARD_GRID_OPTIONS.rows).toBe("auto");
    expect(DEFAULT_CARD_GRID_OPTIONS.rows).not.toBe(5);
  });
});

describe("buildCollapsedHeaderTitle", () => {
  it("joins program and sport without the season year", () => {
    expect(buildCollapsedHeaderTitle(FOOTBALL_PROGRAM_ATTRIBUTES)).toBe(
      "Boys Varsity Football · Football",
    );
  });
});

describe("formatFinalStatusLine", () => {
  it("formats a compact final date without time", () => {
    expect(formatFinalStatusLine("2026-09-11T19:30:00")).toBe("Final · Sep 11");
  });
});

describe("formatUpcomingStatusLine", () => {
  it("formats a short weekday, month day, and time", () => {
    expect(formatUpcomingStatusLine("2026-09-18T19:30:00")).toBe(
      "Fri, Sep 18 · 7:30 PM",
    );
  });
});

describe("formatMatchupVenueLabel", () => {
  it("uses vs for home and neutral games", () => {
    expect(
      formatMatchupVenueLabel({
        ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
        home_away: "home",
      }),
    ).toBe("vs");
    expect(
      formatMatchupVenueLabel({
        ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
        home_away: "neutral",
      }),
    ).toBe("vs");
  });

  it("uses AT for away games", () => {
    expect(
      formatMatchupVenueLabel({
        ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
        home_away: "away",
      }),
    ).toBe("AT");
  });
});

describe("formatNextGameStrip", () => {
  it("joins preposition, opponent, and upcoming status", () => {
    expect(formatNextGameStrip(FOOTBALL_PROGRAM_ATTRIBUTES.next_game)).toBe(
      "vs Alpharetta · Fri, Sep 4 · 7:30 PM",
    );
  });

  it("uses at for an away next game", () => {
    expect(
      formatNextGameStrip({
        ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
        home_away: "away",
        opponent_name: "Cambridge",
      }),
    ).toBe("at Cambridge · Fri, Sep 4 · 7:30 PM");
  });
});

describe("scoreOutcomes", () => {
  it("dims the losing score and treats a tie as full opacity", () => {
    const layout = buildMatchupLayout(
      FOOTBALL_PROGRAM_ATTRIBUTES,
      FOOTBALL_PROGRAM_ATTRIBUTES.last_game,
    );
    expect(scoreOutcomes(layout)).toEqual({ away: "lose", home: "win" });
    expect(
      scoreOutcomes({
        away: { displayName: "A", score: 21 },
        home: { displayName: "B", score: 21 },
      }),
    ).toEqual({ away: "tie", home: "tie" });
  });
});

describe("teamMonogram", () => {
  it("uses the first initial and a stable hue", () => {
    const mono = teamMonogram("Johns Creek");
    expect(mono.initial).toBe("J");
    expect(mono.hue).toBe(hashNameToHue("Johns Creek"));
    expect(mono.hue).toBeGreaterThanOrEqual(0);
    expect(mono.hue).toBeLessThan(360);
    expect(teamMonogram("").initial).toBe("?");
  });
});

describe("buildSecondaryStripContent", () => {
  it("uses vs for a home game last result", () => {
    const strip = buildSecondaryStripContent(
      "last",
      FOOTBALL_PROGRAM_ATTRIBUTES.last_game,
    );
    expect(strip.label).toBe("Last");
    expect(strip.highlight).toBe("W 54-18 vs Johns Creek");
    expect(strip.dateLine).toBe("Fri, Aug 28 · 7:30 PM");
  });

  it("uses at for an away game next summary", () => {
    const awayNext = {
      ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
      home_away: "away",
      opponent_name: "South Forsyth",
    };
    const strip = buildSecondaryStripContent("next", awayNext);
    expect(strip.highlight).toBe("at South Forsyth");
    expect(strip.dateLine).toBe("Fri, Sep 4 · 7:30 PM");
  });

  it("uses vs for a neutral-site game", () => {
    const neutralNext = {
      ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
      home_away: "neutral",
      opponent_name: "Alpharetta",
    };
    const strip = buildSecondaryStripContent("next", neutralNext);
    expect(strip.highlight).toBe("vs Alpharetta");
  });
});
