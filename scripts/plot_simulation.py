"""Static matplotlib visualization — no server, just a PNG.

    python scripts/plot_simulation.py

Saves artifacts/simulation.png with three panels:
  1. Map view: corridor + naive vs risk-aware routes
  2. Cascade heatmap: Hawkes intensity per node over time
  3. KPI bar comparison: naive vs risk-aware
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import matplotlib.pyplot as plt
import numpy as np

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
    ship = output.shipments[0]

    fig = plt.figure(figsize=(16, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.2, 1.4, 1.0])

    # ----- 1. Map view -----
    ax_map = fig.add_subplot(gs[0, 0])
    state_color = {"Normal": "#46c878", "Stressed": "#f0b43c", "Critical": "#dc3c3c"}
    for u, v in graph.edges():
        x = [graph.nodes[u]["lon"], graph.nodes[v]["lon"]]
        y = [graph.nodes[u]["lat"], graph.nodes[v]["lat"]]
        ax_map.plot(x, y, color="#dddddd", lw=0.6, zorder=1)
    for u, v in zip(ship.naive.path[:-1], ship.naive.path[1:]):
        x = [graph.nodes[u]["lon"], graph.nodes[v]["lon"]]
        y = [graph.nodes[u]["lat"], graph.nodes[v]["lat"]]
        ax_map.plot(x, y, color="#888", lw=2.5, zorder=2,
                    label="naive" if (u, v) == (ship.naive.path[0], ship.naive.path[1]) else None)
    for u, v in zip(ship.risk_aware.path[:-1], ship.risk_aware.path[1:]):
        x = [graph.nodes[u]["lon"], graph.nodes[v]["lon"]]
        y = [graph.nodes[u]["lat"], graph.nodes[v]["lat"]]
        ax_map.plot(x, y, color="#3282fa", lw=3.0, zorder=3,
                    label="risk-aware" if (u, v) == (ship.risk_aware.path[0], ship.risk_aware.path[1]) else None)
    for n, data in graph.nodes(data=True):
        c = state_color[data.get("state", "Normal")]
        ax_map.scatter(data["lon"], data["lat"], c=c, s=60,
                       edgecolors="black", linewidths=0.6, zorder=4)
    ax_map.set_title("Routes  ·  green/yellow/red = node state")
    ax_map.set_xlabel("lon")
    ax_map.set_ylabel("lat")
    ax_map.legend(loc="upper right")

    # ----- 2. Cascade heatmap -----
    ax_heat = fig.add_subplot(gs[0, 1])
    nodes = list(graph.nodes())
    risk_matrix = np.array([[f.risk[n] for n in nodes] for f in output.frames])
    im = ax_heat.imshow(
        risk_matrix.T, aspect="auto", cmap="hot_r", origin="lower",
        extent=[0, output.frames[-1].t, 0, len(nodes)],
    )
    fig.colorbar(im, ax=ax_heat, label="Hawkes intensity")
    ax_heat.set_title("Cascade  ·  Hawkes intensity across nodes over time")
    ax_heat.set_xlabel("time (min)")
    ax_heat.set_ylabel("node index")

    # ----- 3. KPI bars -----
    ax_kpi = fig.add_subplot(gs[0, 2])
    kpi = summarize_run(output)
    labels = ["time (min)", "risk", "CO2 (kg)"]
    naive_vals = [kpi["naive_total_time"], kpi["naive_total_risk"] * 50, kpi["naive_total_co2"]]
    risk_vals = [kpi["risk_aware_total_time"], kpi["risk_aware_total_risk"] * 50, kpi["risk_aware_total_co2"]]
    x = np.arange(len(labels))
    w = 0.35
    ax_kpi.bar(x - w / 2, naive_vals, w, label="naive", color="#888")
    ax_kpi.bar(x + w / 2, risk_vals, w, label="risk-aware", color="#3282fa")
    ax_kpi.set_xticks(x)
    ax_kpi.set_xticklabels(labels)
    ax_kpi.set_title("Outcomes  ·  naive vs risk-aware")
    ax_kpi.legend()
    ax_kpi.grid(True, axis="y", alpha=0.3)

    out_dir = REPO / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "simulation.png"
    fig.suptitle(
        f"FlowSight  |  shipment {s} -> {t}  |  "
        f"time saved {kpi['time_saved']:.0f} min  |  "
        f"risk avoided {kpi['risk_avoided']:.2f}",
        fontsize=13,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
