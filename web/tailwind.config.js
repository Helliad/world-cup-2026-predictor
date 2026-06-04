/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Semantic tokens (§7.7) — all reference CSS variables so light/dark and
      // contributors stay consistent. Defined in src/index.css.
      colors: {
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-2": "rgb(var(--surface-2) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        text: "rgb(var(--text) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        "prob-fill": "rgb(var(--prob-fill) / <alpha-value>)",
        warning: "rgb(var(--warning) / <alpha-value>)",
      },
      // 6-step modular type scale (1.25 ratio).
      fontSize: {
        "step-0": ["0.875rem", { lineHeight: "1.25rem" }],
        "step-1": ["1rem", { lineHeight: "1.5rem" }],
        "step-2": ["1.25rem", { lineHeight: "1.75rem" }],
        "step-3": ["1.563rem", { lineHeight: "2rem" }],
        "step-4": ["1.953rem", { lineHeight: "2.25rem" }],
        "step-5": ["2.441rem", { lineHeight: "2.75rem" }],
        "step-6": ["3.052rem", { lineHeight: "3.25rem" }],
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
