import type { ReactNode } from "react";

// A single marquee number with a label — the tournament's headline stats (§7.2).
export function StatCallout({
  label,
  value,
  sub,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-2/40 px-4 py-3">
      <div className="text-step-4 font-extrabold tabular-nums leading-none">{value}</div>
      <div className="mt-1 text-step-0 text-muted">{label}</div>
      {sub && <div className="mt-0.5 text-[0.7rem] text-muted">{sub}</div>}
    </div>
  );
}
