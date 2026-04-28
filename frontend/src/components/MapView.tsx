import { useMemo } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import type { SimulationDTO } from "../types";

const STATE_COLOR: Record<string, string> = {
  Normal: "#46c878",
  Stressed: "#f0b43c",
  Critical: "#dc3c3c"
};

interface Props {
  sim: SimulationDTO;
  frameIdx: number;
}

export default function MapView({ sim, frameIdx }: Props) {
  const center = useMemo<LatLngExpression>(() => {
    if (!sim.graph.nodes.length) return [22, 75];
    const lat = sim.graph.nodes.reduce((s, n) => s + n.lat, 0) / sim.graph.nodes.length;
    const lon = sim.graph.nodes.reduce((s, n) => s + n.lon, 0) / sim.graph.nodes.length;
    return [lat, lon];
  }, [sim.graph]);

  const ship = sim.shipments[0];
  const frame = sim.frames[Math.min(frameIdx, sim.frames.length - 1)];

  const nodeIndex = useMemo(() => {
    const m: Record<number, number> = {};
    sim.graph.nodes.forEach((n, i) => (m[n.id] = i));
    return m;
  }, [sim.graph.nodes]);

  function pathCoords(path: number[]): LatLngExpression[] {
    return path.map((id) => {
      const n = sim.graph.nodes.find((x) => x.id === id);
      return n ? [n.lat, n.lon] : [0, 0];
    });
  }

  // Active disruption events visible at this frame
  const activeEvents = sim.events.filter((e) => e.t <= frame.t);

  return (
    <MapContainer
      center={center}
      zoom={5}
      className="h-full w-full"
      scrollWheelZoom
      style={{ background: "#1e293b" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* underlying network — faint */}
      {sim.graph.edges.map((e, i) => {
        const a = sim.graph.nodes.find((n) => n.id === e.from);
        const b = sim.graph.nodes.find((n) => n.id === e.to);
        if (!a || !b) return null;
        return (
          <Polyline
            key={`e${i}`}
            positions={[[a.lat, a.lon], [b.lat, b.lon]]}
            pathOptions={{ color: "#475569", weight: 1, opacity: 0.35 }}
          />
        );
      })}

      {ship && (
        <>
          <Polyline
            positions={pathCoords(ship.naive.path)}
            pathOptions={{
              color: "#94a3b8",
              weight: 4,
              opacity: 0.85,
              dashArray: "6 6"
            }}
          />
          <Polyline
            positions={pathCoords(ship.risk_aware.path)}
            pathOptions={{ color: "#3282fa", weight: 5, opacity: 0.95 }}
          />
        </>
      )}

      {/* disruption pulses */}
      {activeEvents.map((e, i) => {
        if (Array.isArray(e.target)) return null;
        const node = sim.graph.nodes.find((n) => n.id === e.target);
        if (!node) return null;
        return (
          <CircleMarker
            key={`ev${i}`}
            center={[node.lat, node.lon]}
            radius={14}
            pathOptions={{
              color: "#dc3c3c",
              fillColor: "#dc3c3c",
              fillOpacity: 0.15,
              weight: 1
            }}
          />
        );
      })}

      {sim.graph.nodes.map((n) => {
        const idx = nodeIndex[n.id];
        const state = frame?.state[idx] ?? "Normal";
        const risk = frame?.risk[idx] ?? 0;
        const radius = state === "Critical" ? 9 : state === "Stressed" ? 7 : 6;
        return (
          <CircleMarker
            key={n.id}
            center={[n.lat, n.lon]}
            radius={radius}
            pathOptions={{
              color: "#0f172a",
              fillColor: STATE_COLOR[state],
              fillOpacity: 0.95,
              weight: 1.2
            }}
          >
            <Popup>
              <div className="text-xs text-slate-900">
                <div>
                  <strong>node {n.id}</strong> ({n.kind})
                </div>
                <div>
                  state: <strong>{state}</strong>
                </div>
                <div>risk: {risk.toFixed(3)}</div>
                <div>lat/lon: {n.lat.toFixed(3)}, {n.lon.toFixed(3)}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
