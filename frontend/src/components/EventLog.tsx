import type { EventDTO } from "../types";

interface Props {
  events: EventDTO[];
}

const KIND_COLOR: Record<string, string> = {
  congestion: "bg-amber-900/40 text-amber-200 border-amber-700/50",
  closure: "bg-red-900/40 text-red-200 border-red-700/50",
  delay: "bg-orange-900/40 text-orange-200 border-orange-700/50",
  weather: "bg-sky-900/40 text-sky-200 border-sky-700/50",
  demand_spike: "bg-purple-900/40 text-purple-200 border-purple-700/50"
};

export default function EventLog({ events }: Props) {
  return (
    <div className="bg-ink2 rounded-lg p-3 border border-slate-700 overflow-auto max-h-[260px]">
      <h3 className="text-sm font-semibold mb-2 text-slate-300">
        Disruption events{" "}
        <span className="text-[10px] uppercase tracking-widest text-slate-500 font-normal ml-1">
          {events.length}
        </span>
      </h3>
      {events.length === 0 ? (
        <p className="text-xs text-slate-500">No disruptions in this run.</p>
      ) : (
        <table className="w-full text-xs">
          <thead className="text-slate-400 sticky top-0 bg-ink2">
            <tr className="border-b border-slate-700">
              <th className="text-left py-1.5 font-medium">t (min)</th>
              <th className="text-left py-1.5 font-medium">target</th>
              <th className="text-left py-1.5 font-medium">kind</th>
              <th className="text-right py-1.5 font-medium">severity</th>
              <th className="text-left py-1.5 font-medium">source</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i} className="border-b border-slate-800/60">
                <td className="py-1.5 tabular-nums">{e.t.toFixed(1)}</td>
                <td className="font-mono text-slate-300">
                  {Array.isArray(e.target) ? e.target.join("→") : e.target}
                </td>
                <td>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded border ${
                      KIND_COLOR[e.kind] ?? "bg-slate-700/40 text-slate-200 border-slate-600"
                    }`}
                  >
                    {e.kind}
                  </span>
                </td>
                <td className="text-right tabular-nums">{e.severity.toFixed(2)}</td>
                <td className="text-slate-500">{e.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
