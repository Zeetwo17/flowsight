import { useMemo } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";
import type { SimulationDTO } from "../types";

interface Props { sim: SimulationDTO }

export default function CascadeChart({ sim }: Props) {
  const data = useMemo(() => {
    // Plot risk for the disrupted nodes (top-3 peak) to keep the chart legible.
    const N = sim.graph.nodes.length;
    const peak = new Array<number>(N).fill(0);
    sim.frames.forEach((f) => f.risk.forEach((r, i) => { peak[i] = Math.max(peak[i], r); }));
    const ranked = peak
      .map((p, i) => ({ i, p }))
      .sort((a, b) => b.p - a.p)
      .slice(0, 3)
      .map((x) => x.i);

    return sim.frames.map((f) => {
      const row: Record<string, number> = { t: f.t };
      ranked.forEach((idx) => {
        const id = sim.graph.nodes[idx].id;
        row[`node ${id}`] = f.risk[idx];
      });
      return row;
    });
  }, [sim]);

  const seriesKeys = data.length ? Object.keys(data[0]).filter((k) => k !== "t") : [];

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-sm font-semibold mb-1 text-slate-300">
        Cascade · top-3 peak risk nodes
      </h3>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#334155" />
            <XAxis dataKey="t" stroke="#94a3b8" fontSize={11} />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip
              contentStyle={{ background: "#1e293b", border: "1px solid #334155" }}
              labelFormatter={(t) => `t = ${Number(t).toFixed(1)} min`}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {seriesKeys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={["#dc3c3c", "#f0b43c", "#3282fa"][i % 3]} dot={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
