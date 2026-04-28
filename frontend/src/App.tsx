import { useEffect, useState } from "react";
import MapView from "./components/MapView";
import CascadeChart from "./components/CascadeChart";
import KPIBar from "./components/KPIBar";
import RouteCompare from "./components/RouteCompare";
import EventLog from "./components/EventLog";
import ExplanationPanel from "./components/ExplanationPanel";
import Sidebar from "./components/Sidebar";
import { runSimulation, explainRoute, pingHealth } from "./api";
import type { SimulateRequest, SimulationDTO, ExplanationDTO } from "./types";

const DEFAULTS: SimulateRequest = {
  n_nodes: 20,
  seed: 42,
  horizon_minutes: 120,
  n_disruptions: 4,
  risk_weight: 5,
  random_disruptions: true
};

type WakeStatus = "idle" | "waking" | "ready" | "down";

export default function App() {
  const [params, setParams] = useState<SimulateRequest>(DEFAULTS);
  const [sim, setSim] = useState<SimulationDTO | null>(null);
  const [explanation, setExplanation] = useState<ExplanationDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wake, setWake] = useState<WakeStatus>("idle");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const result = await runSimulation(params);
      setSim(result);
      setExplanation(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function explain() {
    setLoading(true);
    try {
      const r = await explainRoute(params);
      setExplanation(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // On mount: probe /health first. If backend is awake, auto-run simulation.
  // If asleep, just show a "waking up" banner — let the user click Run when ready.
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      setWake("waking");
      const t0 = performance.now();
      // Up to 4 attempts to wake the backend (Render cold start can be 30-90s).
      for (let i = 0; i < 4; i++) {
        if (cancelled) return;
        const ok = await pingHealth();
        if (ok) {
          if (cancelled) return;
          setWake("ready");
          // Only auto-run if backend was already warm (< 5s probe).
          if (performance.now() - t0 < 5000) {
            refresh();
          }
          return;
        }
        await new Promise((r) => setTimeout(r, 5000));
      }
      if (!cancelled) setWake("down");
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="h-full grid grid-cols-[300px_1fr] bg-ink text-slate-100">
      <Sidebar
        params={params}
        onChange={setParams}
        onRun={refresh}
        onExplain={explain}
        loading={loading}
      />
      <main className="overflow-auto p-4 grid grid-rows-[auto_1fr_auto] gap-4">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">
              FlowSight <span className="text-slate-400 text-sm font-normal">
                · Supply chain ripple-effect mitigation
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Hawkes (cascade) → HMM (state) → Risk-aware Dijkstra (decision) ·
              CVaR-aware · Gemini-explained
            </p>
          </div>
          {sim && <KPIBar kpi={sim.kpi} />}
        </header>

        {wake === "waking" && !sim && (
          <div className="bg-amber-900/30 border border-amber-700/60 rounded p-3 text-sm">
            Waking up backend (Render free tier sleeps after 15 min idle —
            takes 30–60s to cold-start).
          </div>
        )}
        {wake === "down" && !sim && (
          <div className="bg-red-900/40 border border-red-700 rounded p-3 text-sm">
            Backend didn't respond after 4 attempts. It may still be starting up —
            click <strong>Run simulation</strong> to retry, or open
            <a className="text-accent ml-1" href="https://flowsight-api-ylyx.onrender.com/health" target="_blank" rel="noreferrer">
              /health
            </a> in a new tab.
          </div>
        )}
        {error && (
          <div className="bg-red-900/40 border border-red-700 rounded p-3 text-sm">
            {error}
          </div>
        )}

        {sim ? (
          <section className="grid grid-cols-2 gap-4 min-h-[500px]">
            <div className="bg-ink2 rounded-lg overflow-hidden border border-slate-700">
              <MapView sim={sim} />
            </div>
            <div className="grid grid-rows-2 gap-4">
              <div className="bg-ink2 rounded-lg p-3 border border-slate-700">
                <CascadeChart sim={sim} />
              </div>
              <div className="bg-ink2 rounded-lg p-3 border border-slate-700 overflow-auto">
                <RouteCompare sim={sim} />
              </div>
            </div>
          </section>
        ) : (
          <div className="flex items-center justify-center text-slate-400">
            {loading ? "Running simulation..." : "No data yet."}
          </div>
        )}

        <footer className="grid grid-cols-2 gap-4">
          {sim && <EventLog events={sim.events} />}
          <ExplanationPanel explanation={explanation} />
        </footer>
      </main>
    </div>
  );
}
