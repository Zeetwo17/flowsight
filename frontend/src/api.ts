import type { ExplanationDTO, SimulateRequest, SimulationDTO } from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

export async function runSimulation(req: SimulateRequest): Promise<SimulationDTO> {
  const r = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req)
  });
  if (!r.ok) throw new Error(`simulate failed: ${r.status}`);
  return r.json();
}

export async function explainRoute(req: SimulateRequest): Promise<ExplanationDTO> {
  const r = await fetch(`${BASE}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ simulate: req })
  });
  if (!r.ok) throw new Error(`explain failed: ${r.status}`);
  return r.json();
}
