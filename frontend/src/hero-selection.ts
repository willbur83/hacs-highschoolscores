import type { GameAttribute } from "./types";

export type HeroRole = "last" | "next";

export interface HeroSelection {
  hero: GameAttribute;
  heroRole: HeroRole;
  secondary: GameAttribute | null;
  secondaryRole: HeroRole | null;
}

const ISO_NAIVE_RE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/;

/**
 * Interpret provider-naive ISO against browser-local civil time for hero relevance only.
 * Not used for displayed date/time formatting.
 */
export function naiveIsoToLocalMs(value: string | null | undefined): number | null {
  if (value == null || typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed || trimmed.includes("Z") || /[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return null;
  }

  const match = ISO_NAIVE_RE.exec(trimmed);
  if (!match) {
    return null;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6] ?? "0");

  if (
    !Number.isInteger(year) ||
    !Number.isInteger(month) ||
    !Number.isInteger(day) ||
    !Number.isInteger(hour) ||
    !Number.isInteger(minute) ||
    !Number.isInteger(second)
  ) {
    return null;
  }

  return new Date(year, month - 1, day, hour, minute, second).getTime();
}

function singleHero(
  game: GameAttribute,
  role: HeroRole,
): HeroSelection {
  return {
    hero: game,
    heroRole: role,
    secondary: null,
    secondaryRole: null,
  };
}

function pairHero(
  hero: GameAttribute,
  heroRole: HeroRole,
  secondary: GameAttribute,
  secondaryRole: HeroRole,
): HeroSelection {
  return { hero, heroRole, secondary, secondaryRole };
}

/**
 * Choose the temporally closer game as the collapsed-card hero.
 * Frontend presentation heuristic only; inject `now` in tests.
 */
export function selectHeroGame(
  lastGame: GameAttribute | undefined,
  nextGame: GameAttribute | undefined,
  now: Date,
): HeroSelection | null {
  if (!lastGame && !nextGame) {
    return null;
  }
  if (lastGame && !nextGame) {
    return singleHero(lastGame, "last");
  }
  if (!lastGame && nextGame) {
    return singleHero(nextGame, "next");
  }

  const lastMs = naiveIsoToLocalMs(lastGame!.date);
  const nextMs = naiveIsoToLocalMs(nextGame!.date);

  if (lastMs == null && nextMs == null) {
    return pairHero(lastGame!, "last", nextGame!, "next");
  }
  if (lastMs == null) {
    return pairHero(nextGame!, "next", lastGame!, "last");
  }
  if (nextMs == null) {
    return pairHero(lastGame!, "last", nextGame!, "next");
  }

  const nowMs = now.getTime();
  const lastDistance = Math.abs(nowMs - lastMs);
  const nextDistance = Math.abs(nextMs - nowMs);

  if (lastDistance <= nextDistance) {
    return pairHero(lastGame!, "last", nextGame!, "next");
  }
  return pairHero(nextGame!, "next", lastGame!, "last");
}
