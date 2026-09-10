import { formatNaiveDateTime } from "./datetime";
import type { CardMode, GameAttribute, ProgramSensorAttributes } from "./types";

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

export function buildSecondaryStripContent(
  role: "last" | "next",
  game: GameAttribute,
): SecondaryStripContent {
  const label = role === "last" ? "Last" : "Next";
  const opponent = shortenDisplayName(game.opponent_name);
  const dateLine = formatCardDateLine(game.date);

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
