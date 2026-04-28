interface Props { kpi: Record<string, number> }

export default function KPIBar({ kpi }: Props) {
  const cards = [
    { label: "Time saved", value: `${(kpi.time_saved ?? 0).toFixed(0)} min`, accent: "text-accent" },
    { label: "Risk avoided", value: (kpi.risk_avoided ?? 0).toFixed(2), accent: "text-normal" },
    { label: "CO₂ delta", value: `${((kpi.co2_saved ?? 0)).toFixed(1)} kg`, accent: "text-slate-200" },
    { label: "Shipments", value: `${(kpi.shipments ?? 0).toFixed(0)}`, accent: "text-slate-200" }
  ];
  return (
    <div className="flex gap-3">
      {cards.map((c) => (
        <div key={c.label} className="metric-card min-w-[110px]">
          <span className="text-xs text-slate-400">{c.label}</span>
          <span className={`text-lg font-semibold ${c.accent}`}>{c.value}</span>
        </div>
      ))}
    </div>
  );
}
