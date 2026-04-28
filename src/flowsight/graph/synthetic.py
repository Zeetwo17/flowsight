"""Synthetic transit graphs for development and demos.

Each node carries lat/lon in WGS84 so the same data structure works
when we later swap in real OSM graphs.
"""

from __future__ import annotations

import math
import random

import networkx as nx


def build_corridor_graph(
    n_nodes: int = 20,
    seed: int = 42,
    lat_start: float = 28.61,
    lon_start: float = 77.21,
    lat_end: float = 19.08,
    lon_end: float = 72.88,
    bypass_factor: float = 0.25,
    branch_factor: float = 0.2,
) -> nx.DiGraph:
    """A Delhi -> Mumbai-shaped intercity corridor with bypasses.

    Topology:
      - Backbone: linear chain from start -> end (the "highway")
      - Bypasses: 1-2 node alternate paths spanning distant backbone
        nodes (the routing alternatives)
      - Branches: 1-hop dead-ends off the backbone (stress test)
    """
    rng = random.Random(seed)
    g = nx.DiGraph()

    # ---- Backbone ----
    backbone = []
    for i in range(n_nodes):
        t = i / max(n_nodes - 1, 1)
        lat = lat_start + (lat_end - lat_start) * t + rng.uniform(-0.1, 0.1)
        lon = lon_start + (lon_end - lon_start) * t + rng.uniform(-0.1, 0.1)
        g.add_node(i, lat=lat, lon=lon, kind="backbone")
        backbone.append(i)

    for a, b in zip(backbone, backbone[1:]):
        _add_edge(g, a, b)
        _add_edge(g, b, a)

    next_id = n_nodes

    # ---- Bypasses: real alternate routes around chunks of backbone ----
    n_bypasses = max(int(n_nodes * bypass_factor), 2)
    for _ in range(n_bypasses):
        if len(backbone) < 6:
            break
        a_idx = rng.randint(0, len(backbone) - 5)
        span = rng.randint(3, 5)
        b_idx = min(a_idx + span, len(backbone) - 1)
        a, b = backbone[a_idx], backbone[b_idx]

        # Place 1-2 intermediate nodes to one side of the backbone.
        n_inter = rng.randint(1, 2)
        side = rng.choice([-1, 1])
        offset = rng.uniform(0.4, 0.8) * side
        prev = a
        for k in range(n_inter):
            frac = (k + 1) / (n_inter + 1)
            lat_a, lon_a = g.nodes[a]["lat"], g.nodes[a]["lon"]
            lat_b, lon_b = g.nodes[b]["lat"], g.nodes[b]["lon"]
            lat = lat_a + (lat_b - lat_a) * frac + rng.uniform(-0.1, 0.1)
            lon = lon_a + (lon_b - lon_a) * frac + offset + rng.uniform(-0.1, 0.1)
            g.add_node(next_id, lat=lat, lon=lon, kind="bypass")
            _add_edge(g, prev, next_id)
            _add_edge(g, next_id, prev)
            prev = next_id
            next_id += 1
        _add_edge(g, prev, b)
        _add_edge(g, b, prev)

    # ---- Branches: dead-end spurs ----
    n_branches = max(int(n_nodes * branch_factor), 1)
    for _ in range(n_branches):
        anchor = rng.choice(backbone[1:-1]) if len(backbone) > 2 else backbone[0]
        anchor_lat = g.nodes[anchor]["lat"]
        anchor_lon = g.nodes[anchor]["lon"]
        lat = anchor_lat + rng.uniform(-0.4, 0.4)
        lon = anchor_lon + rng.uniform(-0.4, 0.4)
        g.add_node(next_id, lat=lat, lon=lon, kind="branch")
        _add_edge(g, anchor, next_id)
        _add_edge(g, next_id, anchor)
        next_id += 1

    return g


def build_grid_graph(rows: int = 5, cols: int = 5, seed: int = 42) -> nx.DiGraph:
    rng = random.Random(seed)
    g = nx.DiGraph()
    for r in range(rows):
        for c in range(cols):
            node_id = r * cols + c
            g.add_node(
                node_id,
                lat=28.0 + r * 0.05 + rng.uniform(-0.005, 0.005),
                lon=77.0 + c * 0.05 + rng.uniform(-0.005, 0.005),
                kind="grid",
            )
    for r in range(rows):
        for c in range(cols):
            u = r * cols + c
            if c + 1 < cols:
                v = r * cols + (c + 1)
                _add_edge(g, u, v)
                _add_edge(g, v, u)
            if r + 1 < rows:
                v = (r + 1) * cols + c
                _add_edge(g, u, v)
                _add_edge(g, v, u)
    return g


def _add_edge(g: nx.DiGraph, u: int, v: int) -> None:
    if g.has_edge(u, v):
        return
    lat1, lon1 = g.nodes[u]["lat"], g.nodes[u]["lon"]
    lat2, lon2 = g.nodes[v]["lat"], g.nodes[v]["lon"]
    distance_km = _haversine_km(lat1, lon1, lat2, lon2)
    base_speed_kmh = 60.0
    travel_time = max((distance_km / base_speed_kmh) * 60.0, 1.0)
    g.add_edge(
        u, v,
        distance_km=distance_km,
        travel_time=travel_time,
        base_travel_time=travel_time,
        risk=0.0,
        cvar_risk=0.0,
        state_multiplier=1.0,
        co2_per_trip=distance_km * 0.21,  # kg CO2 per km, light truck ballpark
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
