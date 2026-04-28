import type { EventDTO } from "../types";

interface Props { events: EventDTO[] }

export default function EventLog({ events }: Props) {
  return (
    <div className="bg-ink2 rounded-lg p-3 border border-slate-700 overflow-auto">
      <h3 className="text-sm font-semibold mb-2 text-slate-300">Disruption events</h3>
      <table className="w-full text-xs">
        <thead className="text-slate-400">
          <tr>
            <th className="text-left">t (min)</th>
            <th className="text-left">target</th>
            <th className="text-left">kind</th>
            <th className="text-right">severity</th>
            <th className="text-left">source</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e, i) => (
            <tr key={i} className="border-t border-slate-700">
              <td className="py-1">{e.t.toFixed(1)}</td>
              <td>{Array.isArray(e.target) ? e.target.join("→") : e.target}</td>
              <td>{e.kind}</td>
              <td className="text-right">{e.severity.toFixed(2)}</td>
              <td className="text-slate-400">{e.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
