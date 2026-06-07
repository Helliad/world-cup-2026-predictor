import { useMemo } from "react";
import { BracketSlot } from "../components/BracketSlot";
import { Explainer } from "../components/Explainer";
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
        <div className="flex min-w-max gap-3 pb-4">
          {proj.rounds.map((nodes, r) => (
            <div key={r} className="flex w-48 flex-col">
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
