"""FastAPI server exposing FlowSight as a REST + WebSocket service.

Endpoints:
    GET  /health
    GET  /graph          - nodes + edges as JSON
    POST /simulate       - run end-to-end simulation, return frames + routes
    POST /explain        - run Gemini explainer on a route comparison
    WS   /stream         - live cascade frames pushed at 1 Hz

Run locally:
    uvicorn flowsight.api.server:app --reload --port 8080

Deploy to Cloud Run via the Dockerfile at the repo root.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import networkx as nx

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    _HAVE_FASTAPI = True
except ImportError:
    _HAVE_FASTAPI = False
    FastAPI = None  # type: ignore


from ..config import DEFAULT
from ..events.injector import DisruptionInjector
from ..graph import build_corridor_graph
from ..metrics import summarize_run
from ..reasoning import GeminiExplainer
from ..simulation import World


def _serialize_graph(g: nx.DiGraph) -> Dict[str, Any]:
    return {
        "nodes": [
            {
                "id": int(n),
                "lat": float(d.get("lat", 0.0)),
                "lon": float(d.get("lon", 0.0)),
                "kind": d.get("kind", "unknown"),
            }
            for n, d in g.nodes(data=True)
        ],
        "edges": [
            {
                "from": int(u),
                "to": int(v),
                "distance_km": float(d.get("distance_km", 0.0)),
                "base_travel_time": float(d.get("base_travel_time", 0.0)),
            }
            for u, v, d in g.edges(data=True)
        ],
    }


def _serialize_simulation(graph: nx.DiGraph, output) -> Dict[str, Any]:
    nodes = list(graph.nodes())
    return {
        "graph": _serialize_graph(graph),
        "frames": [
            {
                "t": f.t,
                "risk": [float(f.risk[n]) for n in nodes],
                "state": [f.state[n] for n in nodes],
            }
            for f in output.frames
        ],
        "shipments": [
            {
                "id": s.shipment_id,
                "source": s.source,
                "target": s.target,
                "naive": {
                    "path": s.naive.path,
                    "total_time": s.naive.total_time,
                    "total_risk": s.naive.total_risk,
                    "total_co2": s.naive.total_co2,
                },
                "risk_aware": {
                    "path": s.risk_aware.path,
                    "total_time": s.risk_aware.total_time,
                    "total_risk": s.risk_aware.total_risk,
                    "total_co2": s.risk_aware.total_co2,
                },
            }
            for s in output.shipments
        ],
        "events": [
            {
                "t": e.timestamp,
                "target": list(e.target) if isinstance(e.target, tuple) else int(e.target),
                "kind": e.kind,
                "severity": e.severity,
                "source": e.source,
            }
            for e in output.events.all()
        ],
        "kpi": summarize_run(output),
    }


if _HAVE_FASTAPI:

    class SimulateRequest(BaseModel):
        n_nodes: int = Field(DEFAULT.sim.n_nodes, ge=8, le=80)
        seed: int = DEFAULT.sim.seed
        horizon_minutes: float = Field(DEFAULT.sim.horizon_minutes, gt=0)
        n_disruptions: int = Field(4, ge=0, le=20)
        risk_weight: float = Field(DEFAULT.routing.risk_weight, ge=0)
        random_disruptions: bool = True

    class ExplainRequest(BaseModel):
        # The explainer needs a recent simulation; for simplicity we
        # rerun the same simulation deterministically by request payload.
        simulate: SimulateRequest

    app = FastAPI(title="FlowSight API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # dev only — tighten for prod
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "flowsight"}

    @app.get("/graph")
    def get_graph(n_nodes: int = DEFAULT.sim.n_nodes, seed: int = DEFAULT.sim.seed):
        g = build_corridor_graph(n_nodes=n_nodes, seed=seed)
        return _serialize_graph(g)

    @app.post("/simulate")
    def simulate(req: SimulateRequest):
        from dataclasses import replace
        g = build_corridor_graph(n_nodes=req.n_nodes, seed=req.seed)
        cfg = replace(
            DEFAULT,
            sim=replace(DEFAULT.sim, horizon_minutes=req.horizon_minutes, seed=req.seed),
            routing=replace(DEFAULT.routing, risk_weight=req.risk_weight),
        )
        injector = DisruptionInjector(g, seed=req.seed)
        if req.random_disruptions:
            events = injector.random_schedule(
                n_events=req.n_disruptions, horizon=req.horizon_minutes
            )
        else:
            events = injector.from_schedule(DEFAULT.sim.disruption_schedule)
        backbone = [n for n, d in g.nodes(data=True) if d.get("kind") == "backbone"]
        if len(backbone) < 2:
            raise HTTPException(400, "graph has too few backbone nodes")
        world = World(g, cfg=cfg)
        output = world.run(events=events, shipments=[(backbone[0], backbone[-1])])
        return _serialize_simulation(g, output)

    @app.post("/explain")
    def explain(req: ExplainRequest):
        from dataclasses import replace
        s = req.simulate
        g = build_corridor_graph(n_nodes=s.n_nodes, seed=s.seed)
        cfg = replace(
            DEFAULT,
            sim=replace(DEFAULT.sim, horizon_minutes=s.horizon_minutes, seed=s.seed),
            routing=replace(DEFAULT.routing, risk_weight=s.risk_weight),
        )
        injector = DisruptionInjector(g, seed=s.seed)
        events = injector.random_schedule(n_events=s.n_disruptions, horizon=s.horizon_minutes) \
                 if s.random_disruptions else \
                 injector.from_schedule(DEFAULT.sim.disruption_schedule)
        backbone = [n for n, d in g.nodes(data=True) if d.get("kind") == "backbone"]
        world = World(g, cfg=cfg)
        output = world.run(events=events, shipments=[(backbone[0], backbone[-1])])
        ship = output.shipments[0]
        states = {n: g.nodes[n].get("state", "Normal") for n in g.nodes()}
        triggering = [(e.timestamp, e.origin_node, e.kind) for e in output.events.all()]
        explainer = GeminiExplainer()
        result = explainer.explain_reroute(ship.naive, ship.risk_aware, states, triggering)
        return {"explanation": result.text, "used_llm": result.used_llm, "model": result.model}

    @app.websocket("/stream")
    async def stream(ws: WebSocket):
        """Push cascade frames at 1 frame/sec for live UI animation."""
        await ws.accept()
        try:
            params = ws.query_params
            n_nodes = int(params.get("n_nodes", DEFAULT.sim.n_nodes))
            seed = int(params.get("seed", DEFAULT.sim.seed))
            horizon = float(params.get("horizon_minutes", DEFAULT.sim.horizon_minutes))
            n_dis = int(params.get("n_disruptions", 4))

            g = build_corridor_graph(n_nodes=n_nodes, seed=seed)
            injector = DisruptionInjector(g, seed=seed)
            events = injector.random_schedule(n_events=n_dis, horizon=horizon)
            world = World(g, cfg=DEFAULT)
            output = world.run(events=events)
            nodes = list(g.nodes())
            await ws.send_text(json.dumps({"type": "graph", "data": _serialize_graph(g)}))
            for f in output.frames:
                payload = {
                    "type": "frame",
                    "t": f.t,
                    "risk": [float(f.risk[n]) for n in nodes],
                    "state": [f.state[n] for n in nodes],
                }
                await ws.send_text(json.dumps(payload))
                await asyncio.sleep(0.05)
            await ws.send_text(json.dumps({
                "type": "summary",
                "data": _serialize_simulation(g, output),
            }))
        except WebSocketDisconnect:
            return

else:  # pragma: no cover
    app = None
