/** Provider-naive ISO datetime formatting without JavaScript Date parsing. */

export interface NaiveDateTimeParts {
  weekday: string;
  date: string;
  time: string;
}

const EMPTY_PARTS: NaiveDateTimeParts = {
  weekday: "",
  date: "",
  time: "",
};

const WEEKDAYS = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

const ISO_NAIVE_RE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/;

function isValidDateParts(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1) {
    return false;
  }
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month === 2) {
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return day <= (leap ? 29 : 28);
  }
  return day <= daysInMonth[month - 1];
}

/** Zeller's congruence for Gregorian calendar weekday (0 = Sunday). */
function weekdayIndex(year: number, month: number, day: number): number {
  let y = year;
  let m = month;
  if (m < 3) {
    m += 12;
    y -= 1;
  }
  const k = y % 100;
  const j = Math.floor(y / 100);
  const h = (day + Math.floor((13 * (m + 1)) / 5) + k + Math.floor(k / 4) + Math.floor(j / 4) + 5 * j) % 7;
  return ((h + 6) % 7);
}

function formatTime12Hour(hour24: number, minute: number): string {
  const suffix = hour24 >= 12 ? "PM" : "AM";
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  const minuteText = minute.toString().padStart(2, "0");
  return `${hour12}:${minuteText} ${suffix}`;
}

/**
 * Format a provider-naive ISO string such as ``2026-09-04T19:30:00``.
 *
 * Never uses ``Date``, timezone suffixes, or relative-time wording.
 */
export function formatNaiveDateTime(value: string | null | undefined): NaiveDateTimeParts {
  if (value == null || typeof value !== "string") {
    return { ...EMPTY_PARTS };
  }

  const trimmed = value.trim();
  if (!trimmed || trimmed.includes("Z") || /[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return { ...EMPTY_PARTS };
  }

  const match = ISO_NAIVE_RE.exec(trimmed);
  if (!match) {
    return { ...EMPTY_PARTS };
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
    !Number.isInteger(second) ||
    hour > 23 ||
    minute > 59 ||
    second > 59 ||
    !isValidDateParts(year, month, day)
  ) {
    return { ...EMPTY_PARTS };
  }

  const weekday = WEEKDAYS[weekdayIndex(year, month, day)];
  const date = `${MONTHS[month - 1]} ${day}, ${year}`;
  const time = formatTime12Hour(hour, minute);

  return { weekday, date, time };
}
