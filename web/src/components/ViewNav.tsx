import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { REPO_URL } from "../lib/site";
import { useStore } from "../store/store";

// Primary data views (left of the bar).
const VIEW_TABS = [
  { to: "/title", label: "Title Race", end: false },
  { to: "/groups", label: "Groups", end: false },
  { to: "/schedule", label: "Schedule", end: false },
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
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Close the mobile menu whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const sourceLink = (
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
  );

  const themeButton = (
    <button
      type="button"
      onClick={toggle}
      className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted hover:text-text"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur">
      <div className="mx-auto flex min-h-14 max-w-5xl items-center gap-x-3 gap-y-1 px-4 py-2 md:flex-wrap">
        <NavLink to="/" className="text-step-1 font-extrabold tracking-tight">
          WC<span className="text-accent">26</span>
        </NavLink>

        {/* Desktop: inline primary views. */}
        <nav className="hidden gap-1 text-sm md:flex" aria-label="Primary views">
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

        {/* Desktop: inline info links + theme toggle. */}
        <div className="ml-auto hidden items-center gap-1 text-sm md:flex">
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
            {sourceLink}
          </nav>
          {themeButton}
        </div>

        {/* Mobile: theme toggle stays visible, links live behind the hamburger. */}
        <div className="ml-auto flex items-center gap-1 md:hidden">
          {themeButton}
          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            className="rounded-md border border-border p-2 text-muted hover:text-text"
            aria-label="Toggle navigation menu"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {menuOpen ? (
                <path d="M6 6 18 18M18 6 6 18" />
              ) : (
                <path d="M3 6h18M3 12h18M3 18h18" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile: collapsible panel with all nav links. */}
      {menuOpen && (
        <nav
          id="mobile-nav"
          className="flex flex-col gap-1 border-t border-border px-4 py-3 text-sm md:hidden"
          aria-label="Primary navigation"
        >
          {[...VIEW_TABS, ...INFO_TABS].map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={"end" in t ? (t as { end: boolean }).end : undefined}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 font-medium transition-colors ${
                  isActive ? "bg-surface-2 text-text" : "text-muted hover:text-text"
                }`
              }
            >
              {t.label}
            </NavLink>
          ))}
          <div className="px-3 py-2">{sourceLink}</div>
        </nav>
      )}
    </header>
  );
}
