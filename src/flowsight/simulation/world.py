"""End-to-end simulator.

Drives the full pipeline forward in time:
    1. Compute Hawkes intensity over the time horizon
    2. Fit/predict HMM state labels per timestep
    3. Re-weight graph at the final-frame state
    4. Route every shipment under both naive and risk-aware modes
    5. Track resilience metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from ..config import DEFAULT, FlowSightConfig
from ..detection.hawkes import HawkesDetector
from ..events.injector import DisruptionInjector
from ..events.stream import EventStream
from ..routing.dijkstra import RiskAwareRouter, RouteResult
from ..state.hmm import StateEstimator


@dataclass
class ShipmentResult:
    shipment_id: int
    source: int
    target: int
    naive: RouteResult
    risk_aware: RouteResult

    @property
    def time_saved(self) -> float:
        return self.naive.total_time - self.risk_aware.total_time

    @property
    def co2_saved(self) -> float:
        return self.naive.total_co2 - self.risk_aware.total_co2

    @property
    def risk_avoided(self) -> float:
        return self.naive.total_risk - self.risk_aware.total_risk


@dataclass
class SimulationFrame:
    t: float
    risk: Dict[int, float]
    state: Dict[int, str]


@dataclass
class SimulationOutput:
    frames: List[SimulationFrame]
    shipments: List[ShipmentResult]
    events: EventStream


class World:
    def __init__(
        self,
        graph: nx.DiGraph,
        cfg: FlowSightConfig = DEFAULT,
        detector=None,
    ) -> None:
        """Build a World.

        Args:
            graph:    transit graph
            cfg:      configuration (Hawkes/HMM/routing/sim params)
            detector: any object with a `risk_trajectory(events, timesteps)`
                      method. Defaults to classical `HawkesDetector` —
                      pass `NeuralHawkesDetector` or `DCRNNForecaster`
                      to use the research-backed alternatives.
        """
        self.graph = graph
        self.cfg = cfg
        self.detector = detector or HawkesDetector(
            graph=graph,
            base_rate=cfg.hawkes.base_rate,
            alpha=cfg.hawkes.alpha,
            beta=cfg.hawkes.beta,
            spatial_decay=cfg.hawkes.spatial_decay,
        )
        self.estimator = StateEstimator(
            n_states=cfg.hmm.n_states,
            n_iter=cfg.hmm.n_iter,
            random_state=cfg.sim.seed,
        )
        self.router = RiskAwareRouter(
            graph=graph,
            risk_weight=cfg.routing.risk_weight,
            cvar_alpha=cfg.routing.cvar_alpha,
            cvar_weight=cfg.routing.cvar_weight,
            co2_weight=cfg.routing.co2_weight,
        )

    def run(
        self,
        events: Optional[EventStream] = None,
        shipments: Optional[List[Tuple[int, int]]] = None,
    ) -> SimulationOutput:
        if events is None:
            injector = DisruptionInjector(self.graph, seed=self.cfg.sim.seed)
            events = injector.from_schedule(self.cfg.sim.disruption_schedule)
        if shipments is None:
            shipments = self._default_shipments()

        timesteps = np.arange(
            0.0,
            self.cfg.sim.horizon_minutes,
            self.cfg.sim.timestep_minutes,
        )
        traj = self.detector.risk_trajectory(events, timesteps)
        self.estimator.fit(traj)

        nodes = list(self.graph.nodes())
        frames: List[SimulationFrame] = []
        for ti, t in enumerate(timesteps):
            risk_vec = traj[ti]
            risk = {n: float(risk_vec[i]) for i, n in enumerate(nodes)}
            states = self.estimator.predict(risk_vec)
            state = dict(zip(nodes, states))
            frames.append(SimulationFrame(t=float(t), risk=risk, state=state))

        # Routing uses per-node peak intensity over the horizon — the
        # right "should we route through this node?" signal. The visual
        # cascade still uses per-frame intensities for animation.
        peak_per_node = traj.max(axis=0)
        peak_risk = {n: float(peak_per_node[i]) for i, n in enumerate(nodes)}
        peak_states = self.estimator.predict(peak_per_node)
        peak_state_dict = dict(zip(nodes, peak_states))
        for n in nodes:
            self.graph.nodes[n]["risk"] = peak_risk[n]
            self.graph.nodes[n]["state"] = peak_state_dict[n]
        self.router.update_risk(peak_risk, peak_state_dict)

        shipment_results: List[ShipmentResult] = []
        for sid, (s, t) in enumerate(shipments):
            naive = self.router.route(s, t, mode="naive")
            risk_aware = self.router.route(s, t, mode="risk")
            shipment_results.append(ShipmentResult(
                shipment_id=sid, source=s, target=t,
                naive=naive, risk_aware=risk_aware,
            ))

        return SimulationOutput(frames=frames, shipments=shipment_results, events=events)

    def _default_shipments(self) -> List[Tuple[int, int]]:
        backbone = [n for n, d in self.graph.nodes(data=True)
                    if d.get("kind") in ("backbone", "grid", "osm")]
        if len(backbone) < 2:
            backbone = list(self.graph.nodes())
        return [(backbone[0], backbone[-1])]
