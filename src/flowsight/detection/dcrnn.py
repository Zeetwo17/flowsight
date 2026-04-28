"""Diffusion Convolutional Recurrent Neural Network (DCRNN).

Forecasts per-node risk T_out timesteps ahead given the last T_in
timesteps of risk + features. Uses diffusion convolution as the spatial
operator and a GRU as the temporal operator.

Diffusion convolution at order K:

    DC(X, theta) = sum_{k=0..K-1} theta_k * (D^-1 W)^k X

where W is the (weighted) adjacency matrix and D is its diagonal degree
matrix. The K-step random walk operator captures spatial smoothing
along the graph at multiple scales.

For supply chain risk this is genuinely better than Hawkes because:
  - It learns spatial spread patterns from data instead of using a
    fixed exp(-decay * dist) kernel
  - It can fuse multiple input features (risk, weather, traffic)
  - It produces a multi-step forecast, not just point intensity

Reference:
    Li, Y., Yu, R., Shahabi, C., Liu, Y. (2018). "Diffusion Convolutional
    Recurrent Neural Network: Data-Driven Traffic Forecasting." ICLR.
"""

from __future__ import annotations

from typing import List, Optional

import networkx as nx
import numpy as np

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
            "to use DCRNNForecaster."
        )


def _build_random_walk(graph: nx.DiGraph, distance_attr: str = "distance_km") -> np.ndarray:
    """Row-normalised weighted adjacency = D^-1 W. Edge weights are 1/distance."""
    nodes = list(graph.nodes())
    n = len(nodes)
    idx = {n_: i for i, n_ in enumerate(nodes)}
    W = np.zeros((n, n), dtype=np.float32)
    for u, v, data in graph.edges(data=True):
        d = float(data.get(distance_attr, 1.0))
        W[idx[u], idx[v]] = 1.0 / max(d, 1e-3)
    deg = W.sum(axis=1, keepdims=True)
    deg[deg == 0] = 1.0
    return W / deg


if _TORCH_AVAILABLE:

    class _DiffusionConv(nn.Module):
        """sum_k theta_k * (D^-1 W)^k @ X — applied feature-wise."""

        def __init__(self, in_dim: int, out_dim: int, K: int = 3, n_supports: int = 1) -> None:
            super().__init__()
            self.K = K
            self.n_supports = n_supports
            # k=0 (identity) plus K-1 powers per support, all using a shared weight
            n_terms = 1 + n_supports * (K - 1)
            self.weight = nn.Parameter(torch.empty(n_terms * in_dim, out_dim))
            self.bias = nn.Parameter(torch.zeros(out_dim))
            nn.init.xavier_uniform_(self.weight)

        def forward(self, x: "torch.Tensor", supports: List["torch.Tensor"]) -> "torch.Tensor":
            # x: [B, N, in_dim]
            B, N, F_in = x.shape
            terms = [x]  # k=0
            for S in supports:
                Sx = x  # [B, N, in_dim]
                for _ in range(1, self.K):
                    Sx = torch.einsum("nm,bmf->bnf", S, Sx)
                    terms.append(Sx)
            stacked = torch.cat(terms, dim=-1)  # [B, N, n_terms * in_dim]
            out = stacked @ self.weight + self.bias
            return out  # [B, N, out_dim]

    class _DCGRUCell(nn.Module):
        """GRU cell where each linear layer is replaced by a diffusion conv."""

        def __init__(self, in_dim: int, hidden_dim: int, K: int = 3, n_supports: int = 1) -> None:
            super().__init__()
            self.hidden_dim = hidden_dim
            self.gate_conv = _DiffusionConv(in_dim + hidden_dim, 2 * hidden_dim, K, n_supports)
            self.cand_conv = _DiffusionConv(in_dim + hidden_dim, hidden_dim, K, n_supports)

        def forward(
            self,
            x: "torch.Tensor",
            h: "torch.Tensor",
            supports: List["torch.Tensor"],
        ) -> "torch.Tensor":
            # x, h: [B, N, *]
            xh = torch.cat([x, h], dim=-1)
            gates = torch.sigmoid(self.gate_conv(xh, supports))
            r, u = gates.chunk(2, dim=-1)
            xrh = torch.cat([x, r * h], dim=-1)
            c = torch.tanh(self.cand_conv(xrh, supports))
            return u * h + (1.0 - u) * c

    class _DCRNNModule(nn.Module):
        """Encoder-only DCRNN: last hidden state -> linear -> T_out forecasts."""

        def __init__(
            self,
            in_dim: int,
            hidden_dim: int,
            n_nodes: int,
            T_out: int,
            K: int = 3,
            n_supports: int = 1,
        ) -> None:
            super().__init__()
            self.n_nodes = n_nodes
            self.T_out = T_out
            self.hidden_dim = hidden_dim
            self.cell = _DCGRUCell(in_dim, hidden_dim, K, n_supports)
            self.proj = nn.Linear(hidden_dim, T_out)

        def forward(
            self,
            x_seq: "torch.Tensor",      # [B, T_in, N, in_dim]
            supports: List["torch.Tensor"],
        ) -> "torch.Tensor":
            B, T_in, N, _ = x_seq.shape
            h = torch.zeros(B, N, self.hidden_dim, device=x_seq.device)
            for t in range(T_in):
                h = self.cell(x_seq[:, t], h, supports)
            # Project hidden to T_out forecasts per node.
            out = self.proj(h)  # [B, N, T_out]
            return out.permute(0, 2, 1)  # [B, T_out, N]


class DCRNNForecaster:
    """Multi-step risk forecaster.

    Usage:
        forecaster = DCRNNForecaster(graph, T_in=10, T_out=5)
        forecaster.train_on_classical(traj, n_epochs=200)
        future = forecaster.forecast(traj[-10:])  # [5, N]
    """

    def __init__(
        self,
        graph: nx.DiGraph,
        T_in: int = 10,
        T_out: int = 5,
        in_dim: int = 1,
        hidden_dim: int = 32,
        K: int = 3,
        device: Optional[str] = None,
    ) -> None:
        _require_torch()
        self.graph = graph
        self.nodes = list(graph.nodes())
        self.n_nodes = len(self.nodes)
        self.T_in = T_in
        self.T_out = T_out
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.K = K
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        rw = _build_random_walk(graph)
        self.support = torch.from_numpy(rw).to(self.device)
        self.supports = [self.support]

        self.model = _DCRNNModule(
            in_dim=in_dim,
            hidden_dim=hidden_dim,
            n_nodes=self.n_nodes,
            T_out=T_out,
            K=K,
            n_supports=1,
        ).to(self.device)

    def _slice_windows(self, traj: np.ndarray):
        """Build (X, Y) windows from a [T, N] trajectory."""
        T = traj.shape[0]
        if T < self.T_in + self.T_out:
            raise ValueError(
                f"Trajectory too short ({T} < T_in+T_out={self.T_in + self.T_out})"
            )
        Xs, Ys = [], []
        for start in range(0, T - self.T_in - self.T_out + 1):
            x = traj[start : start + self.T_in]
            y = traj[start + self.T_in : start + self.T_in + self.T_out]
            Xs.append(x)
            Ys.append(y)
        X = np.stack(Xs, axis=0)[..., None]  # [B, T_in, N, 1]
        Y = np.stack(Ys, axis=0)              # [B, T_out, N]
        return X.astype(np.float32), Y.astype(np.float32)

    def train_on_classical(
        self,
        classical_traj: np.ndarray,
        n_epochs: int = 200,
        lr: float = 5e-3,
        verbose: bool = False,
    ) -> List[float]:
        """Distil from the classical Hawkes trajectory as teacher."""
        X, Y = self._slice_windows(classical_traj)
        Xt = torch.from_numpy(X).to(self.device)
        Yt = torch.from_numpy(Y).to(self.device)

        opt = torch.optim.Adam(self.model.parameters(), lr=lr)
        losses: List[float] = []
        self.model.train()
        for epoch in range(n_epochs):
            opt.zero_grad()
            pred = self.model(Xt, self.supports)
            loss = F.mse_loss(pred, Yt)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
            if verbose and (epoch + 1) % 20 == 0:
                print(f"  DCRNN epoch {epoch + 1}/{n_epochs}  loss={loss.item():.5f}")
        return losses

    def forecast(self, recent: np.ndarray) -> np.ndarray:
        """Predict T_out timesteps ahead given the last T_in timesteps.

        Args:
            recent: [T_in, N] array.

        Returns:
            [T_out, N] forecast.
        """
        if recent.shape[0] != self.T_in:
            raise ValueError(f"Expected T_in={self.T_in} timesteps, got {recent.shape[0]}")
        X = recent.astype(np.float32)[None, ..., None]  # [1, T_in, N, 1]
        Xt = torch.from_numpy(X).to(self.device)
        self.model.eval()
        with torch.no_grad():
            pred = self.model(Xt, self.supports)
        return pred[0].cpu().numpy()  # [T_out, N]

    def forecast_peak(self, recent: np.ndarray) -> np.ndarray:
        """Per-node peak across the forecast horizon — the routing-relevant signal."""
        return self.forecast(recent).max(axis=0)
