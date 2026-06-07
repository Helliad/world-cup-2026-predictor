// Helpers for the Schedule / Match Center views: round labels, grouping the 104
// matches by date, resolving each side's display name (actual team once known,
// otherwise the official slot descriptor), and date formatting.

import type { MatchRound, ScheduleMatch } from "../types";

export const ROUND_LABEL: Record<MatchRound, string> = {
  group: "Group stage",
  r32: "Round of 32",
  r16: "Round of 16",
  qf: "Quarter-final",
  sf: "Semi-final",
  third: "Third-place play-off",
  final: "Final",
};

export const ROUND_SHORT: Record<MatchRound, string> = {
  group: "Group",
  r32: "R32",
  r16: "R16",
  qf: "QF",
  sf: "SF",
  third: "3rd",
  final: "Final",
};

export const isKnockout = (round: MatchRound): boolean => round !== "group";

/** What to show for each side: the resolved team (preferred) or its descriptor. */
export interface MatchSides {
  homeTeam: string | null; // actual team if known, else null
  awayTeam: string | null;
  homeLabel: string; // team name, or slot descriptor like "Winner Group A"
  awayLabel: string;
  bothKnown: boolean;
}

export function matchSides(m: ScheduleMatch): MatchSides {
  const homeTeam = m.home;
  const awayTeam = m.away;
  return {
    homeTeam,
    awayTeam,
    homeLabel: homeTeam ?? m.top_label ?? "TBD",
    awayLabel: awayTeam ?? m.bottom_label ?? "TBD",
    bothKnown: !!homeTeam && !!awayTeam,
  };
}

export interface DateGroup {
  date: string; // ISO yyyy-mm-dd
  label: string; // e.g. "Thursday, 11 June 2026"
  matches: ScheduleMatch[];
}

const DATE_FMT = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const SHORT_DATE_FMT = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

/** "Thursday, 11 June 2026" for a yyyy-mm-dd string (UTC, no off-by-one). */
export const formatDate = (iso: string): string => DATE_FMT.format(new Date(`${iso}T00:00:00Z`));

/** "Thu 11 Jun" for compact rows. */
export const formatDateShort = (iso: string): string =>
  SHORT_DATE_FMT.format(new Date(`${iso}T00:00:00Z`));

/** Group the schedule by calendar date, ordered, with each day's matches by number. */
export function byDate(schedule: ScheduleMatch[]): DateGroup[] {
  const map = new Map<string, ScheduleMatch[]>();
  for (const m of schedule) {
    const list = map.get(m.date) ?? [];
    list.push(m);
    map.set(m.date, list);
  }
  return [...map.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, matches]) => ({
      date,
      label: formatDate(date),
      matches: matches.sort((a, b) => a.match - b.match),
    }));
}

/** Venue as "Stadium, City" (knockout) or just the host country (group). */
export function venueText(m: ScheduleMatch): string {
  const v = m.venue;
  if (v.stadium && v.city) return `${v.stadium}, ${v.city}`;
  return v.country;
}
