"""Train a PPO agent on the supply-chain env. Requires torch + sb3.

Install ML extras first:
    pip install torch stable-baselines3

Then:
    python scripts/train_agent.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flowsight.config import DEFAULT
from flowsight.events.injector import DisruptionInjector
from flowsight.graph import build_corridor_graph
from flowsight.routing.env import SupplyChainEnv
from flowsight.simulation import World


def make_env_factory():
    """Each parallel env gets its own random disruption schedule so the
    PPO agent generalises across cascade scenarios."""

    counter = {"i": 0}

    def _factory():
        seed = DEFAULT.sim.seed + counter["i"]
        counter["i"] += 1
        graph = build_corridor_graph(n_nodes=DEFAULT.sim.n_nodes, seed=seed)
        injector = DisruptionInjector(graph, seed=seed)
        events = injector.random_schedule(
            n_events=4, horizon=DEFAULT.sim.horizon_minutes
        )
        world = World(graph, cfg=DEFAULT)
        backbone = [n for n, d in graph.nodes(data=True) if d.get("kind") == "backbone"]
        s, t = backbone[0], backbone[-1]
        world.run(events=events, shipments=[(s, t)])
        return SupplyChainEnv(
            graph, source=s, target=t,
            risk_weight=DEFAULT.routing.risk_weight,
            co2_weight=DEFAULT.routing.co2_weight,
        )

    return _factory


def main() -> int:
    from flowsight.rl import PPOAgent

    agent = PPOAgent(
        env_fn=make_env_factory(),
        n_envs=DEFAULT.rl.n_envs,
        learning_rate=DEFAULT.rl.learning_rate,
        gamma=DEFAULT.rl.gamma,
        cvar_alpha=DEFAULT.rl.cvar_alpha,
        verbose=1,
    )
    agent.train(total_timesteps=DEFAULT.rl.total_timesteps)

    out = REPO / "artifacts"
    out.mkdir(exist_ok=True)
    agent.save(out / "ppo_flowsight.zip")
    print(f"Saved agent -> {out / 'ppo_flowsight.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
