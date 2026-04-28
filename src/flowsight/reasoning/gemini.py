"""Gemini-powered reasoning layer.

Two surfaces:
  1. `explain_reroute()` — given a naive vs risk-aware route + system
     state, generate a human-readable justification ("we diverted via
     X because cascading congestion from event Y is predicted to hit
     segment Z in 23 min").
  2. `dispatch_chat()` — conversational Q&A over the live system state
     ("what's the risk on the Mumbai corridor today?").

Both fall back to **deterministic templated explanations** when no API
key is set, so the rest of the pipeline runs without external deps.
This is what runs in CI and offline demos.

Set `GEMINI_API_KEY` in the environment to enable live LLM responses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..routing.dijkstra import RouteResult


_GENAI_AVAILABLE = True
try:
    import google.generativeai as genai
except ImportError:
    _GENAI_AVAILABLE = False
    genai = None  # type: ignore


SYSTEM_PROMPT = """You are FlowSight, a logistics dispatcher AI. You explain
re-routing decisions to human dispatchers in plain, factual language. Each
explanation:
  - Is 1 to 3 sentences.
  - States the *cause* (what disruption triggered the reroute).
  - States the *consequence* (what would happen on the original route).
  - States the *outcome* (the alternative chosen and what it saves).
  - Cites concrete node IDs and minute counts when given.
  - Never speculates beyond the data given.
  - Never uses adjectives like "catastrophic" or "massive" — be precise.
"""


@dataclass
class ReasoningResult:
    text: str
    used_llm: bool
    model: str


class GeminiExplainer:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model
        self._model = None
        if self.api_key and _GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(model)
            except Exception:
                self._model = None

    @property
    def has_llm(self) -> bool:
        return self._model is not None

    # ---------- public API ----------

    def explain_reroute(
        self,
        naive: RouteResult,
        risk_aware: RouteResult,
        node_states: Dict[int, str],
        triggering_events: List[Tuple[float, int, str]],  # (t, node, kind)
    ) -> ReasoningResult:
        prompt = self._reroute_prompt(naive, risk_aware, node_states, triggering_events)
        if self._model is None:
            return ReasoningResult(
                text=self._template_reroute(naive, risk_aware, node_states, triggering_events),
                used_llm=False,
                model="template",
            )
        try:
            resp = self._model.generate_content(SYSTEM_PROMPT + "\n\n" + prompt)
            return ReasoningResult(text=resp.text.strip(), used_llm=True, model=self.model_name)
        except Exception as e:
            # Network/quota failure -> fall back, never crash the pipeline.
            return ReasoningResult(
                text=self._template_reroute(naive, risk_aware, node_states, triggering_events)
                + f"\n\n[LLM call failed: {e}]",
                used_llm=False,
                model="template-fallback",
            )

    def dispatch_chat(self, query: str, system_state: dict) -> ReasoningResult:
        if self._model is None:
            return ReasoningResult(
                text=self._template_chat(query, system_state),
                used_llm=False,
                model="template",
            )
        prompt = (
            f"System state: {system_state}\n\n"
            f"Dispatcher question: {query}\n\n"
            "Answer in 1-3 sentences using only the data above."
        )
        try:
            resp = self._model.generate_content(SYSTEM_PROMPT + "\n\n" + prompt)
            return ReasoningResult(text=resp.text.strip(), used_llm=True, model=self.model_name)
        except Exception as e:
            return ReasoningResult(
                text=self._template_chat(query, system_state) + f"\n\n[LLM call failed: {e}]",
                used_llm=False,
                model="template-fallback",
            )

    # ---------- prompt construction ----------

    @staticmethod
    def _reroute_prompt(
        naive: RouteResult,
        risk_aware: RouteResult,
        node_states: Dict[int, str],
        events: List[Tuple[float, int, str]],
    ) -> str:
        critical_on_naive = [
            n for n in naive.path if node_states.get(n) == "Critical"
        ]
        critical_avoided = [
            n for n in critical_on_naive if n not in set(risk_aware.path)
        ]
        ev_lines = "\n".join(
            f"  - t={t:.0f}min  node={n}  kind={k}" for t, n, k in events
        ) or "  (none reported)"
        return (
            f"Naive shortest path: {naive.path}\n"
            f"  total_time={naive.total_time:.1f} min, "
            f"risk={naive.total_risk:.2f}, CO2={naive.total_co2:.1f} kg\n"
            f"Risk-aware path:   {risk_aware.path}\n"
            f"  total_time={risk_aware.total_time:.1f} min, "
            f"risk={risk_aware.total_risk:.2f}, CO2={risk_aware.total_co2:.1f} kg\n"
            f"Critical-state nodes on naive path: {critical_on_naive}\n"
            f"Critical-state nodes avoided by reroute: {critical_avoided}\n"
            f"Triggering events:\n{ev_lines}\n"
            f"Time saved: {naive.total_time - risk_aware.total_time:.1f} min, "
            f"risk avoided: {naive.total_risk - risk_aware.total_risk:.2f}\n"
            "\nWrite a 2-3 sentence explanation."
        )

    # ---------- deterministic templates (offline fallback) ----------

    @staticmethod
    def _template_reroute(
        naive: RouteResult,
        risk_aware: RouteResult,
        node_states: Dict[int, str],
        events: List[Tuple[float, int, str]],
    ) -> str:
        critical_on_naive = [n for n in naive.path if node_states.get(n) == "Critical"]
        critical_avoided = [n for n in critical_on_naive if n not in set(risk_aware.path)]
        time_saved = naive.total_time - risk_aware.total_time
        if not critical_avoided:
            return (
                f"Holding the original route ({len(naive.path) - 1} hops). "
                f"No critical-state nodes on the naive path; "
                f"no reroute justified."
            )
        events_str = ", ".join(f"t={t:.0f}min/{k} at node {n}" for t, n, k in events[:3]) or "no events reported"
        return (
            f"Diverting via {[n for n in risk_aware.path if n not in naive.path][:3]} "
            f"to avoid critical-state nodes {critical_avoided[:3]}. "
            f"Triggers: {events_str}. "
            f"Saves {time_saved:.0f} min and reduces total path risk by "
            f"{naive.total_risk - risk_aware.total_risk:.2f}."
        )

    @staticmethod
    def _template_chat(query: str, state: dict) -> str:
        critical = state.get("critical_nodes", [])
        stressed = state.get("stressed_nodes", [])
        return (
            f"Query: {query}\n"
            f"Current state: {len(critical)} critical-state nodes ({critical[:5]}), "
            f"{len(stressed)} stressed-state nodes. "
            "Set GEMINI_API_KEY for nuanced answers."
        )
