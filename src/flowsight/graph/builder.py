"""OSM-backed real road graphs.

Optional — only imports osmnx when called. The synthetic module covers
the demo path; this is for the production-grade story.
"""

from __future__ import annotations

import networkx as nx


def load_osm_graph(
    place: str = "Delhi, India",
    network_type: str = "drive",
    simplify: bool = True,
) -> nx.DiGraph:
    """Load a real road network from OpenStreetMap via osmnx.

    Returns a `networkx.DiGraph` with the same node/edge attribute schema
    as `synthetic.build_corridor_graph` so downstream code is graph-source
    agnostic.
    """
    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError(
            "osmnx is not installed. Install via `pip install osmnx` to use real road graphs."
        ) from e

    raw = ox.graph_from_place(place, network_type=network_type, simplify=simplify)
    raw = ox.add_edge_speeds(raw)
    raw = ox.add_edge_travel_times(raw)

    g = nx.DiGraph()
    for node, data in raw.nodes(data=True):
        g.add_node(node, lat=data["y"], lon=data["x"], kind="osm")
    for u, v, data in raw.edges(data=True):
        distance_km = data.get("length", 0.0) / 1000.0
        travel_time = data.get("travel_time", distance_km / 60.0 * 3600.0) / 60.0
        travel_time = max(travel_time, 0.5)
        g.add_edge(
            u, v,
            distance_km=distance_km,
            travel_time=travel_time,
            base_travel_time=travel_time,
            risk=0.0,
            cvar_risk=0.0,
            state_multiplier=1.0,
            co2_per_trip=distance_km * 0.21,
        )
    return g
