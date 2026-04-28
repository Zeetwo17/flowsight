"""Interactive demo — Streamlit + pydeck.

Run from the repo root:

    streamlit run src/flowsight/viz/streamlit_app.py

Configure parameters in the sidebar, then click 'Run simulation' to:
- inject the configured cascade
- watch HMM state labels evolve along the corridor
- compare naive vs risk-aware routes side-by-side
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from flowsight.config import DEFAULT
from flowsight.events.injector import DisruptionInjector
from flowsight.graph import build_corridor_graph
from flowsight.metrics import summarize_run
from flowsight.simulation import World


st.set_page_config(page_title="FlowSight", layout="wide")
st.title("FlowSight  ·  Supply Chain Ripple-Effect Mitigation")
st.caption(
    "Hawkes cascade detection · HMM state estimation · Risk-aware routing · "
    "research-backed digital twin"
)

with st.sidebar:
    st.header("Scenario")
    n_nodes = st.slider("Backbone nodes", 10, 40, DEFAULT.sim.n_nodes)
    horizon = st.slider("Horizon (min)", 30, 240, int(DEFAULT.sim.horizon_minutes))
    seed = int(st.number_input("Seed", value=DEFAULT.sim.seed, step=1))
    n_disruptions = st.slider("Disruptions", 1, 12, 4)
    risk_weight = st.slider(
        "λ — risk weight",
        0.0, 20.0, float(DEFAULT.routing.risk_weight),
    )
    st.markdown("---")
    st.markdown(
        "**Pipeline**\n\n"
        "`Hawkes → HMM → Risk-aware Dijkstra`\n\n"
        "Hawkes models cascade arrivals; HMM labels each node "
        "(Normal / Stressed / Critical); Dijkstra routes on "
        "`travel_time × multiplier + λ·risk + γ·CO₂`."
    )
    run_btn = st.button("Run simulation", type="primary")

if "output" not in st.session_state:
    st.session_state.output = None
    st.session_state.graph = None

if run_btn:
    graph = build_corridor_graph(n_nodes=n_nodes, seed=seed)
    cfg = replace(
        DEFAULT,
        sim=replace(DEFAULT.sim, horizon_minutes=float(horizon), seed=seed),
        routing=replace(DEFAULT.routing, risk_weight=float(risk_weight)),
    )

    injector = DisruptionInjector(graph, seed=seed)
    events = injector.random_schedule(n_events=n_disruptions, horizon=float(horizon))

    world = World(graph, cfg=cfg)
    backbone = [n for n, d in graph.nodes(data=True) if d.get("kind") == "backbone"]
    shipments = [(backbone[0], backbone[-1])]
    output = world.run(events=events, shipments=shipments)
    st.session_state.output = output
    st.session_state.graph = graph

if st.session_state.output is None:
    st.info("Set parameters in the sidebar and click **Run simulation**.")
    st.stop()

output = st.session_state.output
graph = st.session_state.graph

# ---------------- KPIs ----------------
kpi = summarize_run(output)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Shipments", int(kpi["shipments"]))
c2.metric("Time saved (min)", f"{kpi['time_saved']:.1f}")
c3.metric("CO₂ saved (kg)", f"{kpi['co2_saved']:.2f}")
c4.metric("Risk avoided", f"{kpi['risk_avoided']:.2f}")

# ---------------- Map ----------------
st.subheader("Network state — final frame")

frame = output.frames[-1]
state_color = {
    "Normal":   [70, 200, 120],
    "Stressed": [240, 180, 60],
    "Critical": [220, 60, 60],
}
node_rows = []
for n, data in graph.nodes(data=True):
    s = frame.state[n]
    node_rows.append({
        "node": n,
        "lat": data["lat"],
        "lon": data["lon"],
        "risk": round(frame.risk[n], 3),
        "state": s,
        "color": state_color[s],
    })
nodes_df = pd.DataFrame(node_rows)

ship = output.shipments[0]


def edges_to_df(path, color):
    rows = []
    for u, v in zip(path[:-1], path[1:]):
        rows.append({
            "from_lat": graph.nodes[u]["lat"], "from_lon": graph.nodes[u]["lon"],
            "to_lat": graph.nodes[v]["lat"],   "to_lon": graph.nodes[v]["lon"],
            "color": color,
        })
    return pd.DataFrame(rows)


naive_edges = edges_to_df(ship.naive.path, [120, 120, 120])
risk_edges = edges_to_df(ship.risk_aware.path, [50, 130, 250])

view = pdk.ViewState(
    latitude=float(nodes_df["lat"].mean()),
    longitude=float(nodes_df["lon"].mean()),
    zoom=4.5,
)
layers = [
    pdk.Layer(
        "LineLayer",
        data=naive_edges,
        get_source_position="[from_lon, from_lat]",
        get_target_position="[to_lon, to_lat]",
        get_color="color",
        get_width=3,
    ),
    pdk.Layer(
        "LineLayer",
        data=risk_edges,
        get_source_position="[from_lon, from_lat]",
        get_target_position="[to_lon, to_lat]",
        get_color="color",
        get_width=5,
    ),
    pdk.Layer(
        "ScatterplotLayer",
        data=nodes_df,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius=8000,
        pickable=True,
    ),
]
st.pydeck_chart(pdk.Deck(
    initial_view_state=view,
    layers=layers,
    tooltip={"text": "Node {node}\nState: {state}\nRisk: {risk}"},
))

st.markdown(
    "**Legend** · grey: naive shortest path · blue: risk-aware route · "
    "green/yellow/red: HMM state (Normal / Stressed / Critical)"
)

# ---------------- Cascade time series ----------------
st.subheader("Cascade — Hawkes intensity over time")
all_nodes = list(graph.nodes())
risk_matrix = np.array([[f.risk[n] for n in all_nodes] for f in output.frames])
risk_df = pd.DataFrame(
    risk_matrix,
    index=[f.t for f in output.frames],
    columns=[f"node {n}" for n in all_nodes],
)
backbone_cols = [f"node {n}" for n, d in graph.nodes(data=True)
                 if d.get("kind") == "backbone"]
st.line_chart(risk_df[backbone_cols], height=300)

# ---------------- Routes ----------------
st.subheader("Route comparison")
route_table = pd.DataFrame([
    {
        "mode": "naive",
        "hops": len(ship.naive.path) - 1,
        "time (min)": round(ship.naive.total_time, 2),
        "risk": round(ship.naive.total_risk, 3),
        "CO₂ (kg)": round(ship.naive.total_co2, 2),
        "cost": round(ship.naive.total_cost, 2),
    },
    {
        "mode": "risk-aware",
        "hops": len(ship.risk_aware.path) - 1,
        "time (min)": round(ship.risk_aware.total_time, 2),
        "risk": round(ship.risk_aware.total_risk, 3),
        "CO₂ (kg)": round(ship.risk_aware.total_co2, 2),
        "cost": round(ship.risk_aware.total_cost, 2),
    },
])
st.dataframe(route_table, hide_index=True, use_container_width=True)
st.write(f"**Naive path:**       `{ship.naive.path}`")
st.write(f"**Risk-aware path:** `{ship.risk_aware.path}`")

with st.expander("Injected events"):
    ev_rows = [{
        "t (min)": round(e.timestamp, 2),
        "target": str(e.target),
        "kind": e.kind,
        "severity": round(e.severity, 2),
    } for e in output.events.all()]
    st.dataframe(pd.DataFrame(ev_rows), hide_index=True, use_container_width=True)
