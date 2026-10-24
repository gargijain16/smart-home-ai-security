# Architecture, problem statement and objectives

## Problem statement
Consumer smart homes (locks, cameras, lights, HVAC) talk MQTT through a broker. Weak or absent broker authentication allows brute force, topic enumeration, flooding and takeover (see the Smart Home poster's kill chain). Home users have no SOC; they need automated detection that is honest about its limits.

## Research objectives
1. Build a reproducible ML pipeline that classifies MQTT network-frame feature rows (normal, DoS, MitM, intrusion) from a public dataset.
2. Evaluate it without leakage and report per-class errors, false-positive/negative rates and latency, not accuracy alone.
3. Serve it behind a validated API and a dashboard that separates real inference from simulation.
4. Keep the design ready for a later VAPT module.

## Architecture
```mermaid
flowchart LR
  subgraph Browser
    UI[React + TS dashboard<br/>Vercel]
  end
  subgraph Backend[FastAPI backend - single worker]
    R[routes: system / events / predict]
    SIM[Simulator + rules]
    DB[(SQLite events)]
    ML[ModelService<br/>validate + predict]
  end
  ART[(models/*.joblib + metadata.json<br/>reports/*.json,png)]
  COL[Colab notebook<br/>train + export]
  DS[(MQTT_UAD CSVs<br/>CC BY 4.0)]
  UI -- HTTPS JSON --> R
  R --> SIM --> DB
  R --> ML --> ART
  DS --> COL --> ART
```
## Data flow
```mermaid
flowchart TD
  A[Simulator tick] --> B[rule label + severity] --> C[(events table)] --> D[Overview / Devices / Events pages]
  E[User CSV] --> F[schema validation vs model_metadata.json] -->|valid| G[sklearn Pipeline: imputer + tree model] --> H[class, vote share, evidence] --> I[Detection page]
  F -->|invalid| J[422 schema_mismatch with missing/unexpected columns]
  K[No model files] --> L[503 model_unavailable + how-to-enable, demo mode]
```
## Module boundaries (for future work)
`ml_service.py` (framework-free), `simulator.py`, `store.py`, `simulation.py`, thin routers, typed contracts in `schemas.py` ↔ `frontend/src/types/api.ts`. New detectors, ingestion or VAPT plug in as new services plus routers without touching existing pages.
