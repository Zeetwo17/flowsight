import type { ExplanationDTO } from "../types";

interface Props { explanation: ExplanationDTO | null }

export default function ExplanationPanel({ explanation }: Props) {
  return (
    <div className="bg-ink2 rounded-lg p-3 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-300">Why we rerouted</h3>
        {explanation && (
          <span className="text-xs text-slate-400">
            {explanation.used_llm ? `via ${explanation.model}` : "template (no API key)"}
          </span>
        )}
      </div>
      {explanation ? (
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {explanation.explanation}
        </p>
      ) : (
        <p className="text-sm text-slate-400">
          Click <em>Explain reroute</em> to generate a justification for the latest decision.
          Uses Gemini if <code>GEMINI_API_KEY</code> is configured; falls back to a deterministic
          template otherwise.
        </p>
      )}
    </div>
  );
}
