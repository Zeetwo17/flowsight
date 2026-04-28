import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { SimulationDTO } from "../types";

interface Props {
  sim: SimulationDTO;
  cursorT?: number;
}

export default function CascadeChart({ sim, cursorT }: Props) {
  const { data, seriesKeys } = useMemo(() => {
    const N = sim.graph.nodes.length;
    const peak = new Array<number>(N).fill(0);
    sim.frames.forEach((f) =>
      f.risk.forEach((r, i) => {
        peak[i] = Math.max(peak[i], r);
      })
    );
    const ranked = peak
      .map((p, i) => ({ i, p }))
      .sort((a, b) => b.p - a.p)
      .slice(0, 4)
      .map((x) => x.i);

    const data = sim.frames.map((f) => {
      const row: Record<string, number> = { t: f.t };
      ranked.forEach((idx) => {
        const id = sim.graph.nodes[idx].id;
        row[`node ${id}`] = f.risk[idx];
      });
      return row;
    });
    const seriesKeys = data.length ? Object.keys(data[0]).filter((k) => k !== "t") : [];
    return { data, seriesKeys };
  }, [sim]);

  const colors = ["#dc3c3c", "#f0b43c", "#f97316", "#3282fa"];

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-semibold text-slate-300">
          Cascade — Hawkes intensity
        </h3>
        <span className="text-[10px] uppercase tracking-widest text-slate-500">
          top-4 nodes
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="#94a3b8" fontSize={10} />
            <YAxis stroke="#94a3b8" fontSize={10} />
            <Tooltip
              contentStyle={{
                background: "#1e293b",
                border: "1px solid #334155",
                fontSize: 12
              }}
              labelFormatter={(t) => `t = ${Number(t).toFixed(1)} min`}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {cursorT !== undefined && (
              <ReferenceLine x={cursorT} stroke="#3282fa" strokeDasharray="3 3" />
            )}
            {seriesKeys.map((k, i) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                stroke={colors[i % colors.length]}
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
