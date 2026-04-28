"""Central configuration for FlowSight.

All tunable knobs live here so experiments are reproducible. Defaults
are picked for the demo scenario (synthetic 20-node Delhi-Mumbai
corridor) and overridden at runtime via dataclasses.replace().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class HawkesConfig:
    base_rate: float = 0.05
    alpha: float = 0.8
    beta: float = 0.05         # 1/(20 min) — supply-chain disruptions persist
    spatial_decay: float = 0.02  # 1/km — so neighbours feel the cascade


@dataclass
class HMMConfig:
    n_states: int = 3
    state_names: Tuple[str, ...] = ("Normal", "Stressed", "Critical")
    n_iter: int = 50


@dataclass
class RoutingConfig:
    risk_weight: float = 5.0
    cvar_alpha: float = 0.1
    cvar_weight: float = 2.0
    co2_weight: float = 0.5


@dataclass
class SimConfig:
    seed: int = 42
    n_nodes: int = 20
    horizon_minutes: float = 120.0
    timestep_minutes: float = 1.0
    n_shipments: int = 1
    disruption_schedule: Tuple = (
        (15.0, "node", 5),
        (35.0, "node", 7),
        (55.0, "edge", (10, 11)),
    )


@dataclass
class RLConfig:
    total_timesteps: int = 50_000
    n_envs: int = 4
    learning_rate: float = 3e-4
    gamma: float = 0.99
    cvar_alpha: float = 0.1


@dataclass
class FlowSightConfig:
    hawkes: HawkesConfig = field(default_factory=HawkesConfig)
    hmm: HMMConfig = field(default_factory=HMMConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    sim: SimConfig = field(default_factory=SimConfig)
    rl: RLConfig = field(default_factory=RLConfig)


DEFAULT = FlowSightConfig()
