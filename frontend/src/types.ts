export interface GraphNode {
  id: number;
  lat: number;
  lon: number;
  kind: string;
}

export interface GraphEdge {
  from: number;
  to: number;
  distance_km: number;
  base_travel_time: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FrameRow {
  t: number;
  risk: number[];
  state: ("Normal" | "Stressed" | "Critical")[];
}

export interface RouteResultDTO {
  path: number[];
  total_time: number;
  total_risk: number;
  total_co2: number;
}

export interface ShipmentDTO {
  id: number;
  source: number;
  target: number;
  naive: RouteResultDTO;
  risk_aware: RouteResultDTO;
}

export interface EventDTO {
  t: number;
  target: number | number[];
  kind: string;
  severity: number;
  source: string;
}

export interface SimulationDTO {
  graph: GraphPayload;
  frames: FrameRow[];
  shipments: ShipmentDTO[];
  events: EventDTO[];
  kpi: Record<string, number>;
}

export interface ExplanationDTO {
  explanation: string;
  used_llm: boolean;
  model: string;
}

export interface SimulateRequest {
  n_nodes: number;
  seed: number;
  horizon_minutes: number;
  n_disruptions: number;
  risk_weight: number;
  random_disruptions: boolean;
}
