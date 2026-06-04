import { pct } from "../lib/format";

// The numeric percentage, always shown as text beside its bar (§7.4). Tabular
// figures so columns align and screenshots read cleanly.
export function ProbabilityValue({
  p,
  decimals = 1,
  className = "",
}: {
  p: number;
  decimals?: number;
  className?: string;
}) {
  return <span className={`tabular-nums ${className}`}>{pct(p, decimals)}</span>;
}
