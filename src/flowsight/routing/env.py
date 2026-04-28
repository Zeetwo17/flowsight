"""Gymnasium environment wrapping the supply-chain routing problem.

Observation:
    [risk_per_node, state_per_node, current_idx, target_idx, step_frac, elapsed]

Action:
    discrete index into the current node's outgoing neighbours
    (clipped if the node has fewer neighbours than max_degree).

Reward:
    -(travel_time + risk_weight * risk + co2_weight * co2)
    + reach_bonus on terminate
    - failure_penalty on dead-end / step-out

Designed for stable-baselines3 PPO. Use vectorized envs for parallel
rollouts.
"""

from __future__ import annotations

from typing import Optional

import networkx as nx
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    _HAVE_GYM = True
except ImportError:
    _HAVE_GYM = False
    gym = None  # type: ignore
    spaces = None  # type: ignore


_BASE = gym.Env if _HAVE_GYM else object


class SupplyChainEnv(_BASE):  # type: ignore[misc, valid-type]
    metadata = {"render_modes": []}

    def __init__(
        self,
        graph: nx.DiGraph,
        source: int,
        target: int,
        max_steps: int = 50,
        risk_weight: float = 5.0,
        co2_weight: float = 0.5,
        reach_bonus: float = 50.0,
        failure_penalty: float = 100.0,
    ) -> None:
        if not _HAVE_GYM:
            raise ImportError("Install gymnasium to use SupplyChainEnv.")
        super().__init__()
        self.graph = graph
        self.source = source
        self.target = target
        self.max_steps = max_steps
        self.risk_weight = risk_weight
        self.co2_weight = co2_weight
        self.reach_bonus = reach_bonus
        self.failure_penalty = failure_penalty

        self.nodes = list(graph.nodes())
        self.node_index = {n: i for i, n in enumerate(self.nodes)}
        self.max_degree = max((graph.out_degree(n) for n in self.nodes), default=1) or 1

        self.action_space = spaces.Discrete(self.max_degree)
        obs_dim = 2 * len(self.nodes) + 4
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        self.current: Optional[int] = None
        self.steps = 0
        self.elapsed_time = 0.0

    def reset(self, *, seed: Optional[int] = None, options=None):
        super().reset(seed=seed)
        self.current = self.source
        self.steps = 0
        self.elapsed_time = 0.0
        return self._obs(), {}

    def step(self, action: int):
        neighbors = list(self.graph.successors(self.current))
        if not neighbors:
            return self._obs(), -self.failure_penalty, True, False, {"reason": "dead_end"}

        action = int(min(action, len(neighbors) - 1))
        nxt = neighbors[action]
        data = self.graph.edges[self.current, nxt]

        time_step = float(data.get("travel_time", 1.0))
        risk = float(data.get("risk", 0.0))
        co2 = float(data.get("co2_per_trip", 0.0))
        reward = -(time_step + self.risk_weight * risk + self.co2_weight * co2)

        self.current = nxt
        self.steps += 1
        self.elapsed_time += time_step

        terminated = self.current == self.target
        truncated = self.steps >= self.max_steps
        if terminated:
            reward += self.reach_bonus
        return self._obs(), float(reward), terminated, truncated, {}

    def _obs(self) -> np.ndarray:
        risks = np.array(
            [self.graph.nodes[n].get("risk", 0.0) for n in self.nodes],
            dtype=np.float32,
        )
        state_score = {"Normal": 0.0, "Stressed": 0.5, "Critical": 1.0}
        states = np.array(
            [state_score.get(self.graph.nodes[n].get("state", "Normal"), 0.0)
             for n in self.nodes],
            dtype=np.float32,
        )
        ctx = np.array([
            self.node_index[self.current] / max(len(self.nodes) - 1, 1),
            self.node_index[self.target] / max(len(self.nodes) - 1, 1),
            self.steps / self.max_steps,
            self.elapsed_time / 60.0,
        ], dtype=np.float32)
        return np.concatenate([risks, states, ctx])
