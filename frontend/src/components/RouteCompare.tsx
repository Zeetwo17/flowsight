import type { SimulationDTO } from "../types";

interface Props {
  sim: SimulationDTO;
}

export default function RouteCompare({ sim }: Props) {
  const ship = sim.shipments[0];
  if (!ship) return <div className="text-slate-400 text-sm">No shipments.</div>;

  const rows = [
    { label: "naive", route: ship.naive, color: "text-slate-300", swatch: "bg-slate-400" },
    { label: "risk-aware", route: ship.risk_aware, color: "text-accent", swatch: "bg-accent" }
  ];
  const tDelta = ship.naive.total_time - ship.risk_aware.total_time;
  const rDelta = ship.naive.total_risk - ship.risk_aware.total_risk;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-300">Route comparison</h3>
        <span className="text-[11px] text-slate-400">
          shipment {ship.source} → {ship.target}
        </span>
      </div>
      <table className="w-full text-xs">
        <thead className="text-slate-400">
          <tr className="border-b border-slate-700">
            <th className="text-left py-1.5">mode</th>
            <th className="text-right py-1.5">hops</th>
            <th className="text-right py-1.5">time (min)</th>
            <th className="text-right py-1.5">risk</th>
            <th className="text-right py-1.5">CO₂</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-slate-800/60">
              <td className={`py-1.5 font-semibold ${r.color}`}>
                <span className="inline-flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded ${r.swatch}`} />
                  {r.label}
                </span>
              </td>
              <td className="text-right tabular-nums">{r.route.path.length - 1}</td>
              <td className="text-right tabular-nums">{r.route.total_time.toFixed(1)}</td>
              <td className="text-right tabular-nums">{r.route.total_risk.toFixed(2)}</td>
              <td className="text-right tabular-nums">{r.route.total_co2.toFixed(1)}</td>
            </tr>
          ))}
          <tr>
            <td colSpan={2} className="py-1.5 text-right text-slate-500 text-[11px]">
              delta
            </td>
            <td className="text-right tabular-nums text-accent">
              {tDelta >= 0 ? "−" : "+"}
              {Math.abs(tDelta).toFixed(1)}
            </td>
            <td className="text-right tabular-nums text-emerald-400">
              {rDelta >= 0 ? "−" : "+"}
              {Math.abs(rDelta).toFixed(2)}
            </td>
            <td />
          </tr>
        </tbody>
      </table>
      <details className="mt-2 text-xs text-slate-400">
        <summary className="cursor-pointer hover:text-slate-300">paths</summary>
        <div className="mt-1.5 space-y-0.5 font-mono text-[11px]">
          <div>
            <span className="text-slate-300">naive:</span> {ship.naive.path.join(" → ")}
          </div>
          <div>
            <span className="text-accent">risk-aware:</span> {ship.risk_aware.path.join(" → ")}
          </div>
        </div>
      </details>
    </div>
  );
}
