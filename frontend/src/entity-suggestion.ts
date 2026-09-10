import type { HomeAssistantLike } from "./types";

const REQUIRED_PROGRAM_ATTRIBUTES = [
  "school_id",
  "school_name",
  "sport",
  "gender",
  "level",
  "display_label",
] as const;

/** Frontend-only heuristic for card picker suggestions (not websocket ownership). */
export function isProgramEntity(
  hass: HomeAssistantLike,
  entityId: string,
): boolean {
  if (entityId.split(".")[0] !== "sensor") {
    return false;
  }

  const state = hass.states[entityId];
  if (!state) {
    return false;
  }

  const attributes = state.attributes;
  return REQUIRED_PROGRAM_ATTRIBUTES.every((key) => {
    const value = attributes[key];
    return typeof value === "string" && value.length > 0;
  });
}
