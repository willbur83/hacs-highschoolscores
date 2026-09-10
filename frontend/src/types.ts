/** Lovelace card configuration. */

export type CardMode = "both" | "last_next" | "schedule";

export interface HighSchoolSportsScoresCardConfig {
  type?: string;
  entity: string;
  mode?: CardMode;
}

/** One last_game / next_game attribute object from a program sensor. */
export interface GameAttribute {
  id: string;
  date: string;
  status: string;
  opponent_name: string;
  home_away: string;
  opponent_id?: string;
  team_score?: number;
  opponent_score?: number;
  result?: string;
  venue?: string;
  game_url?: string;
  opponent_logo?: string;
  season?: string;
}

/** Program sensor attributes consumed by the card (collapsed view). */
export interface ProgramSensorAttributes {
  school_id?: string;
  school_name?: string;
  sport?: string;
  gender?: string;
  level?: string;
  year?: string;
  display_label?: string;
  team_record?: string;
  entity_picture?: string;
  last_game?: GameAttribute;
  next_game?: GameAttribute;
}

export interface HassEntityState {
  entity_id: string;
  state: string;
  attributes: ProgramSensorAttributes & Record<string, unknown>;
}

/** Websocket schedule DTO (schema_version 1). */
export type ResolutionStatus =
  | "resolved"
  | "unresolved"
  | "waiting_for_applicable_year";

export type TermRefreshStatus = "refreshed" | "stale" | "error";

export interface ScheduleTerm {
  season: string | null;
  year: string | null;
  status: TermRefreshStatus;
  games: GameAttribute[];
}

export interface ProgramSchedulePayload {
  schema_version: number;
  entity_id: string;
  school_id: string;
  school_name: string;
  applicable_school_year: string;
  sport: string;
  gender: string;
  level: string;
  display_label: string;
  resolution_status: ResolutionStatus;
  terms: ScheduleTerm[];
}

export interface ScheduleUpdateEvent {
  entity_id: string;
  event: "schedule_updated";
}

export interface HomeAssistantConnectionLike {
  subscribeMessage<TMessage>(
    callback: (message: TMessage) => void,
    subscribePayload: Record<string, unknown>,
  ): Promise<() => void>;
}

export interface HomeAssistantLike {
  states: Record<string, HassEntityState | undefined>;
  callWS?<T = unknown>(message: Record<string, unknown>): Promise<T>;
  connection?: HomeAssistantConnectionLike;
}
