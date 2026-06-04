import { CONFIDENCE_TEXT } from "../lib/format";
import type { DataConfidence } from "../types";

// Honest labelling of thin-data teams (§4.4, §7). High confidence is the norm,
// so only medium/low are surfaced, to keep the UI quiet.
export function ConfidenceTag({ level }: { level: DataConfidence }) {
  if (level === "high") return null;
  return (
    <span
      title={CONFIDENCE_TEXT[level]}
      className="rounded border border-warning/40 px-1 text-[0.6rem] font-semibold uppercase tracking-wide text-warning"
    >
      {level} data
    </span>
  );
}
