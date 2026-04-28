"""Neural Hawkes Process (Mei & Eisner, NeurIPS 2017).

Replaces the parametric kernel of classical Hawkes with a
continuous-time LSTM whose cell state c(t) evolves through events and
decays exponentially between them:

    on event:   c <- f * c + i * tanh(z),  c_bar <- f_bar * c_bar + i_bar * tanh(z)
    between:    c(t) = c_bar + (c - c_bar) * exp(-decay * dt)
    output:     h(t) = o * tanh(c(t))
    intensity:  lambda_i(t) = softplus(W_i h(t))   per node i

Used as a drop-in upgrade for `HawkesDetector` — exposes the same
`risk_trajectory(events, timesteps)` interface so `simulation/world.py`
doesn't need to change. Train against the classical Hawkes trajectory
as a teacher (knowledge distillation) when ground-truth cascade labels
aren't available.

Reference:
    Mei, H. & Eisner, J. (2017). "The Neural Hawkes Process: A Neurally
    Self-Modulating Multivariate Point Process." NeurIPS.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

import networkx as nx
import numpy as np

from ..events.stream import Event


_TORCH_AVAILABLE = True
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    _TORCH_AVAILABLE = False
    torch = None  # type: ignore
    nn = None  # type: ignore
    F = None  # type: ignore


def _require_torch() -> None:
    if not _TORCH_AVAILABLE:
        raise ImportError(
            "PyTorch is not installed. Install with `pip install torch` "
            "to use NeuralHawkesDetector."
        )


_KIND_TO_INDEX = {"congestion": 0, "delay": 1, "closure": 2, "weather": 3, "demand_spike": 4}
N_KINDS = len(_KIND_TO_INDEX)


if _TORCH_AVAILABLE:

    class _CTLSTMCell(nn.Module):
        """One continuous-time LSTM cell.

        On event: standard LSTM gates update c and the long-run target c_bar.
        Between events: c(t) decays exponentially toward c_bar.
        """

        def __init__(self, in_dim: int, hidden_dim: int) -> None:
            super().__init__()
            self.hidden_dim = hidden_dim
            # 7 gate outputs: i, f, z, o, i_bar, f_bar, decay
            self.gate = nn.Linear(in_dim + hidden_dim, 7 * hidden_dim)
            nn.init.xavier_uniform_(self.gate.weight)

        def event_step(
            self,
            x: "torch.Tensor",
            h_at_event: "torch.Tensor",
            c_bar_prev: "torch.Tensor",
        ):
            gates = self.gate(torch.cat([x, h_at_event], dim=-1))
            i, f, z, o, i_bar, f_bar, decay = gates.chunk(7, dim=-1)
            i, f, o = torch.sigmoid(i), torch.sigmoid(f), torch.sigmoid(o)
            i_bar, f_bar = torch.sigmoid(i_bar), torch.sigmoid(f_bar)
            z = torch.tanh(z)
            decay = F.softplus(decay) + 1e-3  # strictly positive

            # Use h_at_event as a proxy for c at event time so we don't
            # need to thread c separately through decay.
            c_new = f * h_at_event + i * z
            c_bar_new = f_bar * c_bar_prev + i_bar * z
            return c_new, c_bar_new, decay, o

        @staticmethod
        def decay_to(
            c: "torch.Tensor",
            c_bar: "torch.Tensor",
            decay: "torch.Tensor",
            o: "torch.Tensor",
            dt: "torch.Tensor",
        ) -> "torch.Tensor":
            c_t = c_bar + (c - c_bar) * torch.exp(-decay * dt)
            return o * torch.tanh(c_t)

    class _NHPModule(nn.Module):
        def __init__(self, in_dim: int, hidden_dim: int, n_nodes: int) -> None:
            super().__init__()
            self.cell = _CTLSTMCell(in_dim, hidden_dim)
            self.head = nn.Linear(hidden_dim, n_nodes)
            self.hidden_dim = hidden_dim

        def forward(
            self,
            event_embs: "torch.Tensor",  # [E, in_dim]
            event_times: "torch.Tensor",  # [E]
            query_times: "torch.Tensor",  # [T]
        ) -> "torch.Tensor":
            device = event_embs.device
            h = torch.zeros(self.hidden_dim, device=device)
            c = torch.zeros(self.hidden_dim, device=device)
            c_bar = torch.zeros(self.hidden_dim, device=device)
            decay = torch.ones(self.hidden_dim, device=device) * 0.1
            o = torch.zeros(self.hidden_dim, device=device)

            E = int(event_embs.shape[0])
            ev_idx = 0
            prev_t = torch.tensor(0.0, device=device)

            outs: List["torch.Tensor"] = []
            for qi in range(int(query_times.shape[0])):
                t = query_times[qi]
                while ev_idx < E and event_times[ev_idx] <= t:
                    ev_t = event_times[ev_idx]
                    dt = (ev_t - prev_t).clamp(min=0.0)
                    h_at_event = self.cell.decay_to(c, c_bar, decay, o, dt)
                    c, c_bar, decay, o = self.cell.event_step(
                        event_embs[ev_idx], h_at_event, c_bar
                    )
                    prev_t = ev_t
                    ev_idx += 1
                dt_q = (t - prev_t).clamp(min=0.0)
                h_t = self.cell.decay_to(c, c_bar, decay, o, dt_q)
                outs.append(F.softplus(self.head(h_t)))
            return torch.stack(outs, dim=0)


class NeuralHawkesDetector:
    """API-compatible with `HawkesDetector` — drop-in upgrade.

    Behaviour:
      - On construction, weights are randomly initialised.
      - Call `train_on_classical()` to distil from the classical Hawkes
        trajectory — gives a learned intensity surface without needing
        labelled cascade ground truth.
      - `risk_trajectory()` runs inference and returns a [T, N] matrix.
    """

    def __init__(
        self,
        graph: nx.DiGraph,
        hidden_dim: int = 32,
        device: str | None = None,
    ) -> None:
        _require_torch()
        self.graph = graph
        self.nodes = list(graph.nodes())
        self.node_index = {n: i for i, n in enumerate(self.nodes)}
        self.n_nodes = len(self.nodes)
        self.hidden_dim = hidden_dim
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self._spatial = self._precompute_spatial_features()
        in_dim = N_KINDS + self.n_nodes  # one-hot kind + spatial signature
        self.model = _NHPModule(in_dim, hidden_dim, self.n_nodes).to(self.device)

    def _precompute_spatial_features(self) -> np.ndarray:
        ud = self.graph.to_undirected()
        feat = np.zeros((self.n_nodes, self.n_nodes), dtype=np.float32)
        for src in self.nodes:
            try:
                lengths = nx.single_source_dijkstra_path_length(ud, src, weight="distance_km")
            except nx.NetworkXNoPath:
                lengths = {src: 0.0}
            for tgt, d in lengths.items():
                feat[self.node_index[src], self.node_index[tgt]] = float(np.exp(-0.02 * d))
        return feat

    def _embed_events(self, events: List[Event]):
        if not events:
            return (torch.zeros((0, N_KINDS + self.n_nodes), device=self.device),
                    torch.zeros((0,), device=self.device))
        kinds = np.zeros((len(events), N_KINDS), dtype=np.float32)
        spatial = np.zeros((len(events), self.n_nodes), dtype=np.float32)
        times = np.zeros((len(events),), dtype=np.float32)
        for i, ev in enumerate(events):
            kinds[i, _KIND_TO_INDEX.get(ev.kind, 0)] = float(ev.severity)
            origin = self.node_index.get(ev.origin_node, 0)
            spatial[i] = self._spatial[origin] * float(ev.severity)
            times[i] = float(ev.timestamp)
        embs = np.concatenate([kinds, spatial], axis=1)
        return (torch.from_numpy(embs).to(self.device),
                torch.from_numpy(times).to(self.device))

    def risk_trajectory(
        self,
        events: Iterable[Event],
        timesteps: Iterable[float],
    ) -> np.ndarray:
        """End-to-end intensity from the trained NHP — no post-processing.

        After distillation, the network output IS the intensity per node;
        any extra spatial multiplication would double-count the spatial
        signal that's already encoded in the event embedding.
        """
        events = sorted(events, key=lambda e: e.timestamp)
        ts = np.asarray(list(timesteps), dtype=np.float32)
        embs, ev_times = self._embed_events(events)
        qts = torch.from_numpy(ts).to(self.device)
        self.model.eval()
        with torch.no_grad():
            traj = self.model(embs, ev_times, qts)
        return traj.cpu().numpy()

    def train_on_classical(
        self,
        classical_traj: np.ndarray,
        events: Iterable[Event],
        timesteps: Iterable[float],
        n_epochs: int = 200,
        lr: float = 1e-2,
        peak_weight: float = 5.0,
        verbose: bool = False,
    ) -> List[float]:
        """Distil from classical Hawkes — MSE + peak-weighted loss.

        The peak-weighted term up-weights samples in the top quartile of
        the teacher's intensity. Without it, MSE on a sparse cascade
        signal (mostly zeros, a few peaks) drives the model toward a
        smooth low-intensity surface that loses the routing-relevant
        contrast at peaks.
        """
        target = torch.from_numpy(classical_traj.astype(np.float32)).to(self.device)
        peak_thr = torch.quantile(target, 0.75)
        peak_mask = (target > peak_thr).float()

        events = sorted(events, key=lambda e: e.timestamp)
        embs, ev_times = self._embed_events(events)
        qts = torch.from_numpy(np.asarray(list(timesteps), dtype=np.float32)).to(self.device)

        opt = torch.optim.Adam(self.model.parameters(), lr=lr)
        losses: List[float] = []
        self.model.train()
        for epoch in range(n_epochs):
            opt.zero_grad()
            pred = self.model(embs, ev_times, qts)
            base_loss = F.mse_loss(pred, target)
            peak_loss = F.mse_loss(pred * peak_mask, target * peak_mask)
            loss = base_loss + peak_weight * peak_loss
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
            if verbose and (epoch + 1) % 20 == 0:
                print(f"  epoch {epoch + 1}/{n_epochs}  loss={loss.item():.5f}")
        return losses
