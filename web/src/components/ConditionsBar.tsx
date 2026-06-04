import { useStore } from "../store/store";
import { useProbabilities } from "../store/useProbabilities";

// The persistent "what if" conditions bar (§7.6): visible, each chip removable,
// a reset, and an honest sample-size readout that turns into a warning when the
// matching subset is too small to trust.
export function ConditionsBar() {
  const conditions = useStore((s) => s.conditions);
  const remove = useStore((s) => s.removeCondition);
  const clear = useStore((s) => s.clearConditions);
  const dp = useProbabilities();

  if (conditions.length === 0) return null;

  return (
    <div className="sticky top-14 z-20 border-b border-accent/30 bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2 px-4 py-2">
        <span className="text-xs font-bold uppercase tracking-wide text-accent">What if</span>
        {conditions.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => remove(c.id)}
            className="group inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs font-medium text-accent hover:bg-accent/20"
          >
            {c.label}
            <span aria-hidden="true" className="text-accent/60 group-hover:text-accent">
              ✕
            </span>
            <span className="sr-only">(remove condition)</span>
          </button>
        ))}
        <button
          type="button"
          onClick={clear}
          className="ml-auto text-xs text-muted underline underline-offset-2 hover:text-text"
        >
          reset all
        </button>
        <p
          className={`w-full text-[0.72rem] ${dp.lowConfidence ? "font-medium text-warning" : "text-muted"}`}
        >
          {dp.lowConfidence
            ? `Only ${dp.count} of ${dp.total.toLocaleString()} simulations match — too few for a precise number. Try removing a condition.`
            : `${dp.count.toLocaleString()} of ${dp.total.toLocaleString()} simulations match. All probabilities below are conditional on these outcomes.`}
        </p>
      </div>
    </div>
  );
}
