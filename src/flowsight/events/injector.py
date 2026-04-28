"""Controlled disruption injection for demos and RL training.

For the demo we use a fixed schedule so the cascade story is reproducible.
For RL training we use random_schedule so the agent sees varied scenarios.
"""

from __future__ import annotations

import random
from typing import Iterable, Tuple

import networkx as nx

from .stream import Event, EventStream


class DisruptionInjector:
    def __init__(self, graph: nx.DiGraph, seed: int = 42) -> None:
        self.graph = graph
        self.rng = random.Random(seed)

    def from_schedule(self, schedule: Iterable[Tuple[float, str, object]]) -> EventStream:
        stream = EventStream()
        for t, kind, target in schedule:
            event_kind = "closure" if kind == "edge" else "congestion"
            # Skip events targeting nodes/edges that don't exist in this graph.
            if kind == "edge":
                if not isinstance(target, tuple) or not self.graph.has_edge(*target):
                    continue
            else:
                if target not in self.graph.nodes:
                    continue
            stream.push(Event(timestamp=float(t), target=target, kind=event_kind, severity=1.0))
        return stream

    def random_schedule(
        self,
        n_events: int = 5,
        horizon: float = 120.0,
        prefer_backbone: bool = True,
    ) -> EventStream:
        nodes = list(self.graph.nodes(data=True))
        if prefer_backbone:
            backbone = [n for n, d in nodes if d.get("kind") == "backbone"]
            pool = backbone or [n for n, _ in nodes]
        else:
            pool = [n for n, _ in nodes]

        stream = EventStream()
        for _ in range(n_events):
            t = self.rng.uniform(5.0, max(horizon - 5.0, 6.0))
            target = self.rng.choice(pool)
            severity = self.rng.uniform(0.5, 1.5)
            stream.push(Event(
                timestamp=t,
                target=target,
                kind="congestion",
                severity=severity,
            ))
        return stream
