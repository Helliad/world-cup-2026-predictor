import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { BracketSlot } from "../components/BracketSlot";
import { Explainer } from "../components/Explainer";
import { ROUND_NAMES, projectBracket } from "../lib/bracket";
import { useStore } from "../store/store";

type Seg = { x1: number; y1: number; x2: number; y2: number };

// Projected knockout tree (§7.2): most-likely occupant of each slot with the
// probability that team reaches it. Reconstructed from the simulation sample, so
// it recomputes exactly under pinned "what if" conditions. Horizontally scrollable.
export function Bracket() {
  const outcomes = useStore((s) => s.outcomes);
  const conditions = useStore((s) => s.conditions);
  const proj = useMemo(
    () => (outcomes ? projectBracket(outcomes, conditions) : null),
    [outcomes, conditions],
  );

  // Connector lines linking each pair of slots to the slot they feed in the next
  // round. Measured from the laid-out DOM (exact regardless of font/row heights)
  // and recomputed on any resize. Drawn behind the slots as an SVG overlay.
  const contentRef = useRef<HTMLDivElement>(null);
  const slotRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [segs, setSegs] = useState<Seg[]>([]);

  useLayoutEffect(() => {
    const container = contentRef.current;
    if (!container || !proj) return;
    const compute = () => {
      const c = container.getBoundingClientRect();
      const box = (r: number, i: number) => {
        const el = slotRefs.current[`${r}-${i}`];
        if (!el) return null;
        const b = el.getBoundingClientRect();
        return { left: b.left - c.left, right: b.right - c.left, cy: b.top - c.top + b.height / 2 };
      };
      const out: Seg[] = [];
      for (let r = 0; r < proj.rounds.length - 1; r++) {
        for (let j = 0; j < proj.rounds[r + 1].length; j++) {
          const a = box(r, 2 * j);
          const b = box(r, 2 * j + 1);
          const p = box(r + 1, j);
          if (!a || !b || !p) continue;
          const midX = (a.right + p.left) / 2;
          out.push({ x1: a.right, y1: a.cy, x2: midX, y2: a.cy }); // upper child → bus
          out.push({ x1: b.right, y1: b.cy, x2: midX, y2: b.cy }); // lower child → bus
          out.push({ x1: midX, y1: a.cy, x2: midX, y2: b.cy }); // vertical bus
          out.push({ x1: midX, y1: p.cy, x2: p.left, y2: p.cy }); // bus → parent
        }
      }
      setSegs(out);
    };
    compute();
    const ro = new ResizeObserver(compute);
    ro.observe(container);
    return () => ro.disconnect();
  }, [proj]);

  if (!outcomes || !proj) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 text-muted">Loading bracket sample…</div>
    );
  }

  return (
    <div className="px-4 py-6">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-step-4 font-extrabold">Projected bracket</h1>
        <p className="mt-1 text-muted">
          The most-likely team in each knockout slot, with its probability of reaching that slot.
          Tap <span className="text-text">☆</span> to assume a team advances. Scroll sideways →
        </p>

        <div className="mt-4">
          <Explainer title="How the bracket and “what if” work — read this if a star looks surprising">
            <p>
              Each slot shows the team <strong>most likely</strong> to fill that position, and the
              number is its probability of reaching that slot across the simulated tournaments. The
              same team can appear in different Round-of-32 slots in different simulations, because
              where it lands depends on whether it wins its group, finishes second, or sneaks through
              as one of the eight best third-placed teams.
            </p>
            <p>
              <strong>The star pins an assumption.</strong> Starring a team in the Round-of-32 column
              pins “this team reaches the Round of 16” (it wins its first knockout tie); starring it
              further right assumes it reaches that round. Every number then recomputes using{" "}
              <em>only</em> the simulations where your assumption held — exact conditional probability,
              not the model re-running.
            </p>
            <p>
              <strong>Why a small-looking star can move everything.</strong> Take “England reach the
              Round of 16”. It sounds minor, but England only get there in about <strong>55%</strong>{" "}
              of simulations — so pinning it throws away the other ~45% (where they're already
              eliminated) and roughly <strong>doubles</strong> every later-round figure. Their title
              chance jumps from ~6% to ~10%. That isn't a glitch: you've assumed they survive the
              round they most often go out in.
            </p>
            <p>
              <strong>It usually doesn't crown them.</strong> After pinning England, the champion slot
              still shows the overall favourite (Argentina) — England only becomes the likeliest{" "}
              <em>finalist from its own half</em>. Watch the numbers along a pinned team's path: they{" "}
              <em>fall</em> (e.g. 65% → 41% → 24%), they don't climb to the trophy.
            </p>
            <p>
              If too few simulations match your pinned conditions, the bar at the top warns you
              instead of showing a falsely precise number.
            </p>
          </Explainer>
        </div>
      </div>
      <div className="mx-auto mt-5 max-w-7xl overflow-x-auto">
        <div ref={contentRef} className="relative flex min-w-max gap-6 pb-4">
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full overflow-visible"
            aria-hidden="true"
          >
            {segs.map((s, i) => (
              <line
                key={i}
                x1={s.x1}
                y1={s.y1}
                x2={s.x2}
                y2={s.y2}
                className="stroke-border"
                strokeWidth={1.5}
              />
            ))}
          </svg>
          {proj.rounds.map((nodes, r) => (
            <div key={r} className="relative z-10 flex w-48 flex-col">
              <div className="mb-2 text-center text-[0.7rem] font-bold uppercase tracking-wide text-muted">
                {ROUND_NAMES[r]}
              </div>
              <div className="flex h-full flex-col justify-around gap-1.5">
                {nodes.map((node, i) => (
                  <div
                    key={i}
                    ref={(el) => {
                      slotRefs.current[`${r}-${i}`] = el;
                    }}
                  >
                    <BracketSlot node={node} round={r} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
