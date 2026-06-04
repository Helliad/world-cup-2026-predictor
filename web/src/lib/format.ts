// Small presentation helpers. Percentages are rounded consistently (§7.4).

export const pct = (p: number, decimals = 1): string => `${(p * 100).toFixed(decimals)}%`;

export function teamAbbr(team: string): string {
  const cleaned = team.replace(/[^A-Za-z ]/g, "");
  const words = cleaned.split(" ").filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0] + (words[1][1] ?? "")).toUpperCase();
  return cleaned.slice(0, 3).toUpperCase();
}

export const CONFIDENCE_TEXT: Record<string, string> = {
  high: "High data confidence",
  medium: "Medium data confidence — thinner recent record",
  low: "Low data confidence — sparse data, leans on prior",
};
