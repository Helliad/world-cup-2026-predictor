import { NavLink } from "react-router-dom";
import { useStore } from "../store/store";

const TABS = [
  { to: "/", label: "Title Race", end: true },
  { to: "/groups", label: "Groups", end: false },
  { to: "/bracket", label: "Bracket", end: false },
];

export function ViewNav() {
  const theme = useStore((s) => s.theme);
  const toggle = useStore((s) => s.toggleTheme);
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4">
        <NavLink to="/" className="text-step-1 font-extrabold tracking-tight">
          WC<span className="text-accent">26</span>
        </NavLink>
        <nav className="flex gap-1 text-sm" aria-label="Primary views">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 font-medium transition-colors ${
                  isActive ? "bg-surface-2 text-text" : "text-muted hover:text-text"
                }`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={toggle}
          className="ml-auto rounded-md border border-border px-2.5 py-1.5 text-xs text-muted hover:text-text"
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>
    </header>
  );
}
