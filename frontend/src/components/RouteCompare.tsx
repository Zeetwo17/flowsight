import type { SimulationDTO } from "../types";

interface Props { sim: SimulationDTO }

export default function RouteCompare({ sim }: Props) {
  const ship = sim.shipments[0];
  if (!ship) return <div className="text-slate-400 text-sm">No shipments.</div>;
  const rows = [
    { label: "naive", route: ship.naive, color: "text-slate-300" },
    { label: "risk-aware", route: ship.risk_aware, color: "text-accent" }
  ];
  return (
    <div>
      <h3 className="text-sm font-semibold mb-2 text-slate-300">Route comparison</h3>
      <table className="w-full text-xs">
        <thead className="text-slate-400">
          <tr>
            <th className="text-left">mode</th>
            <th className="text-right">hops</th>
            <th className="text-right">time (min)</th>
            <th className="text-right">risk</th>
            <th className="text-right">CO₂</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-t border-slate-700">
              <td className={`py-1 font-semibold ${r.color}`}>{r.label}</td>
              <td className="text-right">{r.route.path.length - 1}</td>
              <td className="text-right">{r.route.total_time.toFixed(1)}</td>
              <td className="text-right">{r.route.total_risk.toFixed(2)}</td>
              <td className="text-right">{r.route.total_co2.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <details className="mt-2 text-xs text-slate-400">
        <summary>paths</summary>
        <div className="mt-1">
          <div><span className="text-slate-300">naive:</span> {ship.naive.path.join(" → ")}</div>
          <div><span className="text-accent">risk-aware:</span> {ship.risk_aware.path.join(" → ")}</div>
        </div>
      </details>
    </div>
  );
}
