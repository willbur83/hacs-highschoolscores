import {
  formatLastGameScore,
  shortenDisplayName,
} from "./card-helpers";
import { formatNaiveDateTime } from "./datetime";
import type { GameAttribute, ProgramSchedulePayload, ScheduleTerm } from "./types";

export type ScheduleBodyKind =
  | "loading"
  | "error"
  | "empty-resolved"
  | "unresolved"
  | "waiting"
  | "ready";

export interface ScheduleBodyState {
  kind: ScheduleBodyKind;
  message?: string;
  payload?: ProgramSchedulePayload;
}

export type VenueBucket = "home" | "away" | "neutral";

export interface VenueRecordCount {
  wins: number;
  losses: number;
  ties: number;
}

const WEEKDAY_PREFIX_RE =
  /^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\b/i;

function stripYearFromDisplayDate(date: string): string {
  return date.replace(/,\s*\d{4}$/, "");
}

function opponentPreposition(game: GameAttribute): "at" | "vs" {
  if (game.home_away === "away") {
    return "at";
  }
  return "vs";
}

function classifyFinalResult(result: string | undefined): "W" | "L" | "T" | null {
  if (!result) {
    return null;
  }
  const normalized = result.trim().toUpperCase();
  if (normalized === "W" || normalized === "WIN") {
    return "W";
  }
  if (normalized === "L" || normalized === "LOSS") {
    return "L";
  }
  if (normalized === "T" || normalized === "TIE") {
    return "T";
  }
  return null;
}

function classifyVenueBucket(homeAway: string | undefined): VenueBucket | null {
  if (homeAway === "home" || homeAway === "away" || homeAway === "neutral") {
    return homeAway;
  }
  return null;
}

/** Compact schedule date without weekday or year: ``Sep 11``. */
export function formatScheduleMonthDay(date: string | undefined): string {
  const parts = formatNaiveDateTime(date);
  if (!parts.date) {
    return "";
  }
  return stripYearFromDisplayDate(parts.date);
}

export function formatScheduleOpponent(game: GameAttribute): string {
  const opponent = shortenDisplayName(game.opponent_name);
  return `${opponentPreposition(game)} ${opponent}`;
}

export function formatScheduleResultColumn(game: GameAttribute): string {
  if (game.status === "final") {
    const score = formatLastGameScore(game);
    return score ?? "Final";
  }
  if (game.status === "scheduled") {
    return formatNaiveDateTime(game.date).time || "Scheduled";
  }
  return game.status || "Unknown";
}

export function collectScheduleGames(payload: ProgramSchedulePayload): GameAttribute[] {
  return payload.terms.flatMap((term) => term.games);
}

function formatVenueRecordLabel(bucket: VenueBucket, record: VenueRecordCount): string {
  const label = bucket.charAt(0).toUpperCase() + bucket.slice(1);
  if (record.ties > 0) {
    return `${label} ${record.wins}-${record.losses}-${record.ties}`;
  }
  return `${label} ${record.wins}-${record.losses}`;
}

/** Derive Home/Away/Neutral W-L(-T) from classified final games across all DTO terms. */
export function deriveVenueRecordBreakdown(
  payload: ProgramSchedulePayload,
): string | null {
  const totals: Record<VenueBucket, VenueRecordCount> = {
    home: { wins: 0, losses: 0, ties: 0 },
    away: { wins: 0, losses: 0, ties: 0 },
    neutral: { wins: 0, losses: 0, ties: 0 },
  };

  for (const game of collectScheduleGames(payload)) {
    if (game.status !== "final") {
      continue;
    }
    const bucket = classifyVenueBucket(game.home_away);
    const outcome = classifyFinalResult(game.result);
    if (bucket == null || outcome == null) {
      continue;
    }
    if (outcome === "W") {
      totals[bucket].wins += 1;
    } else if (outcome === "L") {
      totals[bucket].losses += 1;
    } else {
      totals[bucket].ties += 1;
    }
  }

  const segments = (["home", "away", "neutral"] as const)
    .filter((bucket) => {
      const record = totals[bucket];
      return record.wins + record.losses + record.ties > 0;
    })
    .map((bucket) => formatVenueRecordLabel(bucket, totals[bucket]));

  return segments.length > 0 ? segments.join(" | ") : null;
}

export function countScheduleGames(payload: ProgramSchedulePayload): number {
  return collectScheduleGames(payload).length;
}

export type ScheduleNoticeKind = "rollover" | "stale-last-good";

export interface ScheduleNotice {
  kind: ScheduleNoticeKind;
  message: string;
}

function termHasUsableGames(term: ScheduleTerm): boolean {
  return term.games.length > 0;
}

function hasStaleTermWithGames(payload: ProgramSchedulePayload): boolean {
  return payload.terms.some((term) => term.status === "stale" && termHasUsableGames(term));
}

/**
 * Subtle schedule-view notice for retained prior-year data (A) or last-good after
 * fetch failure (B). A takes precedence over B; never returns both.
 */
export function resolveScheduleNotice(
  payload: ProgramSchedulePayload,
): ScheduleNotice | null {
  const gameCount = countScheduleGames(payload);
  if (gameCount === 0) {
    return null;
  }

  if (payload.resolution_status === "waiting_for_applicable_year") {
    return {
      kind: "rollover",
      message: `Showing the prior school-year schedule until ${payload.applicable_school_year} is published.`,
    };
  }

  if (payload.resolution_status === "resolved" && hasStaleTermWithGames(payload)) {
    return {
      kind: "stale-last-good",
      message: "Schedule refresh failed; showing the last successfully loaded schedule.",
    };
  }

  return null;
}

export function classifySchedulePayload(
  payload: ProgramSchedulePayload,
): ScheduleBodyState {
  if (payload.resolution_status === "unresolved") {
    return {
      kind: "unresolved",
      message: "Schedule data is unavailable for this program.",
      payload,
    };
  }

  const gameCount = countScheduleGames(payload);
  if (payload.resolution_status === "waiting_for_applicable_year" && gameCount === 0) {
    return {
      kind: "waiting",
      message: "Waiting for the applicable school-year schedule to publish.",
      payload,
    };
  }

  if (payload.resolution_status === "resolved" && gameCount === 0) {
    return {
      kind: "empty-resolved",
      message: "No games are currently published.",
      payload,
    };
  }

  return { kind: "ready", payload };
}

export function shouldShowTermSectionLabel(terms: ScheduleTerm[]): boolean {
  return terms.length > 1;
}

export function formatTermSectionLabel(term: ScheduleTerm): string {
  return term.season?.trim() || "Season";
}

export function formatTermEmptyMessage(term: ScheduleTerm): string {
  if (term.status === "error") {
    return "This season schedule could not be loaded.";
  }
  return "No games are currently published for this season.";
}

/** Guard for tests: schedule rows must not include weekday names. */
export function scheduleRowDateContainsWeekday(text: string): boolean {
  return WEEKDAY_PREFIX_RE.test(text.trim());
}
