"""Risk-aware routing.

Edge cost (per mode):

    naive: travel_time
    risk : travel_time * state_multiplier
           + risk_weight  * risk
           + co2_weight   * co2
    cvar : same as risk plus cvar_weight * CVaR_alpha(risk_samples)

CVaR (Conditional Value-at-Risk) at level alpha is the expected loss in
the worst (alpha) fraction of the distribution — picks routes that are
robust under tail risk, not just expected risk.

References:
    Rockafellar & Uryasev (2000). "Optimization of Conditional Value-at-Risk."
    Polychronopoulos & Tsitsiklis (1996). "Stochastic shortest path problems
    with recourse." Networks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np


@dataclass
class RouteResult:
    path: List[int]
    total_time: float
    total_risk: float
    total_co2: float
    total_cost: float
    mode: str

    def edges(self) -> List[Tuple[int, int]]:
        return list(zip(self.path[:-1], self.path[1:]))


class RiskAwareRouter:
    def __init__(
        self,
        graph: nx.DiGraph,
        risk_weight: float = 5.0,
        cvar_alpha: float = 0.1,
        cvar_weight: float = 2.0,
        co2_weight: float = 0.5,
    ) -> None:
        self.graph = graph
        self.risk_weight = risk_weight
        self.cvar_alpha = cvar_alpha
        self.cvar_weight = cvar_weight
        self.co2_weight = co2_weight

    def update_risk(
        self,
        node_risk: Dict[int, float],
        node_state: Optional[Dict[int, str]] = None,
        risk_samples: Optional[Dict[Tuple[int, int], np.ndarray]] = None,
    ) -> None:
        """Project per-node risk and state labels onto edge attributes."""
        from ..state.hmm import StateEstimator
        for u, v, data in self.graph.edges(data=True):
            r_u = node_risk.get(u, 0.0)
            r_v = node_risk.get(v, 0.0)
            edge_risk = 0.5 * (r_u + r_v)
            mult = 1.0
            if node_state is not None:
                s_u = node_state.get(u, "Normal")
                s_v = node_state.get(v, "Normal")
                mult = max(
                    StateEstimator.state_to_multiplier(s_u),
                    StateEstimator.state_to_multiplier(s_v),
                )
            data["risk"] = edge_risk
            data["state_multiplier"] = mult
            data["travel_time"] = data["base_travel_time"] * mult
            if risk_samples is not None and (u, v) in risk_samples:
                data["cvar_risk"] = self._cvar(risk_samples[(u, v)], self.cvar_alpha)
            else:
                data["cvar_risk"] = edge_risk

    @staticmethod
    def _cvar(samples: np.ndarray, alpha: float) -> float:
        if samples.size == 0:
            return 0.0
        threshold = float(np.quantile(samples, 1.0 - alpha))
        tail = samples[samples >= threshold]
        return float(tail.mean()) if tail.size else threshold

    def _cost(self, mode: str):
        rw, cw, c2w = self.risk_weight, self.cvar_weight, self.co2_weight

        def cost_fn(u: int, v: int, data: dict) -> float:
            base = data.get("base_travel_time", 1.0)
            if mode == "naive":
                # Naive baseline ignores disruption signals entirely:
                # uses the un-inflated nominal travel time.
                return base
            t = data.get("travel_time", base)
            r = data.get("risk", 0.0)
            cvar = data.get("cvar_risk", r)
            co2 = data.get("co2_per_trip", 0.0)
            term_risk = rw * r
            term_cvar = cw * cvar if mode == "cvar" else 0.0
            term_co2 = c2w * co2
            return t + term_risk + term_cvar + term_co2

        return cost_fn

    def route(self, source: int, target: int, mode: str = "risk") -> RouteResult:
        path = nx.shortest_path(self.graph, source, target, weight=self._cost(mode))
        return self._summarize(path, mode)

    def _summarize(self, path: List[int], mode: str) -> RouteResult:
        total_time = total_risk = total_co2 = total_cost = 0.0
        cost_fn = self._cost(mode)
        for u, v in zip(path[:-1], path[1:]):
            data = self.graph.edges[u, v]
            total_time += data.get("travel_time", data.get("base_travel_time", 1.0))
            total_risk += data.get("risk", 0.0)
            total_co2 += data.get("co2_per_trip", 0.0)
            total_cost += cost_fn(u, v, data)
        return RouteResult(
            path=path,
            total_time=total_time,
            total_risk=total_risk,
            total_co2=total_co2,
            total_cost=total_cost,
            mode=mode,
        )
