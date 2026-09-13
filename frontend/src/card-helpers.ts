import { formatNaiveDateTime } from "./datetime";
import type {
  CardMode,
  GameAttribute,
  LovelaceCardGridOptions,
  ProgramSensorAttributes,
} from "./types";

export const DEFAULT_CARD_MODE: CardMode = "both";

export function resolveCardMode(mode: CardMode | undefined): CardMode {
  if (mode === "last_next" || mode === "schedule") {
    return mode;
  }
  return DEFAULT_CARD_MODE;
}

export function buildHeaderTitle(attributes: ProgramSensorAttributes): string {
  const school = attributes.school_name?.trim() ?? "";
  const program = attributes.display_label?.trim() || attributes.sport?.trim() || "";
  const year = attributes.year?.trim() ?? "";
  return [school, program, year].filter(Boolean).join(" | ");
}

/** Collapsed-card title: ``{program} · {sport}``. Year stays out of this string. */
export function buildCollapsedHeaderTitle(attributes: ProgramSensorAttributes): string {
  const program =
    attributes.display_label?.trim() || attributes.school_name?.trim() || "";
  const sport = attributes.sport?.trim() ?? "";
  return [program, sport].filter(Boolean).join(" · ");
}

export interface MatchupTeam {
  displayName: string;
  logoUrl?: string;
  score?: number;
}

export interface MatchupLayout {
  away: MatchupTeam;
  home: MatchupTeam;
}

const SUFFIX_PATTERNS = [
  /\s+High School$/i,
  /\s+HS$/i,
  /\s+School$/i,
] as const;

/** Conservative display-name cleanup for logo captions. */
export function shortenDisplayName(name: string | undefined): string {
  if (!name) {
    return "";
  }
  let value = name.trim();
  for (const pattern of SUFFIX_PATTERNS) {
    value = value.replace(pattern, "");
  }
  return value.trim();
}

export function buildMatchupLayout(
  attributes: ProgramSensorAttributes,
  game: GameAttribute,
): MatchupLayout {
  const schoolName = shortenDisplayName(attributes.school_name);
  const opponentName = shortenDisplayName(game.opponent_name);
  const schoolLogo = attributes.entity_picture;
  const opponentLogo = game.opponent_logo;

  const school: MatchupTeam = {
    displayName: schoolName,
    logoUrl: schoolLogo,
    score: game.team_score,
  };
  const opponent: MatchupTeam = {
    displayName: opponentName,
    logoUrl: opponentLogo,
    score: game.opponent_score,
  };

  if (game.home_away === "away") {
    return { away: school, home: opponent };
  }
  if (game.home_away === "neutral") {
    return { away: school, home: opponent };
  }
  return { away: opponent, home: school };
}

export function formatHeroScore(game: GameAttribute, layout: MatchupLayout): string | null {
  if (game.team_score == null || game.opponent_score == null) {
    return null;
  }
  const awayScore = layout.away.score;
  const homeScore = layout.home.score;
  if (awayScore == null || homeScore == null) {
    return null;
  }
  return `${awayScore} – ${homeScore}`;
}

export function formatHeroResult(game: GameAttribute): string | null {
  if (!game.result) {
    return null;
  }
  return game.result;
}

/** Center label for upcoming matchups: away → ``AT``, home/neutral → ``vs``. */
export function formatMatchupVenueLabel(game: GameAttribute): string {
  return opponentPreposition(game) === "at" ? "AT" : "vs";
}

/** Compact completed-game status line: ``Final · Sep 11`` (no time). */
export function formatFinalStatusLine(date: string | undefined): string {
  const parts = formatNaiveDateTime(date);
  const monthDay = stripYearFromDisplayDate(parts.date);
  return monthDay ? `Final · ${monthDay}` : "Final";
}

/** Upcoming status line: ``Fri, Sep 18 · 7:30 PM``. */
export function formatUpcomingStatusLine(date: string | undefined): string {
  const parts = formatNaiveDateTime(date);
  const monthDay = stripYearFromDisplayDate(parts.date);
  const weekday = parts.weekday ? parts.weekday.slice(0, 3) : "";
  const dayDate = [weekday, monthDay].filter(Boolean).join(", ");
  return [dayDate, parts.time].filter(Boolean).join(" · ");
}

export type ScoreOutcome = "win" | "lose" | "tie" | "unknown";

export function scoreOutcomes(layout: MatchupLayout): {
  away: ScoreOutcome;
  home: ScoreOutcome;
} {
  const awayScore = layout.away.score;
  const homeScore = layout.home.score;
  if (awayScore == null || homeScore == null) {
    return { away: "unknown", home: "unknown" };
  }
  if (awayScore === homeScore) {
    return { away: "tie", home: "tie" };
  }
  if (awayScore > homeScore) {
    return { away: "win", home: "lose" };
  }
  return { away: "lose", home: "win" };
}

/** First initial plus a stable hue for missing-logo monograms. */
export function teamMonogram(name: string): { initial: string; hue: number } {
  const trimmed = name.trim();
  const initial = (trimmed.charAt(0) || "?").toUpperCase();
  return { initial, hue: hashNameToHue(trimmed || "?") };
}

export function hashNameToHue(name: string): number {
  let hash = 2166136261;
  for (let i = 0; i < name.length; i++) {
    hash ^= name.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % 360;
}

export function formatHeroScoreCells(layout: MatchupLayout): {
  away: string;
  home: string;
} | null {
  const awayScore = layout.away.score;
  const homeScore = layout.home.score;
  if (awayScore == null || homeScore == null) {
    return null;
  }
  return { away: String(awayScore), home: String(homeScore) };
}

export function formatLastGameScore(game: GameAttribute): string | null {
  if (game.team_score == null || game.opponent_score == null) {
    return null;
  }
  const score = `${game.team_score}-${game.opponent_score}`;
  if (game.result) {
    return `${game.result} ${score}`;
  }
  return score;
}

export interface GameDateTimeDisplay {
  weekday: string;
  date: string;
  time: string;
  line: string;
  compact: string;
  cardLine: string;
}

function stripYearFromDisplayDate(date: string): string {
  return date.replace(/,\s*\d{4}$/, "");
}

/** Single-row card datetime without year: ``FRIDAY - Sep 11 - 7:30 PM``. */
export function formatCardDateLine(date: string | undefined): string {
  const parts = formatNaiveDateTime(date);
  const monthDay = stripYearFromDisplayDate(parts.date);
  return [
    parts.weekday ? parts.weekday.toUpperCase() : "",
    monthDay,
    parts.time,
  ]
    .filter(Boolean)
    .join(" - ");
}

export function formatGameDateTime(date: string | undefined): GameDateTimeDisplay {
  const parts = formatNaiveDateTime(date);
  const line = [parts.weekday, parts.date, parts.time].filter(Boolean).join(" · ");
  const monthDay = stripYearFromDisplayDate(parts.date);
  const compact = [parts.weekday ? parts.weekday.slice(0, 3) : "", monthDay, parts.time]
    .filter(Boolean)
    .join(" - ");
  const cardLine = formatCardDateLine(date);
  return { ...parts, line, compact, cardLine };
}

/** Subscribed school home/neutral → ``vs``; away → ``at`` (secondary strip + last score line). */
function opponentPreposition(game: GameAttribute): "at" | "vs" {
  if (game.home_away === "away") {
    return "at";
  }
  return "vs";
}

export interface SecondaryStripContent {
  label: string;
  highlight: string;
  dateLine: string;
}

/** Next-game strip: ``vs Cambridge · Fri, Sep 18 · 7:30 PM``. */
export function formatNextGameStrip(game: GameAttribute): string {
  const opponent = shortenDisplayName(game.opponent_name);
  const matchup = [opponentPreposition(game), opponent].filter(Boolean).join(" ");
  const when = formatUpcomingStatusLine(game.date);
  return [matchup, when].filter(Boolean).join(" · ");
}

export function buildSecondaryStripContent(
  role: "last" | "next",
  game: GameAttribute,
): SecondaryStripContent {
  const label = role === "last" ? "Last" : "Next";
  const opponent = shortenDisplayName(game.opponent_name);
  const dateLine = formatUpcomingStatusLine(game.date);

  if (role === "last") {
    const score = formatLastGameScore(game);
    const highlight = score
      ? `${score} ${opponentPreposition(game)} ${opponent}`
      : opponent;
    return { label, highlight, dateLine };
  }

  const prep = opponentPreposition(game);
  return {
    label,
    highlight: `${prep} ${opponent}`,
    dateLine,
  };
}

/** Default Sections grid sizing: full width optional, automatic vertical height. */
export const DEFAULT_CARD_GRID_OPTIONS: LovelaceCardGridOptions = {
  columns: 6,
  rows: "auto",
  min_columns: 3,
  max_columns: 12,
  min_rows: 1,
};
