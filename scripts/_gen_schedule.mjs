// One-off generator for data/schedule.json — the authoritative 104-match
// schedule. Group rows derive from data/groups.json (this repo's official
// membership/dates/host); knockout rows (73-104) carry the official FIFA
// dates/venues and the bracket feeds. Run: node scripts/_gen_schedule.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const groups = JSON.parse(readFileSync(join(ROOT, "data", "groups.json"), "utf-8"));

// --- group rows: number 1..72 in (date, group, home) order for a stable id ---
const gf = [...groups.fixtures].sort(
  (a, b) =>
    a.date.localeCompare(b.date) || a.group.localeCompare(b.group) || a.home.localeCompare(b.home),
);
const groupRows = gf.map((f, i) => ({
  match: i + 1,
  round: "group",
  date: f.date,
  group: f.group,
  home: f.home,
  away: f.away,
  host: f.home_advantage, // team name with co-host home advantage, else null
  venue: { country: f.country }, // host nation; city/stadium not modelled for group games
}));

// --- knockout rows: official FIFA schedule (dates, venues, slot feeds) ---
// top_label/bottom_label are official slot descriptors. feeds lists the source
// match numbers (R16+); participants are resolved from results as they are
// played (winner/runner from group standings, "Winner Match N" from feeds).
const V = (city, stadium, country) => ({ city, stadium, country });
const ko = [
  // Round of 32 (match 73..88)
  { match: 73, round: "r32", date: "2026-06-28", venue: V("Inglewood", "SoFi Stadium", "United States"), top_label: "Runner-up Group A", bottom_label: "Runner-up Group B" },
  { match: 74, round: "r32", date: "2026-06-29", venue: V("Foxborough", "Gillette Stadium", "United States"), top_label: "Winner Group E", bottom_label: "3rd Group A/B/C/D/F" },
  { match: 75, round: "r32", date: "2026-06-29", venue: V("Guadalupe", "Estadio BBVA", "Mexico"), top_label: "Winner Group F", bottom_label: "Runner-up Group C" },
  { match: 76, round: "r32", date: "2026-06-29", venue: V("Houston", "NRG Stadium", "United States"), top_label: "Winner Group C", bottom_label: "Runner-up Group F" },
  { match: 77, round: "r32", date: "2026-06-30", venue: V("East Rutherford", "MetLife Stadium", "United States"), top_label: "Winner Group I", bottom_label: "3rd Group C/D/F/G/H" },
  { match: 78, round: "r32", date: "2026-06-30", venue: V("Arlington", "AT&T Stadium", "United States"), top_label: "Runner-up Group E", bottom_label: "Runner-up Group I" },
  { match: 79, round: "r32", date: "2026-06-30", venue: V("Mexico City", "Estadio Azteca", "Mexico"), top_label: "Winner Group A", bottom_label: "3rd Group C/E/F/H/I" },
  { match: 80, round: "r32", date: "2026-07-01", venue: V("Atlanta", "Mercedes-Benz Stadium", "United States"), top_label: "Winner Group L", bottom_label: "3rd Group E/H/I/J/K" },
  { match: 81, round: "r32", date: "2026-07-01", venue: V("Santa Clara", "Levi's Stadium", "United States"), top_label: "Winner Group D", bottom_label: "3rd Group B/E/F/I/J" },
  { match: 82, round: "r32", date: "2026-07-01", venue: V("Seattle", "Lumen Field", "United States"), top_label: "Winner Group G", bottom_label: "3rd Group A/E/H/I/J" },
  { match: 83, round: "r32", date: "2026-07-02", venue: V("Toronto", "BMO Field", "Canada"), top_label: "Runner-up Group K", bottom_label: "Runner-up Group L" },
  { match: 84, round: "r32", date: "2026-07-02", venue: V("Inglewood", "SoFi Stadium", "United States"), top_label: "Winner Group H", bottom_label: "Runner-up Group J" },
  { match: 85, round: "r32", date: "2026-07-02", venue: V("Vancouver", "BC Place", "Canada"), top_label: "Winner Group B", bottom_label: "3rd Group E/F/G/I/J" },
  { match: 86, round: "r32", date: "2026-07-03", venue: V("Miami Gardens", "Hard Rock Stadium", "United States"), top_label: "Winner Group J", bottom_label: "Runner-up Group H" },
  { match: 87, round: "r32", date: "2026-07-03", venue: V("Kansas City", "Arrowhead Stadium", "United States"), top_label: "Winner Group K", bottom_label: "3rd Group D/E/I/J/L" },
  { match: 88, round: "r32", date: "2026-07-03", venue: V("Arlington", "AT&T Stadium", "United States"), top_label: "Runner-up Group D", bottom_label: "Runner-up Group G" },
  // Round of 16 (89..96)
  { match: 89, round: "r16", date: "2026-07-04", venue: V("Philadelphia", "Lincoln Financial Field", "United States"), top_label: "Winner Match 74", bottom_label: "Winner Match 77", feeds: [74, 77] },
  { match: 90, round: "r16", date: "2026-07-04", venue: V("Houston", "NRG Stadium", "United States"), top_label: "Winner Match 73", bottom_label: "Winner Match 75", feeds: [73, 75] },
  { match: 91, round: "r16", date: "2026-07-05", venue: V("East Rutherford", "MetLife Stadium", "United States"), top_label: "Winner Match 76", bottom_label: "Winner Match 78", feeds: [76, 78] },
  { match: 92, round: "r16", date: "2026-07-05", venue: V("Mexico City", "Estadio Azteca", "Mexico"), top_label: "Winner Match 79", bottom_label: "Winner Match 80", feeds: [79, 80] },
  { match: 93, round: "r16", date: "2026-07-06", venue: V("Arlington", "AT&T Stadium", "United States"), top_label: "Winner Match 83", bottom_label: "Winner Match 84", feeds: [83, 84] },
  { match: 94, round: "r16", date: "2026-07-06", venue: V("Seattle", "Lumen Field", "United States"), top_label: "Winner Match 81", bottom_label: "Winner Match 82", feeds: [81, 82] },
  { match: 95, round: "r16", date: "2026-07-07", venue: V("Atlanta", "Mercedes-Benz Stadium", "United States"), top_label: "Winner Match 86", bottom_label: "Winner Match 88", feeds: [86, 88] },
  { match: 96, round: "r16", date: "2026-07-07", venue: V("Vancouver", "BC Place", "Canada"), top_label: "Winner Match 85", bottom_label: "Winner Match 87", feeds: [85, 87] },
  // Quarter-finals (97..100)
  { match: 97, round: "qf", date: "2026-07-09", venue: V("Foxborough", "Gillette Stadium", "United States"), top_label: "Winner Match 89", bottom_label: "Winner Match 90", feeds: [89, 90] },
  { match: 98, round: "qf", date: "2026-07-10", venue: V("Inglewood", "SoFi Stadium", "United States"), top_label: "Winner Match 93", bottom_label: "Winner Match 94", feeds: [93, 94] },
  { match: 99, round: "qf", date: "2026-07-11", venue: V("Miami Gardens", "Hard Rock Stadium", "United States"), top_label: "Winner Match 91", bottom_label: "Winner Match 92", feeds: [91, 92] },
  { match: 100, round: "qf", date: "2026-07-11", venue: V("Kansas City", "Arrowhead Stadium", "United States"), top_label: "Winner Match 95", bottom_label: "Winner Match 96", feeds: [95, 96] },
  // Semi-finals (101..102)
  { match: 101, round: "sf", date: "2026-07-14", venue: V("Arlington", "AT&T Stadium", "United States"), top_label: "Winner Match 97", bottom_label: "Winner Match 98", feeds: [97, 98] },
  { match: 102, round: "sf", date: "2026-07-15", venue: V("Atlanta", "Mercedes-Benz Stadium", "United States"), top_label: "Winner Match 99", bottom_label: "Winner Match 100", feeds: [99, 100] },
  // Third place + Final (103..104)
  { match: 103, round: "third", date: "2026-07-18", venue: V("Miami Gardens", "Hard Rock Stadium", "United States"), top_label: "Loser Match 101", bottom_label: "Loser Match 102", feeds: [101, 102] },
  { match: 104, round: "final", date: "2026-07-19", venue: V("East Rutherford", "MetLife Stadium", "United States"), top_label: "Winner Match 101", bottom_label: "Winner Match 102", feeds: [101, 102] },
];

const out = {
  meta: {
    source:
      "Group rows from data/groups.json (official membership/dates/host). Knockout rows: official FIFA 2026 schedule (dates, venues, bracket feeds). Group match numbers are stable internal ids in (date, group, home) order and need not match FIFA's published 1-72 labels; knockout numbers 73-104 are FIFA's.",
    rounds: ["group", "r32", "r16", "qf", "sf", "third", "final"],
    note: "Knockout participants are decided by results; until then the UI shows the official slot descriptors (top_label/bottom_label) and provisional projected occupants from the simulation.",
  },
  matches: [...groupRows, ...ko],
};

writeFileSync(join(ROOT, "data", "schedule.json"), JSON.stringify(out, null, 2) + "\n");
console.log(`wrote data/schedule.json: ${out.matches.length} matches (${groupRows.length} group + ${ko.length} knockout)`);
