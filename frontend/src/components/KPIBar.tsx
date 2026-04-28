interface Props {
  kpi: Record<string, number>;
  placeholder?: boolean;
}

interface Card {
  label: string;
  value: string;
  sub?: string;
  accent: string;
}

export default function KPIBar({ kpi, placeholder = false }: Props) {
  const cards: Card[] = placeholder
    ? [
        { label: "Time saved", value: "—", accent: "text-slate-500" },
        { label: "Risk avoided", value: "—", accent: "text-slate-500" },
        { label: "CO₂ delta", value: "—", accent: "text-slate-500" },
        { label: "Shipments", value: "—", accent: "text-slate-500" }
      ]
    : [
        {
          label: "Time saved",
          value: `${(kpi.time_saved ?? 0).toFixed(0)}`,
          sub: "min vs naive",
          accent: "text-accent"
        },
        {
          label: "Risk avoided",
          value: `${(kpi.risk_avoided ?? 0).toFixed(2)}`,
          sub: "lower is safer",
          accent: "text-emerald-400"
        },
        {
          label: "CO₂ delta",
          value: `${(kpi.co2_saved ?? 0).toFixed(1)}`,
          sub: "kg per shipment",
          accent: (kpi.co2_saved ?? 0) >= 0 ? "text-emerald-400" : "text-amber-400"
        },
        {
          label: "Shipments",
          value: `${(kpi.shipments ?? 0).toFixed(0)}`,
          sub: "in this run",
          accent: "text-slate-200"
        }
      ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="bg-ink2 rounded-lg p-3 border border-slate-700 flex flex-col gap-0.5"
        >
          <span className="text-[10px] uppercase tracking-widest text-slate-400">
            {c.label}
          </span>
          <span className={`text-2xl sm:text-3xl font-semibold leading-tight ${c.accent}`}>
            {c.value}
          </span>
          {c.sub && (
            <span className="text-[11px] text-slate-500">{c.sub}</span>
          )}
        </div>
      ))}
    </div>
  );
}
