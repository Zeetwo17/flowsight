import type { ExplanationDTO } from "../types";

interface Props {
  explanation: ExplanationDTO | null;
  loading?: boolean;
}

export default function ExplanationPanel({ explanation, loading }: Props) {
  return (
    <div className="bg-ink2 rounded-lg p-3 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-300">Why we rerouted</h3>
        {explanation && (
          <span
            className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded ${
              explanation.used_llm
                ? "bg-emerald-900/40 text-emerald-300 border border-emerald-700/50"
                : "bg-slate-700/40 text-slate-300 border border-slate-600"
            }`}
          >
            {explanation.used_llm ? `via ${explanation.model}` : "template fallback"}
          </span>
        )}
      </div>
      {loading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-slate-700/50 rounded w-full" />
          <div className="h-3 bg-slate-700/50 rounded w-11/12" />
          <div className="h-3 bg-slate-700/50 rounded w-9/12" />
        </div>
      ) : explanation ? (
        <p className="text-sm leading-relaxed whitespace-pre-wrap text-slate-200">
          {explanation.explanation}
        </p>
      ) : (
        <p className="text-sm text-slate-400 leading-relaxed">
          Click <em className="text-slate-300">Explain reroute</em> in the sidebar to generate a
          plain-language justification for the latest decision. With{" "}
          <code className="bg-ink px-1 rounded text-xs">GEMINI_API_KEY</code> configured on the
          backend you'll get live Gemini output; otherwise, a deterministic template runs as a
          fallback.
        </p>
      )}
    </div>
  );
}
