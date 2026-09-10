import { describe, expect, it } from "vitest";

import {
  buildSecondaryStripContent,
  formatCardDateLine,
} from "../src/card-helpers";
import { FOOTBALL_PROGRAM_ATTRIBUTES } from "./fixtures/football-program-state";

describe("formatCardDateLine", () => {
  it("formats a single row without year", () => {
    expect(formatCardDateLine("2026-09-04T19:30:00")).toBe(
      "FRIDAY - Sep 4 - 7:30 PM",
    );
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
    expect(strip.dateLine).toBe("FRIDAY - Aug 28 - 7:30 PM");
  });

  it("uses at for an away game next summary", () => {
    const awayNext = {
      ...FOOTBALL_PROGRAM_ATTRIBUTES.next_game,
      home_away: "away",
      opponent_name: "South Forsyth",
    };
    const strip = buildSecondaryStripContent("next", awayNext);
    expect(strip.highlight).toBe("at South Forsyth");
    expect(strip.dateLine).toBe("FRIDAY - Sep 4 - 7:30 PM");
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
