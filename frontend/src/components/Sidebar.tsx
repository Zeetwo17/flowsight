import type { ReactNode } from "react";
import type { SimulateRequest } from "../types";

interface Props {
  params: SimulateRequest;
  onChange: (p: SimulateRequest) => void;
  onRun: () => void;
  onExplain: () => void;
  loading: boolean;
}

export default function Sidebar({ params, onChange, onRun, onExplain, loading }: Props) {
  function set<K extends keyof SimulateRequest>(k: K, v: SimulateRequest[K]) {
    onChange({ ...params, [k]: v });
  }

  return (
    <aside className="bg-ink2 border-r border-slate-700 p-4 flex flex-col gap-4">
      <h2 className="font-semibold">Scenario</h2>

      <Field label={`Backbone nodes: ${params.n_nodes}`}>
        <input
          type="range" min={10} max={40}
          value={params.n_nodes}
          onChange={(e) => set("n_nodes", parseInt(e.target.value))}
          className="w-full"
        />
      </Field>

      <Field label={`Horizon: ${params.horizon_minutes} min`}>
        <input
          type="range" min={30} max={240}
          value={params.horizon_minutes}
          onChange={(e) => set("horizon_minutes", parseInt(e.target.value))}
          className="w-full"
        />
      </Field>

      <Field label={`Disruptions: ${params.n_disruptions}`}>
        <input
          type="range" min={1} max={12}
          value={params.n_disruptions}
          onChange={(e) => set("n_disruptions", parseInt(e.target.value))}
          className="w-full"
        />
      </Field>

      <Field label={`λ (risk weight): ${params.risk_weight.toFixed(1)}`}>
        <input
          type="range" min={0} max={20} step={0.5}
          value={params.risk_weight}
          onChange={(e) => set("risk_weight", parseFloat(e.target.value))}
          className="w-full"
        />
      </Field>

      <Field label={`Seed`}>
        <input
          type="number"
          value={params.seed}
          onChange={(e) => set("seed", parseInt(e.target.value || "0"))}
          className="w-full bg-ink border border-slate-600 rounded px-2 py-1 text-sm"
        />
      </Field>

      <button
        disabled={loading}
        onClick={onRun}
        className="bg-accent hover:bg-blue-600 disabled:bg-slate-700 px-3 py-2 rounded text-sm font-medium"
      >
        {loading ? "Running..." : "Run simulation"}
      </button>

      <button
        disabled={loading}
        onClick={onExplain}
        className="bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 px-3 py-2 rounded text-sm"
      >
        Explain reroute (Gemini)
      </button>

      <div className="mt-auto text-xs text-slate-400 leading-relaxed">
        <p>
          <strong>Pipeline:</strong> Hawkes (NeurIPS 2017) → HMM (Rabiner 1989) →
          Risk-aware Dijkstra · CVaR (Rockafellar & Uryasev 2000)
        </p>
        <p className="mt-2">
          Set <code>GEMINI_API_KEY</code> on the backend for live LLM explanations.
        </p>
      </div>
    </aside>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-300">{label}</span>
      {children}
    </label>
  );
}
