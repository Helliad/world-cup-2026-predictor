import { useEffect } from "react";
import { Route, Routes, useSearchParams } from "react-router-dom";
import { ConditionsBar } from "./components/ConditionsBar";
import { Footer } from "./components/Footer";
import { ViewNav } from "./components/ViewNav";
import { parseConditions, serializeConditions } from "./lib/recompute";
import { About } from "./routes/About";
import { Bracket } from "./routes/Bracket";
import { FAQ } from "./routes/FAQ";
import { Fixtures } from "./routes/Fixtures";
import { Groups } from "./routes/Groups";
import { Landing } from "./routes/Landing";
import { MatchDetail } from "./routes/MatchDetail";
import { Privacy } from "./routes/Privacy";
import { Schedule } from "./routes/Schedule";
import { Scorecard } from "./routes/Scorecard";
import { TeamDetail } from "./routes/TeamDetail";
import { Terms } from "./routes/Terms";
import { TitleRace } from "./routes/TitleRace";
import { useStore } from "./store/store";

// Keep pinned conditions in the URL query (?pin=Team:kind,…) so a forced-scenario
// view is itself a shareable link (§7.3).
function UrlSync() {
  const [params, setParams] = useSearchParams();
  const conditions = useStore((s) => s.conditions);
  const setConditions = useStore((s) => s.setConditions);
  const predictions = useStore((s) => s.predictions);

  // URL → store, once predictions (the valid team set) are known.
  useEffect(() => {
    if (!predictions) return;
    const valid = new Set(predictions.teams.map((t) => t.team));
    const fromUrl = parseConditions(params.get("pin"), valid);
    if (serializeConditions(fromUrl) !== serializeConditions(conditions)) {
      setConditions(fromUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [predictions]);

  // store → URL, whenever conditions change.
  useEffect(() => {
    const s = serializeConditions(conditions);
    if (s !== (params.get("pin") ?? "")) {
      const next = new URLSearchParams(params);
      if (s) next.set("pin", s);
      else next.delete("pin");
      setParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conditions]);

  return null;
}

function LoadingState() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="h-8 w-2/3 animate-pulse rounded bg-surface-2" />
      <div className="mt-4 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-9 animate-pulse rounded bg-surface-2" />
        ))}
      </div>
      <p className="mt-4 text-sm text-muted">Loading predictions…</p>
    </div>
  );
}

function ErrorState({ message }: { message: string | null }) {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-step-3 font-bold">Couldn’t load the predictions</h1>
      <p className="mt-2 text-muted">{message ?? "Unknown error."}</p>
      <p className="mt-4 text-sm text-muted">
        The site reads a static <code>predictions.json</code>. If you’re running locally, generate it
        with <code>python -m scripts.run_pipeline</code> and reload.
      </p>
    </div>
  );
}

export default function App() {
  const status = useStore((s) => s.status);
  const error = useStore((s) => s.error);
  const load = useStore((s) => s.load);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex min-h-full flex-col">
      <ViewNav />
      <UrlSync />
      <ConditionsBar />
      <main className="flex-1">
        {status === "loading" && <LoadingState />}
        {status === "error" && <ErrorState message={error} />}
        {status === "ready" && (
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/title" element={<TitleRace />} />
            <Route path="/groups" element={<Groups />} />
            <Route path="/fixtures" element={<Fixtures />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/scorecard" element={<Scorecard />} />
            <Route path="/match/:match" element={<MatchDetail />} />
            <Route path="/bracket" element={<Bracket />} />
            <Route path="/team/:id" element={<TeamDetail />} />
            <Route path="/about" element={<About />} />
            <Route path="/faq" element={<FAQ />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="*" element={<Landing />} />
          </Routes>
        )}
      </main>
      <Footer />
    </div>
  );
}
