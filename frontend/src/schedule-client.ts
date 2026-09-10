import type { HomeAssistantLike, ProgramSchedulePayload } from "./types";

export const WS_GET_PROGRAM_SCHEDULE =
  "high_school_sports_scores/get_program_schedule";
export const WS_SUBSCRIBE_PROGRAM_SCHEDULE_UPDATES =
  "high_school_sports_scores/subscribe_program_schedule_updates";

export function extractScheduleWsError(error: unknown): string {
  if (error == null) {
    return "Schedule request failed";
  }
  if (typeof error === "object") {
    const record = error as Record<string, unknown>;
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message;
    }
    if (typeof record.error === "string" && record.error.trim()) {
      return record.error;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Schedule request failed";
}

export async function fetchProgramSchedule(
  hass: HomeAssistantLike,
  entityId: string,
): Promise<ProgramSchedulePayload> {
  if (!hass.callWS) {
    throw new Error("Home Assistant websocket requests are unavailable");
  }
  return hass.callWS<ProgramSchedulePayload>({
    type: WS_GET_PROGRAM_SCHEDULE,
    entity_id: entityId,
  });
}

export async function subscribeProgramScheduleUpdates(
  hass: HomeAssistantLike,
  entityId: string,
  onNotify: () => void,
): Promise<() => void> {
  if (!hass.connection?.subscribeMessage) {
    throw new Error("Home Assistant websocket subscriptions are unavailable");
  }
  return hass.connection.subscribeMessage(
    (message) => {
      if (
        message &&
        typeof message === "object" &&
        (message as { event?: string }).event === "schedule_updated"
      ) {
        onNotify();
      }
    },
    {
      type: WS_SUBSCRIBE_PROGRAM_SCHEDULE_UPDATES,
      entity_id: entityId,
    },
  );
}
