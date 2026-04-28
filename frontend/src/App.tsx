import { useEffect, useRef, useState } from "react";
import MapView from "./components/MapView";
import CascadeChart from "./components/CascadeChart";
import KPIBar from "./components/KPIBar";
import RouteCompare from "./components/RouteCompare";
import EventLog from "./components/EventLog";
import ExplanationPanel from "./components/ExplanationPanel";
import Sidebar from "./components/Sidebar";
import Timeline from "./components/Timeline";
import { runSimulation, explainRoute, pingHealth } from "./api";
import type { SimulateRequest, SimulationDTO, ExplanationDTO } from "./types";

const DEFAULTS: SimulateRequest = {
  n_nodes: 20,
  seed: 42,
  horizon_minutes: 120,
  n_disruptions: 4,
  risk_weight: 5,
  random_disruptions: true
};

type WakeStatus = "checking" | "warm" | "cold" | "down";

export default function App() {
  const [params, setParams] = useState<SimulateRequest>(DEFAULTS);
  const [sim, setSim] = useState<SimulationDTO | null>(null);
  const [explanation, setExplanation] = useState<ExplanationDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wake, setWake] = useState<WakeStatus>("checking");
  const [wakeMsg, setWakeMsg] = useState<string>("Checking backend...");

  // timeline
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const playerRef = useRef<number | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const result = await runSimulation(params);
      setSim(result);
      setFrameIdx(result.frames.length - 1);
      setExplanation(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function explain() {
    setExplaining(true);
    try {
      const r = await explainRoute(params);
      setExplanation(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setExplaining(false);
    }
  }

  // On mount: probe /health, then ALWAYS auto-run simulation once awake.
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      setWake("checking");
      setWakeMsg("Checking backend...");
      const t0 = performance.now();
      const maxAttempts = 6;
      for (let i = 0; i < maxAttempts; i++) {
        if (cancelled) return;
        const ok = await pingHealth();
        if (ok) {
          if (cancelled) return;
          const dt = performance.now() - t0;
          setWake(dt < 5000 ? "warm" : "cold");
          setWakeMsg(dt < 5000 ? "Backend ready." : `Backend woke up after ${(dt / 1000).toFixed(0)}s.`);
          // Always auto-run once awake.
          refresh();
          return;
        }
        setWakeMsg(`Waking backend... (${i + 1}/${maxAttempts}, ~${5 * (i + 1)}s)`);
        await new Promise((r) => setTimeout(r, 5000));
      }
      if (!cancelled) {
        setWake("down");
        setWakeMsg("Backend didn't respond. Click Run simulation to retry.");
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cascade animation timer
  useEffect(() => {
    if (!playing || !sim) return;
    const id = window.setInterval(() => {
      setFrameIdx((i) => {
        const last = sim.frames.length - 1;
        if (i >= last) {
          setPlaying(false);
          return last;
        }
        return i + 1;
      });
    }, 50);
    playerRef.current = id;
    return () => window.clearInterval(id);
  }, [playing, sim]);

  function togglePlay() {
    if (!sim) return;
    if (frameIdx >= sim.frames.length - 1) setFrameIdx(0);
    setPlaying((p) => !p);
  }

  return (
    <div className="h-full grid grid-rows-[auto_1fr] bg-ink text-slate-100">
      {/* Header */}
      <header className="px-4 py-3 border-b border-slate-800 flex items-center justify-between gap-3 bg-ink2/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <button
            className="lg:hidden bg-ink2 hover:bg-slate-700 rounded px-2 py-1 text-sm border border-slate-700"
            onClick={() => setSidebarOpen((s) => !s)}
            aria-label="Toggle sidebar"
          >
            ☰
          </button>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              FlowSight
              <span className="ml-2 text-xs uppercase tracking-widest text-accent">
                ripple-effect mitigation
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5 hidden sm:block">
              Hawkes · HMM · Risk-aware Dijkstra · CVaR · Gemini
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="hidden sm:inline-flex bg-ink2 border border-slate-700 rounded px-2 py-1 text-slate-300">
            SDG 9 · 11 · 12 · 13
          </span>
          <BackendBadge wake={wake} />
        </div>
      </header>

      {/* Main */}
      <div className="grid lg:grid-cols-[300px_1fr] overflow-hidden relative">
        <div
          className={`${sidebarOpen ? "block absolute inset-0 z-30 lg:relative" : "hidden lg:block"}`}
          onClick={(e) => {
            if (e.target === e.currentTarget) setSidebarOpen(false);
          }}
        >
          <Sidebar
            params={params}
            onChange={setParams}
            onRun={() => {
              setSidebarOpen(false);
              refresh();
            }}
            onExplain={() => {
              setSidebarOpen(false);
              explain();
            }}
            loading={loading}
            explaining={explaining}
          />
        </div>

        <main className="overflow-auto p-4 grid grid-rows-[auto_auto_1fr_auto] gap-3">
          {/* KPIs */}
          {sim ? (
            <KPIBar kpi={sim.kpi} />
          ) : (
            <KPIBar kpi={{}} placeholder />
          )}

          {/* Status banners */}
          {wake === "checking" && (
            <Banner tone="info">{wakeMsg}</Banner>
          )}
          {wake === "cold" && !sim && !loading && (
            <Banner tone="warn">
              {wakeMsg} Render free-tier sleeps after 15 min idle.
            </Banner>
          )}
          {wake === "down" && !sim && (
            <Banner tone="error">
              {wakeMsg}{" "}
              <a className="text-accent underline" href="https://flowsight-api-ylyx.onrender.com/health" target="_blank" rel="noreferrer">
                open /health
              </a>
            </Banner>
          )}
          {error && <Banner tone="error">{error}</Banner>}
          {loading && <Banner tone="info">Running simulation...</Banner>}

          {/* Main grid */}
          {sim ? (
            <section className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-3 min-h-[480px]">
              {/* Left: Map + Timeline */}
              <div className="bg-ink2 rounded-lg border border-slate-700 overflow-hidden flex flex-col min-h-[480px]">
                <div className="flex-1 min-h-[360px]">
                  <MapView sim={sim} frameIdx={frameIdx} />
                </div>
                <Timeline
                  frames={sim.frames}
                  frameIdx={frameIdx}
                  setFrameIdx={setFrameIdx}
                  playing={playing}
                  onTogglePlay={togglePlay}
                />
              </div>

              {/* Right: cascade + routes */}
              <div className="grid grid-rows-[1fr_auto] gap-3 min-h-[480px]">
                <div className="bg-ink2 rounded-lg p-3 border border-slate-700 min-h-[240px]">
                  <CascadeChart sim={sim} cursorT={sim.frames[frameIdx]?.t ?? 0} />
                </div>
                <div className="bg-ink2 rounded-lg p-3 border border-slate-700 overflow-auto">
                  <RouteCompare sim={sim} />
                </div>
              </div>
            </section>
          ) : (
            <EmptyState loading={loading || wake === "checking"} />
          )}

          {/* Footer rows */}
          {sim && (
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <EventLog events={sim.events} />
              <ExplanationPanel explanation={explanation} loading={explaining} />
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function BackendBadge({ wake }: { wake: WakeStatus }) {
  const map = {
    checking: { color: "bg-amber-500", text: "checking" },
    warm: { color: "bg-emerald-500", text: "live" },
    cold: { color: "bg-emerald-500", text: "live" },
    down: { color: "bg-red-500", text: "down" }
  };
  const m = map[wake];
  return (
    <span className="inline-flex items-center gap-1.5 bg-ink2 border border-slate-700 rounded px-2 py-1 text-slate-300">
      <span className={`w-2 h-2 rounded-full ${m.color} ${wake === "checking" ? "animate-pulse" : ""}`} />
      backend {m.text}
    </span>
  );
}

function Banner({
  tone,
  children
}: {
  tone: "info" | "warn" | "error";
  children: React.ReactNode;
}) {
  const styles = {
    info: "bg-blue-900/30 border-blue-700/50 text-blue-100",
    warn: "bg-amber-900/30 border-amber-700/60 text-amber-100",
    error: "bg-red-900/30 border-red-700/60 text-red-100"
  };
  return (
    <div className={`rounded p-3 text-sm border ${styles[tone]}`}>{children}</div>
  );
}

function EmptyState({ loading }: { loading: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400">
      <div className="w-16 h-16 rounded-full bg-ink2 border border-slate-700 flex items-center justify-center mb-4">
        <span className="text-2xl">{loading ? "⟳" : "◷"}</span>
      </div>
      <p className="text-base">
        {loading ? "Running first simulation..." : "Click Run simulation in the sidebar to start"}
      </p>
      <p className="text-xs mt-1">
        First call may take 30–60s while the backend wakes up.
      </p>
    </div>
  );
}
