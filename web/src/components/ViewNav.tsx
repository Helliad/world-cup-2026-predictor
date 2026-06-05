import { NavLink } from "react-router-dom";
import { REPO_URL } from "../lib/site";
import { useStore } from "../store/store";

// Primary data views (left of the bar).
const VIEW_TABS = [
  { to: "/", label: "Title Race", end: true },
  { to: "/groups", label: "Groups", end: false },
  { to: "/fixtures", label: "Fixtures", end: false },
  { to: "/bracket", label: "Bracket", end: false },
];

// Secondary project/info links (right of the bar, with the theme toggle).
const INFO_TABS = [
  { to: "/about", label: "How it's made" },
  { to: "/faq", label: "FAQ" },
];

export function ViewNav() {
  const theme = useStore((s) => s.theme);
  const toggle = useStore((s) => s.toggleTheme);
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur">
      <div className="mx-auto flex min-h-14 max-w-5xl flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2">
        <NavLink to="/" className="text-step-1 font-extrabold tracking-tight">
          WC<span className="text-accent">26</span>
        </NavLink>
        <nav className="flex gap-1 text-sm" aria-label="Primary views">
          {VIEW_TABS.map((t) => (
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

        <div className="ml-auto flex items-center gap-1 text-sm">
          <nav className="flex items-center gap-1" aria-label="About this project">
            {INFO_TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-md px-2.5 py-1.5 transition-colors ${
                    isActive ? "bg-surface-2 text-text" : "text-muted hover:text-text"
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 whitespace-nowrap rounded-md px-2.5 py-1.5 text-muted transition-colors hover:text-text"
            >
              Source code
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="h-3 w-3"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M7 17 17 7M9 7h8v8" />
              </svg>
            </a>
          </nav>
          <button
            type="button"
            onClick={toggle}
            className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted hover:text-text"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </div>
    </header>
  );
}
