import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { resolveCardMode } from "../src/card-helpers";
import { isProgramEntity } from "../src/entity-suggestion";
import { HighSchoolSportsScoresCard } from "../src/high-school-sports-scores-card";
import {
  WS_GET_PROGRAM_SCHEDULE,
  WS_SUBSCRIBE_PROGRAM_SCHEDULE_UPDATES,
} from "../src/schedule-client";
import type { HomeAssistantLike, ProgramSchedulePayload } from "../src/types";
import {
  FOOTBALL_EMPTY_SCHEDULE_PAYLOAD,
  FOOTBALL_MIXED_STALE_RESOLVED_PAYLOAD,
  FOOTBALL_SCHEDULE_PAYLOAD,
  FOOTBALL_STALE_RESOLVED_PAYLOAD,
  FOOTBALL_UNRESOLVED_SCHEDULE_PAYLOAD,
  FOOTBALL_WAITING_EMPTY_PAYLOAD,
  FOOTBALL_WAITING_WITH_GAMES_PAYLOAD,
  FRESHMAN_SCHEDULE_PAYLOAD,
  FRESHMAN_SPRING_FIRST_PAYLOAD,
} from "./fixtures/schedule-payload-fixtures";
import {
  FOOTBALL_ENTITY_ID,
  footballProgramState,
} from "./fixtures/football-program-state";

const testDir = dirname(fileURLToPath(import.meta.url));
const srcDir = resolve(testDir, "../src");

/** Minimal stand-in; must not replace children Lit assigns inside ha-card. */
class HaCardStub extends HTMLElement {}

interface MockHassOptions {
  entityId?: string;
  state?: ReturnType<typeof footballProgramState>;
  schedulePayload?: ProgramSchedulePayload;
  callWSError?: unknown;
  subscribeDelayMs?: number;
  fetchDelayMs?: number;
}

interface MockSubscription {
  callback: (message: unknown) => void;
  unsubscribe: ReturnType<typeof vi.fn>;
}

function createMockHass(options: MockHassOptions = {}) {
  const entityId = options.entityId ?? FOOTBALL_ENTITY_ID;
  const state = options.state ?? footballProgramState();
  const subscriptions: MockSubscription[] = [];

  const callWS = vi.fn(async (message: Record<string, unknown>) => {
    if (message.type === WS_GET_PROGRAM_SCHEDULE) {
      if (options.callWSError) {
        throw options.callWSError;
      }
      if (options.fetchDelayMs) {
        await new Promise((resolveDelay) => setTimeout(resolveDelay, options.fetchDelayMs));
      }
      return options.schedulePayload ?? FOOTBALL_SCHEDULE_PAYLOAD;
    }
    throw new Error(`Unexpected websocket message: ${String(message.type)}`);
  });

  const subscribeMessage = vi.fn(
    async (callback: (message: unknown) => void, message: Record<string, unknown>) => {
      expect(message.type).toBe(WS_SUBSCRIBE_PROGRAM_SCHEDULE_UPDATES);
      if (options.subscribeDelayMs) {
        await new Promise((resolveDelay) =>
          setTimeout(resolveDelay, options.subscribeDelayMs),
        );
      }
      const unsubscribe = vi.fn();
      subscriptions.push({ callback, unsubscribe });
      return unsubscribe;
    },
  );

  const hass: HomeAssistantLike = {
    states: {
      [entityId]: state,
    },
    callWS,
    connection: { subscribeMessage },
  };

  return { hass, callWS, subscriptions };
}

function createCard(
  config: { entity: string; mode?: "both" | "last_next" | "schedule" },
): HighSchoolSportsScoresCard {
  const card = new HighSchoolSportsScoresCard();
  card.setConfig(config);
  document.body.appendChild(card);
  return card;
}

async function expandCard(card: HighSchoolSportsScoresCard): Promise<void> {
  const interactive = card.shadowRoot?.querySelector(".program-card--interactive");
  interactive?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await card.updateComplete;
  await vi.waitFor(async () => {
    await card.updateComplete;
    expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();
  });
}

const FRESHMAN_ENTITY_ID = "sensor.centennial_boys_freshman_baseball";

function freshmanProgramState(
  overrides: Partial<ReturnType<typeof footballProgramState>> = {},
) {
  return footballProgramState({
    entity_id: FRESHMAN_ENTITY_ID,
    attributes: {
      sport: "Baseball",
      level: "Freshman",
      display_label: "Boys Freshman Baseball",
    },
    ...overrides,
  });
}

async function collapseCard(card: HighSchoolSportsScoresCard): Promise<void> {
  const interactive = card.shadowRoot?.querySelector(".program-card--interactive");
  interactive?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await card.updateComplete;
}

const CARD_TAG = "high-school-sports-scores-card";

describe("HighSchoolSportsScoresCard", () => {
  beforeAll(() => {
    if (!customElements.get("ha-card")) {
      customElements.define("ha-card", HaCardStub);
    }
    if (!customElements.get(CARD_TAG)) {
      customElements.define(CARD_TAG, HighSchoolSportsScoresCard);
    }
  });

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 7, 30, 12, 0, 0));
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows an error when the entity is missing", async () => {
    const card = createCard({ entity: "sensor.missing_program" });
    card.hass = { states: {} };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Entity not found");
    expect(text).toContain("sensor.missing_program");
  });

  it("shows an unavailable message when the entity is HA unavailable", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({ state: "unavailable" }),
      },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("is unavailable");
    expect(text).not.toContain("No last or next game");
    expect(card.shadowRoot?.querySelector(".chrome")).toBeNull();
  });

  it("renders collapsed chrome with empty body when compact state is unknown", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({
          state: "unknown",
          attributes: {
            last_game: undefined,
            next_game: undefined,
          },
        }),
      },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Centennial | Boys Varsity Football | 26-27");
    expect(text).toContain("Record: 2-0");
    expect(text).toContain("No last or next game is available.");
    expect(text).not.toContain("is unknown");
    expect(text).not.toContain("is unavailable");
    expect(card.shadowRoot?.querySelector(".hero")).toBeNull();
    expect(card.shadowRoot?.querySelector(".secondary-strip")).toBeNull();
  });

  it("renders last_game only without a secondary strip", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({
          attributes: { next_game: undefined },
        }),
      },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Last");
    expect(text).toContain("Johns Creek");
    expect(card.shadowRoot?.querySelector(".secondary-strip")).toBeNull();
  });

  it("renders next_game only without a secondary strip", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({
          attributes: { last_game: undefined },
        }),
      },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Next");
    expect(text).toContain("Alpharetta");
    expect(card.shadowRoot?.querySelector(".hero-score")).toBeNull();
    expect(card.shadowRoot?.querySelector(".secondary-strip")).toBeNull();
  });

  it("hides record when team_record is absent", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({
          attributes: { team_record: undefined },
        }),
      },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).not.toContain("Record:");
  });

  it("does not invent scores on a final hero when scores are missing", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({
          attributes: {
            next_game: undefined,
            last_game: {
              ...footballProgramState().attributes.last_game!,
              team_score: undefined,
              opponent_score: undefined,
              result: "W",
            },
          },
        }),
      },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(card.shadowRoot?.querySelector(".hero-score")).toBeNull();
    expect(text).not.toMatch(/\b0\s*[–-]\s*0\b/);
    expect(text).toContain("W");
  });

  it("preserves neutral-site left/right layout without crashing", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: {
        [FOOTBALL_ENTITY_ID]: footballProgramState({
          attributes: {
            last_game: undefined,
            next_game: {
              ...footballProgramState().attributes.next_game!,
              home_away: "neutral",
            },
          },
        }),
      },
    };
    await card.updateComplete;

    const away = card.shadowRoot?.querySelector(".hero-team--away .team-name")?.textContent;
    const home = card.shadowRoot?.querySelector(".hero-team--home .team-name")?.textContent;
    expect(away).toBe("Centennial");
    expect(home).toBe("Alpharetta");
    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();
  });

  it("renders a centered hero with away on the left and home on the right", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    await card.updateComplete;

    const away = card.shadowRoot?.querySelector(".hero-team--away .team-name")?.textContent;
    const home = card.shadowRoot?.querySelector(".hero-team--home .team-name")?.textContent;
    expect(away).toBe("Johns Creek");
    expect(home).toBe("Centennial");
    expect(card.shadowRoot?.querySelector(".hero-at")?.textContent).toBe("AT");
    expect(card.shadowRoot?.querySelector(".hero-eyebrow")?.textContent).toBe("Last");
  });

  it("shows last_game as hero with score when it is closer to now", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Centennial | Boys Varsity Football | 26-27");
    expect(text).toContain("Record: 2-0");
    expect(text).toContain("Last");
    expect(text).toContain("18 – 54");
    expect(text).toContain("W");
    expect(text).toContain("Next:");
    expect(text).toContain("Alpharetta");
    expect(text).toContain("FRIDAY - Sep 4 - 7:30 PM");
    expect(text).not.toContain("Sep 4, 2026");
    expect(card.shadowRoot?.querySelector(".chrome img")).toBeNull();
    expect(card.shadowRoot?.querySelector(".secondary-highlight")).not.toBeNull();
    expect(text).not.toContain("game_url");
  });

  it("shows next_game as hero without fake scores once it is closer", async () => {
    vi.setSystemTime(new Date(2026, 8, 2, 12, 0, 0));
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Next");
    expect(text).toContain("Alpharetta");
    expect(text).toContain("FRIDAY - Sep 4 - 7:30 PM");
    expect(text).not.toContain("2026");
    expect(card.shadowRoot?.querySelector(".hero-score")).toBeNull();
    expect(text).toContain("Last:");
    expect(text).toContain("Johns Creek");
  });

  it("shows team names beneath hero logos", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    await card.updateComplete;

    const names = card.shadowRoot?.querySelectorAll(".hero .team-name");
    expect(names?.length).toBe(2);
    expect(names?.[0]?.textContent).toBeTruthy();
    expect(names?.[1]?.textContent).toBeTruthy();
  });

  it("does not show a school logo in the header chrome", async () => {
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    await card.updateComplete;

    expect(card.shadowRoot?.querySelector(".chrome img")).toBeNull();
    expect(card.shadowRoot?.querySelector(".hero .logo-image")).not.toBeNull();
  });

  it("keeps layout stable when hero logos are missing", async () => {
    const state = footballProgramState({
      attributes: {
        entity_picture: undefined,
        last_game: {
          ...footballProgramState().attributes.last_game!,
          opponent_logo: undefined,
        },
      },
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = { states: { [FOOTBALL_ENTITY_ID]: state } };
    await card.updateComplete;

    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();
    expect(card.shadowRoot?.querySelectorAll(".team-name").length).toBe(2);
  });

  it("defaults mode to both and renders the collapsed hero shell", async () => {
    expect(resolveCardMode(undefined)).toBe("both");
    const card = createCard({ entity: FOOTBALL_ENTITY_ID });
    card.hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    await card.updateComplete;

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Last");
    expect(text).not.toContain("Schedule rendering is not implemented");
  });

  it("uses current product labels and helpers in the card editor", () => {
    const form = HighSchoolSportsScoresCard.getConfigForm();
    const modeSchema = form.schema.find((entry) => entry.name === "mode");
    const labels = modeSchema?.selector.select.options.map(
      (option: { label: string }) => option.label,
    );
    expect(labels).toEqual(["Last/Next + Schedule", "Last/Next only", "Schedule only"]);

    expect(form.computeHelper({ name: "entity" }, { entity: FOOTBALL_ENTITY_ID })).toContain(
      "full schedule",
    );
    expect(form.computeHelper({ name: "mode" }, { entity: FOOTBALL_ENTITY_ID, mode: "both" })).toBe(
      "Game card; click to view the full schedule.",
    );
    expect(
      form.computeHelper({ name: "mode" }, { entity: FOOTBALL_ENTITY_ID, mode: "last_next" }),
    ).toBe("Game card without the expandable schedule.");
    expect(
      form.computeHelper({ name: "mode" }, { entity: FOOTBALL_ENTITY_ID, mode: "schedule" }),
    ).toBe("Full schedule and results.");

    const cardSource = readFileSync(
      resolve(srcDir, "high-school-sports-scores-card.ts"),
      "utf8",
    );
    expect(cardSource).not.toContain("later slice");
    expect(cardSource).not.toContain("Schedule rendering is not available");
  });

  it("registers picker metadata without custom: prefix but suggests configs with it", () => {
    const entry = window.customCards?.find(
      (card) => card.name === "High School Sports Scores",
    );
    expect(entry?.type).toBe("high-school-sports-scores-card");
    expect(entry?.type).not.toContain("custom:");

    const hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    const suggestion = entry?.getEntitySuggestion?.(hass, FOOTBALL_ENTITY_ID);
    expect(suggestion).not.toBeNull();
    expect(suggestion?.config.type).toBe("custom:high-school-sports-scores-card");
    expect(suggestion?.config.entity).toBe(FOOTBALL_ENTITY_ID);
  });

  it("suggests the card only for full program sensor attribute shapes", () => {
    const hass = {
      states: { [FOOTBALL_ENTITY_ID]: footballProgramState() },
    };
    expect(isProgramEntity(hass, FOOTBALL_ENTITY_ID)).toBe(true);
    expect(isProgramEntity(hass, "sensor.other_sensor")).toBe(false);

    const partial = footballProgramState({
      attributes: { display_label: undefined },
    });
    expect(
      isProgramEntity(
        { states: { [FOOTBALL_ENTITY_ID]: partial } },
        FOOTBALL_ENTITY_ID,
      ),
    ).toBe(false);
  });

  it("does not use Date parsing for displayed provider game timestamps", () => {
    const displaySources = ["card-helpers.ts", "datetime.ts", "entity-suggestion.ts"];
    for (const file of displaySources) {
      const source = readFileSync(resolve(srcDir, file), "utf8");
      expect(source).not.toMatch(/\bnew Date\b/);
      expect(source).not.toMatch(/\bDate\.parse\b/);
    }

    const cardSource = readFileSync(
      resolve(srcDir, "high-school-sports-scores-card.ts"),
      "utf8",
    );
    expect(cardSource).not.toMatch(/\bDate\.parse\b/);
    expect(cardSource).not.toMatch(/naiveIsoToLocalMs/);
    expect(cardSource).toMatch(/selectHeroGame\([\s\S]*new Date\(\)/);
  });
});

describe("HighSchoolSportsScoresCard schedule websocket", () => {
  beforeAll(() => {
    if (!customElements.get("ha-card")) {
      customElements.define("ha-card", HaCardStub);
    }
    if (!customElements.get(CARD_TAG)) {
      customElements.define(CARD_TAG, HighSchoolSportsScoresCard);
    }
  });

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 7, 30, 12, 0, 0));
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not fetch schedule while collapsed in both mode", async () => {
    const { hass, callWS } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    expect(callWS).not.toHaveBeenCalled();
    expect(card.shadowRoot?.querySelector(".schedule-section")).toBeNull();
  });

  it("fetches and renders a one-term football schedule when expanded", async () => {
    const { hass, callWS } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    await expandCard(card);

    expect(callWS).toHaveBeenCalledWith({
      type: WS_GET_PROGRAM_SCHEDULE,
      entity_id: FOOTBALL_ENTITY_ID,
    });
    const labels = [...(card.shadowRoot?.querySelectorAll(".schedule-term-label") ?? [])].map(
      (node) => node.textContent,
    );
    expect(labels).toEqual([]);
    expect(card.shadowRoot?.textContent).toContain("vs Alpharetta");
    expect(card.shadowRoot?.textContent).toContain("W 54-18");
    expect(card.shadowRoot?.textContent).not.toMatch(/\bFRIDAY\b/i);
    expect(card.shadowRoot?.querySelector(".record-summary")?.textContent).toBe("2-0");
    expect(card.shadowRoot?.textContent).toContain("Home 2-0");
  });

  it("highlights the row matching next_game.id", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".schedule-row--next")).not.toBeNull();
    });

    const highlighted = card.shadowRoot?.querySelector(".schedule-row--next");
    expect(highlighted?.textContent).toContain("Alpharetta");
  });

  it("renders freshman terms in DTO order without client-side sorting", async () => {
    const { hass } = createMockHass({
      entityId: FRESHMAN_ENTITY_ID,
      state: freshmanProgramState(),
      schedulePayload: FRESHMAN_SPRING_FIRST_PAYLOAD,
    });
    const card = createCard({
      entity: FRESHMAN_ENTITY_ID,
      mode: "schedule",
    });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelectorAll(".schedule-term-label").length).toBe(2);
    });

    const labels = [...(card.shadowRoot?.querySelectorAll(".schedule-term-label") ?? [])].map(
      (node) => node.textContent?.trim(),
    );
    expect(labels).toEqual(["Spring", "Fall"]);
    expect(card.shadowRoot?.textContent?.indexOf("Chattahoochee")).toBeGreaterThan(
      card.shadowRoot?.textContent?.indexOf("Lassiter") ?? -1,
    );
  });

  it("shows empty-schedule copy for resolved payloads with zero games", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_EMPTY_SCHEDULE_PAYLOAD,
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.textContent).toContain("No games are currently published.");
    });

    expect(card.shadowRoot?.querySelector(".schedule-state--error")).toBeNull();
    expect(card.shadowRoot?.textContent).not.toContain("Schedule data is unavailable");
  });

  it("shows unresolved copy distinct from empty schedule and websocket failure", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_UNRESOLVED_SCHEDULE_PAYLOAD,
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.textContent).toContain(
        "Schedule data is unavailable for this program.",
      );
    });

    expect(card.shadowRoot?.textContent).not.toContain("No games are currently published.");
  });

  it("shows websocket failure copy distinct from empty and unresolved states", async () => {
    const { hass } = createMockHass({
      callWSError: { code: "entity_not_found", message: "Entity not found" },
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.textContent).toContain("Entity not found");
    });

    expect(card.shadowRoot?.textContent).not.toContain("No games are currently published.");
    expect(card.shadowRoot?.textContent).not.toContain(
      "Schedule data is unavailable for this program.",
    );
  });

  it("renders schedule-only mode with header chrome and no hero", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();
    });

    expect(card.shadowRoot?.querySelector(".hero")).toBeNull();
    expect(card.shadowRoot?.textContent).toContain("Centennial | Boys Varsity Football | 26-27");
    expect(card.shadowRoot?.textContent).not.toContain("Schedule rendering is not implemented");
    expect(card.shadowRoot?.querySelector(".program-card--interactive")).toBeNull();
  });

  it("unsubscribes when collapsed and does not fetch again until re-expanded", async () => {
    const { hass, callWS, subscriptions } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    await expandCard(card);
    expect(subscriptions).toHaveLength(1);

    await collapseCard(card);
    expect(subscriptions[0]?.unsubscribe).toHaveBeenCalledTimes(1);
    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();

    const callsAfterCollapse = callWS.mock.calls.length;
    await card.updateComplete;
    expect(callWS.mock.calls.length).toBe(callsAfterCollapse);
  });

  it("refetches when a subscription notify arrives", async () => {
    const { hass, callWS, subscriptions } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => expect(subscriptions).toHaveLength(1));
    await vi.waitFor(() => expect(callWS).toHaveBeenCalledTimes(1));

    subscriptions.at(-1)?.callback({
      entity_id: FOOTBALL_ENTITY_ID,
      event: "schedule_updated",
    });
    await vi.waitFor(() => expect(callWS).toHaveBeenCalledTimes(2));
  });

  it("never fetches or subscribes in last_next mode", async () => {
    const { hass, callWS, subscriptions } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "last_next" });
    card.hass = hass;
    await card.updateComplete;

    card.shadowRoot
      ?.querySelector(".program-card--interactive")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await card.updateComplete;

    expect(callWS).not.toHaveBeenCalled();
    expect(subscriptions).toHaveLength(0);
    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();
  });

  it("ignores stale in-flight fetch results after collapse", async () => {
    const { hass, callWS } = createMockHass({ fetchDelayMs: 50 });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    card.shadowRoot
      ?.querySelector(".program-card--interactive")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await card.updateComplete;

    await collapseCard(card);
    await vi.advanceTimersByTimeAsync(100);
    await card.updateComplete;

    expect(card.shadowRoot?.querySelector(".schedule-section")).toBeNull();
    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();
    expect(callWS).toHaveBeenCalledTimes(1);
  });

  it("collapses expanded both mode from a whole-card click", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    await expandCard(card);
    expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();

    await collapseCard(card);
    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();
    expect(card.shadowRoot?.querySelector(".schedule-section")).toBeNull();
  });

  it("collapses expanded both mode from Space", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    await expandCard(card);
    card.shadowRoot
      ?.querySelector(".program-card--interactive")
      ?.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
    await card.updateComplete;

    expect(card.shadowRoot?.querySelector(".hero")).not.toBeNull();
  });

  it("shows team_record prominently in schedule mode and omits it when absent", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".record-summary")?.textContent).toBe("2-0");
    });

    const withoutRecord = createMockHass({
      state: footballProgramState({ attributes: { team_record: undefined } }),
    });
    const noRecordCard = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    noRecordCard.hass = withoutRecord.hass;
    await noRecordCard.updateComplete;
    await vi.waitFor(() => {
      expect(noRecordCard.shadowRoot?.querySelector(".record-summary")).toBeNull();
    });
  });

  it("does not duplicate date and time across schedule columns", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".schedule-row")).not.toBeNull();
    });

    const nextRow = card.shadowRoot?.querySelector(".schedule-row--next");
    expect(nextRow?.querySelector(".schedule-row-date")?.textContent).toBe("Sep 4");
    expect(nextRow?.querySelector(".schedule-row-result")?.textContent).toBe("7:30 PM");
    expect(nextRow?.querySelector(".schedule-row-date")?.textContent).not.toContain("PM");
  });

  it("does not create duplicate active subscriptions while expanded", async () => {
    const { hass, subscriptions } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    await expandCard(card);
    expect(subscriptions).toHaveLength(1);

    card.hass = {
      ...hass,
      states: { ...hass.states },
    };
    await card.updateComplete;
    await vi.waitFor(() => expect(subscriptions).toHaveLength(1));
  });

  it("does not create duplicate active subscriptions on repeated expand clicks", async () => {
    const { hass, subscriptions } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    await expandCard(card);
    expect(subscriptions).toHaveLength(1);

    await collapseCard(card);
    expect(subscriptions[0]?.unsubscribe).toHaveBeenCalledTimes(1);

    await expandCard(card);
    expect(subscriptions).toHaveLength(2);
    expect(subscriptions[1]?.unsubscribe).not.toHaveBeenCalled();
  });

  it("unsubscribes the prior entity before subscribing to a new one", async () => {
    const otherEntity = "sensor.other_program";
    const { hass, subscriptions } = createMockHass();
    hass.states[otherEntity] = footballProgramState({ entity_id: otherEntity });

    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => expect(subscriptions).toHaveLength(1));

    card.setConfig({ entity: otherEntity, mode: "schedule" });
    await card.updateComplete;
    await vi.waitFor(() => expect(subscriptions).toHaveLength(2));
    expect(subscriptions[0]?.unsubscribe).toHaveBeenCalledTimes(1);
  });

  it("expands from the keyboard on Enter", async () => {
    const { hass, callWS } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;

    const interactive = card.shadowRoot?.querySelector(".program-card--interactive");
    interactive?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await card.updateComplete;
    await vi.waitFor(() => expect(callWS).toHaveBeenCalled());
  });

  it("renders multi-term freshman schedule labels in backend order", async () => {
    const { hass } = createMockHass({
      entityId: FRESHMAN_ENTITY_ID,
      state: freshmanProgramState(),
      schedulePayload: FRESHMAN_SCHEDULE_PAYLOAD,
    });
    const card = createCard({
      entity: FRESHMAN_ENTITY_ID,
      mode: "schedule",
    });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelectorAll(".schedule-term-label").length).toBe(2);
    });

    const labels = [...(card.shadowRoot?.querySelectorAll(".schedule-term-label") ?? [])].map(
      (node) => node.textContent?.trim(),
    );
    expect(labels).toEqual(["Fall", "Spring"]);
    expect(card.shadowRoot?.textContent).toContain("at Chattahoochee");
    expect(card.shadowRoot?.textContent).toContain("vs Lassiter");
  });

  it("shows rollover notice and schedule list for waiting_for_applicable_year with games", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_WAITING_WITH_GAMES_PAYLOAD,
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();
    });

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("until 27-28 is published");
    expect(text).toContain("vs Alpharetta");
    expect(text).not.toContain("Schedule refresh failed");
    expect(text).not.toContain("No games are currently published.");
    expect(text).not.toContain("Schedule data is unavailable for this program.");
    expect(card.shadowRoot?.querySelector(".schedule-state--error")).toBeNull();
    expect(card.shadowRoot?.querySelector(".schedule-notice--rollover")).not.toBeNull();
  });

  it("shows waiting empty copy without rollover notice when waiting has zero games", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_WAITING_EMPTY_PAYLOAD,
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.textContent).toContain(
        "Waiting for the applicable school-year schedule to publish.",
      );
    });

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).not.toContain("prior school-year");
    expect(text).not.toContain("Schedule refresh failed");
    expect(card.shadowRoot?.querySelector(".schedule-notice")).toBeNull();
    expect(card.shadowRoot?.querySelector(".schedule-section")).toBeNull();
  });

  it("shows stale-last-good notice for resolved payload with stale retained games", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_STALE_RESOLVED_PAYLOAD,
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();
    });

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("Schedule refresh failed");
    expect(text).toContain("vs Alpharetta");
    expect(text).not.toContain("prior school-year");
    expect(text).not.toContain("until 27-28 is published");
    expect(card.shadowRoot?.querySelector(".schedule-notice--stale")).not.toBeNull();
    expect(card.shadowRoot?.querySelector(".schedule-notice--rollover")).toBeNull();
  });

  it("shows stale-last-good notice once for mixed refreshed and stale terms", async () => {
    const { hass } = createMockHass({
      entityId: FRESHMAN_ENTITY_ID,
      state: freshmanProgramState(),
      schedulePayload: FOOTBALL_MIXED_STALE_RESOLVED_PAYLOAD,
    });
    const card = createCard({ entity: FRESHMAN_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelectorAll(".schedule-notice--stale").length).toBe(1);
    });

    expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();
    expect(card.shadowRoot?.textContent).toContain("Schedule refresh failed");
  });

  it("shows no stale or rollover notice for all-refreshed resolved schedule", async () => {
    const { hass } = createMockHass();
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "schedule" });
    card.hass = hass;
    await card.updateComplete;
    await vi.waitFor(() => {
      expect(card.shadowRoot?.querySelector(".schedule-section")).not.toBeNull();
    });

    expect(card.shadowRoot?.querySelector(".schedule-notice")).toBeNull();
  });

  it("prefers rollover notice over stale-last-good when waiting also has stale terms", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_WAITING_WITH_GAMES_PAYLOAD,
    });
    const card = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    card.hass = hass;
    await card.updateComplete;
    await expandCard(card);

    const text = card.shadowRoot?.textContent ?? "";
    expect(text).toContain("until 27-28 is published");
    expect(text).not.toContain("Schedule refresh failed");
    expect(card.shadowRoot?.querySelector(".schedule-notice--rollover")).not.toBeNull();
  });

  it("does not show schedule notices in collapsed both or last_next modes", async () => {
    const { hass } = createMockHass({
      schedulePayload: FOOTBALL_STALE_RESOLVED_PAYLOAD,
    });

    const bothCollapsed = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "both" });
    bothCollapsed.hass = hass;
    await bothCollapsed.updateComplete;
    expect(bothCollapsed.shadowRoot?.querySelector(".schedule-notice")).toBeNull();

    const lastNext = createCard({ entity: FOOTBALL_ENTITY_ID, mode: "last_next" });
    lastNext.hass = hass;
    await lastNext.updateComplete;
    expect(lastNext.shadowRoot?.querySelector(".schedule-notice")).toBeNull();
    expect(lastNext.shadowRoot?.querySelector(".hero")).not.toBeNull();
  });
});
