# FlowSight

> **A digital twin for supply chain ripple-effect mitigation.**

FlowSight is a research-backed, end-to-end system that:

1. Detects early signals of supply chain disruptions from multifaceted live data
2. Models how disruptions cascade across a transit network
3. Recommends — or autonomously executes — risk-aware route adjustments before failures spread

Built for the **Google Solution Challenge**. Aligned with UN SDGs **9, 11, 12, 13**.

---

## Pipeline

```
[ Hawkes / HMM ]   →   [ Risk / State Estimation ]   →   [ RL Policy + Dijkstra ]
   detection                  representation                      decision
```

## Research grounding

| Layer | Paper |
|---|---|
| Cascade detection (baseline) | Hawkes — *Spectra of self-exciting point processes*, Biometrika 1971 |
| Cascade detection (advanced) | Mei & Eisner — *The Neural Hawkes Process*, NeurIPS 2017 |
| Spatio-temporal forecasting | Li et al. — *DCRNN*, ICLR 2018 |
| State estimation | Rabiner — *HMM tutorial*, Proc. IEEE 1989 |
| Risk-aware policy learning | Schulman et al. — *PPO*, 2017 |
| Tail-risk objective | Rockafellar & Uryasev — *Optimization of CVaR*, 2000 |
| Problem framing | Ivanov & Dolgui — *Ripple effect in supply chains*, IJPR 2020 |
| Headline metric | Bruneau et al. — *Resilience triangle*, Earthquake Spectra 2003 |

---

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# 1. classical pipeline — no ML deps
python scripts/run_simulation.py
python scripts/plot_simulation.py        # writes artifacts/simulation.png

# 2. Neural Hawkes pipeline — needs torch
pip install torch
python scripts/run_neural.py

# 3. Streamlit demo
streamlit run src/flowsight/viz/streamlit_app.py

# 4. FastAPI backend
pip install -r requirements-api.txt
uvicorn flowsight.api.server:app --reload --port 8080

# 5. React PWA frontend (in separate terminal, requires Node 18+)
cd frontend && npm install && npm run dev
```

Optional ML extras (PPO training, real road graphs, real Gemini calls):

```bash
pip install torch stable-baselines3 osmnx google-generativeai
```

---

## Project structure

```
src/flowsight/
  graph/         synthetic corridor · grid · OSM (via osmnx) · Delhi-Mumbai
  events/        canonical Event schema + disruption injector
  detection/     spatial Hawkes (baseline)
                 + Neural Hawkes Process (Mei & Eisner 2017)
                 + DCRNN spatio-temporal forecaster (Li et al. 2018)
  state/         HMM state estimator (Rabiner 1989) + threshold fallback
  routing/       risk + CVaR Dijkstra · Gym env for PPO
  rl/            PPO agent · CVaR-PPO callback (Hiraoka et al. 2019)
  simulation/    end-to-end world simulator (pluggable detector)
  metrics/       resilience triangle (Bruneau et al. 2003) + KPIs
  data/          GDELT news + Open-Meteo weather + multi-source fusion
  reasoning/     Gemini explainer (with deterministic template fallback)
  api/           FastAPI server (REST + WebSocket)
  viz/           Streamlit + pydeck demo

frontend/        React + TypeScript + Tailwind PWA
                 Vite-built · Leaflet maps · Recharts · service worker

infra/terraform/ GCP IaC: Cloud Run · Pub/Sub · Firestore ·
                 BigQuery · Secret Manager · Firebase Hosting

scripts/
  run_simulation.py   classical pipeline CLI
  run_neural.py       Neural-Hawkes-driven pipeline CLI
  plot_simulation.py  static PNG export of map + cascade + KPIs
  train_agent.py      PPO training loop

Dockerfile          backend image (Cloud Run)
cloudbuild.yaml     CI/CD: build → push → deploy
firebase.json       hosting + Cloud Run rewrites for the PWA
```

---

## Roadmap

### Phase 1 — algorithmic core (done)
- [x] Spatial Hawkes detector
- [x] HMM state estimation (with threshold fallback)
- [x] Risk-aware Dijkstra (CVaR-ready)
- [x] Synthetic corridor graph + disruption injector
- [x] End-to-end simulator + resilience metrics
- [x] Streamlit + pydeck interactive demo
- [x] Gym environment for PPO

### Phase 2 — research models, real data, cloud (done)
- [x] **Neural Hawkes Process** (Mei & Eisner 2017) — PyTorch CT-LSTM
- [x] **DCRNN** spatio-temporal forecaster — PyTorch diffusion-conv GRU
- [x] **CVaR-constrained PPO** — advantage-weighted bottom-tail shaping
- [x] **OSMnx Delhi-Mumbai corridor** — real-roads adapter with waypoint snapping
- [x] **GDELT** news adapter — disruption events from global news
- [x] **Open-Meteo** weather adapter — free, global, no API key
- [x] **Gemini explanation layer** — with deterministic template fallback
- [x] **FastAPI backend** — REST + WebSocket for live cascade streaming
- [x] **React PWA frontend** — Vite + TypeScript + Tailwind + Leaflet
- [x] **GCP deployment** — Dockerfile, Terraform, Cloud Build, Firebase Hosting

### Phase 3 — competition prep (next)
- [ ] Pitch deck + 2-minute demo video
- [ ] One-pager addressing each problem-statement phrase
- [ ] Real GDELT/weather feed integration test (needs internet)
- [ ] Train PPO with CVaR on a corpus of disruption scenarios
- [ ] Deploy backend to Cloud Run, frontend to Firebase Hosting
- [ ] Set up GCP billing alert at $1

---

## SDG alignment

- **SDG 9** Industry, Innovation & Infrastructure — resilient logistics
- **SDG 11** Sustainable Cities — less urban congestion
- **SDG 12** Responsible Consumption — less spoilage and wasted fuel
- **SDG 13** Climate Action — emissions-aware routing (CO₂ in cost function)
