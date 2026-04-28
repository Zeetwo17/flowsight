import { useEffect, useState } from "react";
import MapView from "./components/MapView";
import CascadeChart from "./components/CascadeChart";
import KPIBar from "./components/KPIBar";
import RouteCompare from "./components/RouteCompare";
import EventLog from "./components/EventLog";
import ExplanationPanel from "./components/ExplanationPanel";
import Sidebar from "./components/Sidebar";
import { runSimulation, explainRoute } from "./api";
import type { SimulateRequest, SimulationDTO, ExplanationDTO } from "./types";

const DEFAULTS: SimulateRequest = {
  n_nodes: 20,
  seed: 42,
  horizon_minutes: 120,
  n_disruptions: 4,
  risk_weight: 5,
  random_disruptions: true
};

export default function App() {
  const [params, setParams] = useState<SimulateRequest>(DEFAULTS);
  const [sim, setSim] = useState<SimulationDTO | null>(null);
  const [explanation, setExplanation] = useState<ExplanationDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    refresh();
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
