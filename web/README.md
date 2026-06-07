# `web/` — the frontend

A static **React + Vite + TypeScript + Tailwind** app that reads one
`public/predictions.json` (and a compact `outcomes_sample.json`) and never calls
Python at runtime. Positioned as a polished, editorial predictions microsite —
screenshot-worthy by design.

## Develop / build / deploy

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # tsc -b && vite build -> dist/  (also typechecks)
npm run preview    # serve the production build
```

`predictions.json` + `outcomes_sample.json` live in `public/` and are produced by
`python -m scripts.run_pipeline`. To refresh the site's data, re-run the pipeline
and rebuild.

**Hosting.** `vite.config.ts` uses `base: "./"` (relative assets) and the app uses
`HashRouter`, so the static bundle works at a domain root or any project subpath
with **no server rewrites / `_redirects` file**. The model never runs online — only
the precomputed `predictions.json` + `outcomes_sample.json` are served.

- **GitHub Pages (already wired):** [`../.github/workflows/pages.yml`](../.github/workflows/pages.yml)
  runs `npm ci && npm run build` and publishes `dist/` on every push to `main`.
  One-time: **repo Settings → Pages → Source = “GitHub Actions”**, then re-run it.
- **Cloudflare Pages / other static hosts:** Root directory `web`, build command
  `npm run build`, output `dist`, env `NODE_VERSION=20` (pinned in [`.nvmrc`](.nvmrc)).
  On Cloudflare you can add a `public/_headers` file to cache the hashed `/assets/*`
  immutably while keeping the fixed-name JSON on a short TTL.

## Views & user journey

`/` **Title Race** (landing + share target) → `/groups` → `/bracket` →
`/team/:id` (drill-down), plus the cross-cutting **"What if"** overlay. Land on
the Title Race, recognise a team, drill in or jump to the bracket, pin a "what
if", share the URL.

## Design tokens (§7.7)

Semantic CSS variables in `src/index.css`, exposed to Tailwind in
`tailwind.config.js`. One accent encodes "probability/positive"; everything else
is a restrained neutral palette. Light + dark supported (`class` strategy).

| Token | Meaning |
|-------|---------|
| `--surface`, `--surface-2` | page / raised surfaces |
| `--border` | hairlines |
| `--text`, `--muted` | primary / secondary text |
| `--accent`, `--prob-fill` | probability / positive accent |
| `--warning` | low-confidence / uncertainty |

Type is a 6-step modular scale (`text-step-0` … `text-step-6`, ratio 1.25).

**Visualization standards:** probability bars are hand-rolled flex/SVG; the
numeric percentage is **always shown as text** beside the bar (and baked into the
bar's `aria-label`, so it is announced too). Bars start at zero — no misleading
baselines, no 3D, one-decimal rounding throughout.

## Component system (`src/components/`)

`Bar`, `ProbabilityValue`, `TeamBadge`, `ConfidenceTag`, `StatCallout`,
`TeamRow`, `GroupTable`, `BracketSlot`, `ConditionsBar`, `ViewNav`, `Footer` —
each small, typed, and single-purpose.

## State (`src/store/`)

A single Zustand store holds the loaded artifacts, theme, and the pinned "what if"
conditions. Derived probabilities come from a **memoized selector**
(`useProbabilities`), never stored redundantly: with no conditions it returns the
precise 100k marginals from `predictions.json`; with conditions it returns exact
conditional frequencies from `recompute`.

## "What if" internals (§7.6) — the signature feature

The pipeline ships a compact sample of full tournament outcomes
(`outcomes_sample.json`): for ~8,000 sims, each team's furthest-stage code, each
team's group finish, and the 32 Round-of-32 slot occupants — base64-encoded
`Uint8Array`s (~1.3 MB total).

- **Recompute** (`lib/recompute.ts`): pinning a condition (e.g. "Brazil reach the
  final") filters the sample to the matching subset and recomputes every team's
  stage probabilities as exact conditional frequencies — pure counting, no model
  in the browser, instant.
- **Bracket projection** (`lib/bracket.ts`): every sim's full knockout tree is
  reconstructed by folding the 32 slot occupants (at each node the team whose
  furthest-stage code reaches that round is the one that advanced). Tallying gives
  each slot's most-likely occupant and its exact probability — and it recomputes
  under conditions too.
- **Honesty guardrail:** if fewer than 200 sims match the pinned conditions, the
  UI shows a low-confidence warning instead of a falsely precise number.
- **Shareable scenarios:** pinned conditions are encoded in the URL query
  (`?pin=Team:kind,…`), so a forced-scenario view is itself a shareable link.

## Accessibility

Semantic HTML, WCAG-AA-minded contrast, keyboard navigation with visible focus
rings, ARIA labels on bars and controls (the percentage is announced), and
`prefers-reduced-motion` respected (the only meaningful motion — bars
growing/shrinking on a "what if" recompute — is disabled under reduced motion).
