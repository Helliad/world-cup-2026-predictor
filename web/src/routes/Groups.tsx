import { GroupTable } from "../components/GroupTable";
import { useStore } from "../store/store";

export function Groups() {
  const predictions = useStore((s) => s.predictions)!;
  const letters = Object.keys(predictions.groups).sort();
  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <h1 className="text-step-4 font-extrabold">Groups</h1>
      <p className="mt-1 text-muted">
        Probability each team reaches the knockout stage (top 2 of every group plus the 8 best
        third-placed teams advance). Tap <span className="text-text">top</span> to pin a “what if”.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {letters.map((l) => (
          <GroupTable key={l} letter={l} rows={predictions.groups[l]} />
        ))}
      </div>
    </div>
  );
}
