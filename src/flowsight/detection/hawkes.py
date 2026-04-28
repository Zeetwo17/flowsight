"""Spatial Hawkes process for cascade detection.

Per-node intensity:

    lambda_i(t) = mu_i + sum_j sum_{t_j < t} alpha_ij * exp(-beta * (t - t_j))

where alpha_ij = exp(-spatial_decay * dist(i, j)) so events propagate
along the network rather than instantaneously globally.

This is the classical baseline. The Neural Hawkes Process
(Mei & Eisner, NeurIPS 2017) replaces the parametric kernel with an
LSTM that conditions intensity on the full event history — that
upgrade is planned in `neural_hawkes.py`.

References:
    Hawkes, A.G. (1971). Biometrika, 58(1).
    Reinhart, A. (2018). Statistical Science, 33(3).
    Mei & Eisner (2017). NeurIPS.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable

import networkx as nx
import numpy as np

from ..events.stream import Event


class HawkesDetector:
    def __init__(
        self,
        graph: nx.DiGraph,
        base_rate: float = 0.05,
        alpha: float = 0.6,
        beta: float = 0.4,
        spatial_decay: float = 0.15,
    ) -> None:
        self.graph = graph
        self.base_rate = base_rate
        self.alpha = alpha
        self.beta = beta
        self.spatial_decay = spatial_decay

        self._undirected = graph.to_undirected()
        self._spatial = self._precompute_spatial_kernel()

    def _precompute_spatial_kernel(self) -> Dict[int, Dict[int, float]]:
        kernel: Dict[int, Dict[int, float]] = {}
        for src in self._undirected.nodes():
            try:
                lengths = nx.single_source_dijkstra_path_length(
                    self._undirected, src, weight="distance_km"
                )
            except nx.NetworkXNoPath:
                lengths = {src: 0.0}
            kernel[src] = {
                tgt: math.exp(-self.spatial_decay * d)
                for tgt, d in lengths.items()
            }
        return kernel

    def intensity(self, node: int, t: float, events: Iterable[Event]) -> float:
        lam = self.base_rate
        for ev in events:
            if ev.timestamp >= t:
                break  # events list is time-sorted
            spatial = self._spatial.get(ev.origin_node, {}).get(node, 0.0)
            if spatial < 1e-6:
                continue
            decay = math.exp(-self.beta * (t - ev.timestamp))
            lam += self.alpha * ev.severity * spatial * decay
        return lam

    def risk_vector(self, t: float, events: Iterable[Event]) -> Dict[int, float]:
        events = sorted(events, key=lambda e: e.timestamp)
        return {n: self.intensity(n, t, events) for n in self.graph.nodes()}

    def risk_trajectory(
        self,
        events: Iterable[Event],
        timesteps: Iterable[float],
    ) -> np.ndarray:
        """Return a [T, N] matrix of intensity per node per timestep."""
        nodes = list(self.graph.nodes())
        events = sorted(events, key=lambda e: e.timestamp)
        timesteps = list(timesteps)
        T, N = len(timesteps), len(nodes)
        out = np.zeros((T, N), dtype=np.float64)
        for ti, t in enumerate(timesteps):
            for ni, n in enumerate(nodes):
                out[ti, ni] = self.intensity(n, t, events)
        return out
