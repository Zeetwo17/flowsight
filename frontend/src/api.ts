import type { ExplanationDTO, SimulateRequest, SimulationDTO } from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

async function postJSON<T>(path: string, body: unknown, timeoutMs = 120_000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal
    });
    if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
    return r.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

export async function pingHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/health`, { method: "GET" });
    return r.ok;
  } catch {
    return false;
  }
}

export function runSimulation(req: SimulateRequest): Promise<SimulationDTO> {
  return postJSON<SimulationDTO>("/simulate", req);
}

export function explainRoute(req: SimulateRequest): Promise<ExplanationDTO> {
  return postJSON<ExplanationDTO>("/explain", { simulate: req });
}
