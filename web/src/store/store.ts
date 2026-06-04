// Single top-level store (§7.3). Holds the loaded artifacts, theme, and the
// pinned "what if" conditions. Derived probabilities are computed by memoized
// selectors (useProbabilities), never stored redundantly.

import { create } from "zustand";
import type { Outcomes } from "../lib/data";
import { loadOutcomes, loadPredictions } from "../lib/data";
import type { Condition } from "../lib/recompute";
import type { Predictions } from "../types";

type Status = "loading" | "ready" | "error";

interface AppState {
  status: Status;
  error: string | null;
  predictions: Predictions | null;
  outcomes: Outcomes | null;
  theme: "dark" | "light";
  conditions: Condition[];

  load: () => Promise<void>;
  toggleTheme: () => void;
  addCondition: (c: Condition) => void;
  removeCondition: (id: string) => void;
  clearConditions: () => void;
  setConditions: (c: Condition[]) => void;
}

export const useStore = create<AppState>((set, get) => ({
  status: "loading",
  error: null,
  predictions: null,
  outcomes: null,
  theme: "dark",
  conditions: [],

  load: async () => {
    try {
      // Render progressively: predictions paints the Title Race; the heavier
      // what-if sample streams in behind it.
      const predictions = await loadPredictions();
      set({ predictions, status: "ready" });
      const outcomes = await loadOutcomes();
      set({ outcomes });
    } catch (e) {
      set({ status: "error", error: e instanceof Error ? e.message : String(e) });
    }
  },

  toggleTheme: () => {
    const theme = get().theme === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", theme === "dark");
    set({ theme });
  },

  addCondition: (c) => {
    if (get().conditions.some((x) => x.id === c.id)) return;
    set({ conditions: [...get().conditions, c] });
  },
  removeCondition: (id) => set({ conditions: get().conditions.filter((c) => c.id !== id) }),
  clearConditions: () => set({ conditions: [] }),
  setConditions: (c) => set({ conditions: c }),
}));
