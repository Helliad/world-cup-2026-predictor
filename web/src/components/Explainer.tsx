import type { ReactNode } from "react";

// A collapsible "how to read this" panel. Uses native <details>/<summary> so it
// is keyboard-accessible with no JS state. Content is styled by `.content`.
export function Explainer({
  title = "How to read this",
  children,
  defaultOpen = false,
}: {
  title?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details
      className="group rounded-xl border border-border bg-surface-2/40 [&_summary::-webkit-details-marker]:hidden"
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
        <span className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="grid h-5 w-5 place-items-center rounded-full border border-accent/50 text-xs text-accent"
          >
            ?
          </span>
          {title}
        </span>
        <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <div className="content border-t border-border px-4 py-3 text-step-0">{children}</div>
    </details>
  );
}
