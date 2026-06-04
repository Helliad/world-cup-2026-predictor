// Horizontal probability bar (§7.4). Always paired with the numeric value by
// callers; the percentage is baked into the aria-label so it is announced too.
// Fill grows from zero — never a misleading baseline.

interface BarProps {
  value: number; // 0..1
  ariaLabel: string;
  tone?: "accent" | "warning";
}

export function Bar({ value, ariaLabel, tone = "accent" }: BarProps) {
  const w = Math.max(0, Math.min(100, value * 100));
  const fill = tone === "warning" ? "bg-warning" : "bg-prob-fill";
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
      role="img"
      aria-label={ariaLabel}
    >
      <div
        className={`h-full rounded-full ${fill} transition-[width] duration-300 ease-out motion-reduce:transition-none`}
        style={{ width: `${w}%` }}
      />
    </div>
  );
}
