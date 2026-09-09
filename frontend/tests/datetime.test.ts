import { describe, expect, it } from "vitest";

import { formatNaiveDateTime } from "../src/datetime";

describe("formatNaiveDateTime", () => {
  it("formats a provider-naive ISO datetime without timezone conversion", () => {
    expect(formatNaiveDateTime("2026-09-04T19:30:00")).toEqual({
      weekday: "Friday",
      date: "Sep 4, 2026",
      time: "7:30 PM",
    });
  });

  it("accepts seconds in the ISO string", () => {
    expect(formatNaiveDateTime("2026-01-01T00:00:00")).toEqual({
      weekday: "Thursday",
      date: "Jan 1, 2026",
      time: "12:00 AM",
    });
  });

  it("returns empty parts for malformed input", () => {
    expect(formatNaiveDateTime("not-a-datetime")).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
  });

  it("returns empty parts for missing input", () => {
    expect(formatNaiveDateTime(undefined)).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
    expect(formatNaiveDateTime(null)).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
    expect(formatNaiveDateTime("")).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
  });

  it("rejects timezone-qualified ISO strings", () => {
    expect(formatNaiveDateTime("2026-09-04T19:30:00Z")).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
    expect(formatNaiveDateTime("2026-09-04T19:30:00-04:00")).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
  });

  it("returns empty parts for impossible calendar dates", () => {
    expect(formatNaiveDateTime("2026-02-30T12:00:00")).toEqual({
      weekday: "",
      date: "",
      time: "",
    });
  });
});
