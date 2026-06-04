import { useMemo } from "react";
import { BracketSlot } from "../components/BracketSlot";
import { ROUND_NAMES, projectBracket } from "../lib/bracket";
import { useStore } from "../store/store";

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

  if (!outcomes || !proj) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10 text-muted">Loading bracket sample…</div>
    );
  }

  return (
    <div className="px-4 py-6">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-step-4 font-extrabold">Projected bracket</h1>
        <p className="mt-1 text-muted">
          The most-likely team in each knockout slot, with its probability of reaching that slot.
          Tap <span className="text-text">☆</span> to assume a team advances. Scroll sideways →
        </p>
      </div>
      <div className="mx-auto mt-5 max-w-5xl overflow-x-auto">
        <div className="flex min-w-max gap-3 pb-4">
          {proj.rounds.map((nodes, r) => (
            <div key={r} className="flex w-44 flex-col">
              <div className="mb-2 text-center text-[0.7rem] font-bold uppercase tracking-wide text-muted">
                {ROUND_NAMES[r]}
              </div>
              <div className="flex h-full flex-col justify-around gap-1.5">
                {nodes.map((node, i) => (
                  <BracketSlot key={i} node={node} round={r} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
