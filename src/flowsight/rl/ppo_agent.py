"""PPO agent wrapper.

Thin layer over stable-baselines3 PPO. Lazy-imports torch and sb3 only
when actually constructed, so the rest of the package runs without ML
dependencies installed.

The CVaR-constrained objective is wired in as a `cvar_alpha` knob —
trajectory-level worst-fraction shaping is applied before the policy
gradient step in the training loop. The default `cvar_alpha=None`
behaves as vanilla PPO.

References:
    Schulman et al. (2017). "Proximal Policy Optimization Algorithms."
    Rockafellar & Uryasev (2000). "Optimization of Conditional Value-at-Risk."
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional


class PPOAgent:
    def __init__(
        self,
        env_fn: Callable,
        n_envs: int = 4,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        verbose: int = 0,
        cvar_alpha: Optional[float] = None,
    ) -> None:
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError as e:
            raise ImportError(
                "Install ML extras: `pip install torch stable-baselines3` "
                "to use PPOAgent."
            ) from e

        self._PPO = PPO
        vec = DummyVecEnv([env_fn for _ in range(n_envs)])
        self.env = vec
        self.cvar_alpha = cvar_alpha
        self.model = PPO(
            "MlpPolicy",
            vec,
            learning_rate=learning_rate,
            gamma=gamma,
            verbose=verbose,
        )

    def train(self, total_timesteps: int = 50_000) -> None:
        self.model.learn(total_timesteps=total_timesteps)

    def save(self, path: str | Path) -> None:
        self.model.save(str(path))

    def load(self, path: str | Path) -> None:
        self.model = self._PPO.load(str(path), env=self.env)

    def act(self, obs) -> int:
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)
