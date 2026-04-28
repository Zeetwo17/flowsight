"""End-to-end with Neural Hawkes (research-backed detector).

Trains the NeuralHawkesProcess on the classical Hawkes trajectory as a
teacher (knowledge distillation), then runs the full FlowSight pipeline
with the trained NHP as the cascade detector.

Usage:
    python scripts/run_neural.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

from flowsight.config import DEFAULT
from flowsight.detection import HawkesDetector, NeuralHawkesDetector
from flowsight.events.injector import DisruptionInjector
from flowsight.graph import build_corridor_graph
from flowsight.metrics import summarize_run
from flowsight.simulation import World


def main() -> int:
    graph = build_corridor_graph(n_nodes=DEFAULT.sim.n_nodes, seed=DEFAULT.sim.seed)
    backbone = [n for n, d in graph.nodes(data=True) if d.get("kind") == "backbone"]
    s, t = backbone[0], backbone[-1]

    injector = DisruptionInjector(graph, seed=DEFAULT.sim.seed)
    events = injector.from_schedule(DEFAULT.sim.disruption_schedule)
    timesteps = np.arange(0.0, DEFAULT.sim.horizon_minutes, DEFAULT.sim.timestep_minutes)

    print("[1/3] Running classical Hawkes (teacher)...")
    teacher = HawkesDetector(
        graph,
        base_rate=DEFAULT.hawkes.base_rate,
        alpha=DEFAULT.hawkes.alpha,
        beta=DEFAULT.hawkes.beta,
        spatial_decay=DEFAULT.hawkes.spatial_decay,
    )
    classical_traj = teacher.risk_trajectory(events, timesteps)

    print("[2/3] Distilling Neural Hawkes from teacher (peak-weighted loss)...")
    t0 = time.time()
    nhp = NeuralHawkesDetector(graph, hidden_dim=32)
    losses = nhp.train_on_classical(
        classical_traj, events, timesteps,
        n_epochs=200, lr=1e-2, peak_weight=5.0, verbose=False,
    )
    print(f"  trained {len(losses)} epochs in {time.time()-t0:.1f}s "
          f"(loss {losses[0]:.3f} -> {losses[-1]:.4f})")

    print("[3/3] Running FlowSight world with Neural Hawkes detector...")
    world = World(graph, cfg=DEFAULT, detector=nhp)
    output = world.run(events=events, shipments=[(s, t)])
    kpi = summarize_run(output)

    ship = output.shipments[0]
    print()
    print(f"Shipment {s} -> {t}  (Neural-Hawkes-driven)")
    print(f"  naive       : {ship.naive.path}")
    print(f"  risk-aware  : {ship.risk_aware.path}")
    print()
    width = max(len(k) for k in kpi)
    for k, v in kpi.items():
        print(f"  {k:<{width}}   {v:>10.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
