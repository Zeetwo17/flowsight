"""End-to-end CLI runner — no ML deps required.

Usage:
    python scripts/run_simulation.py
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
from flowsight.metrics import summarize_run
from flowsight.simulation import World


def main() -> int:
    graph = build_corridor_graph(n_nodes=DEFAULT.sim.n_nodes, seed=DEFAULT.sim.seed)
    backbone = [n for n, d in graph.nodes(data=True) if d.get("kind") == "backbone"]
    s, t = backbone[0], backbone[-1]

    injector = DisruptionInjector(graph, seed=DEFAULT.sim.seed)
    events = injector.from_schedule(DEFAULT.sim.disruption_schedule)

    world = World(graph, cfg=DEFAULT)
    output = world.run(events=events, shipments=[(s, t)])

    kpi = summarize_run(output)
    print()
    print(f"FlowSight | {len(graph.nodes())} nodes, "
          f"{len(graph.edges())} edges, {len(events)} disruptions")
    print(f"Shipment {s} -> {t}")
    print()
    ship = output.shipments[0]
    print(f"  naive       : {ship.naive.path}")
    print(f"  risk-aware  : {ship.risk_aware.path}")
    print()
    width = max(len(k) for k in kpi)
    for k, v in kpi.items():
        print(f"  {k:<{width}}   {v:>10.3f}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
