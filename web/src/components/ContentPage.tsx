import type { ReactNode } from "react";

// Shared wrapper for the long-form informational pages (About / FAQ / Privacy /
// Terms). Children are plain semantic HTML styled by the `.content` rules in
// index.css, so each page reads as a clean document.
export function ContentPage({
  title,
  lead,
  updated,
  children,
}: {
  title: string;
  lead?: ReactNode;
  updated?: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-step-5 font-extrabold tracking-tight">{title}</h1>
      {lead && <p className="mt-2 text-step-1 text-muted">{lead}</p>}
      {updated && <p className="mt-2 text-xs text-muted">Last updated: {updated}</p>}
      <div className="content mt-6">{children}</div>
    </div>
  );
}
