import type { ReactNode } from "react";
import type { SimulateRequest } from "../types";

interface Props {
  params: SimulateRequest;
  onChange: (p: SimulateRequest) => void;
  onRun: () => void;
  onExplain: () => void;
  loading: boolean;
  explaining: boolean;
}

export default function Sidebar({
  params,
  onChange,
  onRun,
  onExplain,
  loading,
  explaining
}: Props) {
  function set<K extends keyof SimulateRequest>(k: K, v: SimulateRequest[K]) {
    onChange({ ...params, [k]: v });
  }

  return (
    <aside className="bg-ink2 lg:border-r border-slate-700 p-4 flex flex-col gap-4 h-full overflow-y-auto w-[300px]">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Scenario
        </h2>
      </div>

      <Field label="Backbone nodes" value={params.n_nodes}>
        <input
          type="range"
          min={10}
          max={40}
          value={params.n_nodes}
          onChange={(e) => set("n_nodes", parseInt(e.target.value))}
          className="w-full accent-accent"
        />
      </Field>

      <Field label="Horizon" value={`${params.horizon_minutes} min`}>
        <input
          type="range"
          min={30}
          max={240}
          value={params.horizon_minutes}
          onChange={(e) => set("horizon_minutes", parseInt(e.target.value))}
          className="w-full accent-accent"
        />
      </Field>

      <Field label="Disruptions" value={params.n_disruptions}>
        <input
          type="range"
          min={1}
          max={12}
          value={params.n_disruptions}
          onChange={(e) => set("n_disruptions", parseInt(e.target.value))}
          className="w-full accent-accent"
        />
      </Field>

      <Field label="λ (risk weight)" value={params.risk_weight.toFixed(1)}>
        <input
          type="range"
          min={0}
          max={20}
          step={0.5}
          value={params.risk_weight}
          onChange={(e) => set("risk_weight", parseFloat(e.target.value))}
          className="w-full accent-accent"
        />
      </Field>

      <Field label="Seed">
        <input
          type="number"
          value={params.seed}
          onChange={(e) => set("seed", parseInt(e.target.value || "0"))}
          className="w-full bg-ink border border-slate-600 rounded px-2 py-1 text-sm text-slate-100"
        />
      </Field>

      <button
        disabled={loading}
        onClick={onRun}
        className="bg-accent hover:bg-blue-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm font-medium transition-colors"
      >
        {loading ? "Running…" : "Run simulation"}
      </button>

      <button
        disabled={explaining}
        onClick={onExplain}
        className="bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:cursor-not-allowed px-3 py-2 rounded text-sm transition-colors"
      >
        {explaining ? "Asking Gemini…" : "Explain reroute (Gemini)"}
      </button>

      <div className="mt-auto text-[11px] text-slate-500 leading-relaxed border-t border-slate-700 pt-3">
        <p className="text-slate-400 font-semibold uppercase tracking-widest text-[10px]">
          Pipeline
        </p>
        <p className="mt-1">
          <span className="text-slate-300">Hawkes</span> (NeurIPS 2017){" "}
          <span className="text-slate-500">→</span>{" "}
          <span className="text-slate-300">HMM</span> (Rabiner 1989){" "}
          <span className="text-slate-500">→</span>{" "}
          <span className="text-slate-300">Risk-aware Dijkstra</span> ·{" "}
          <span className="text-slate-300">CVaR</span> (Rockafellar 2000)
        </p>
        <p className="mt-2">
          Set <code className="bg-ink px-1 rounded text-slate-300">GEMINI_API_KEY</code> on the
          backend for live LLM explanations.
        </p>
      </div>
    </aside>
  );
}

function Field({
  label,
  value,
  children
}: {
  label: string;
  value?: string | number;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <div className="flex items-baseline justify-between">
        <span className="text-slate-300">{label}</span>
        {value !== undefined && (
          <span className="text-[11px] tabular-nums text-slate-400">{value}</span>
        )}
      </div>
      {children}
    </label>
  );
}
