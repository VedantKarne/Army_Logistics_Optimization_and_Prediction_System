<div align="center">

# 🚑 Sentinel — Ignisia

### Golden-Hour Emergency Triage & Constraint-Based Hospital Routing System

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-Ensemble-FF6600?style=for-the-badge)](https://xgboost.readthedocs.io)
[![MapLibre](https://img.shields.io/badge/MapLibre--GL-3D--Map-8B5CF6?style=for-the-badge)](https://maplibre.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**A real-time AI dispatch system that predicts what a patient needs before arrival and routes the ambulance to the nearest hospital that is actually capable of treating them — right now.**

</div>

<div align="center">

![Sentinel AI — Ignisia Platform](sentinel.png)

</div>

---

## 📋 Index

| # | Section | Description |
|---|---------|-------------|
| 1 | [The Problem](#-the-problem) | Why this exists |
| 2 | [System Architecture](#-system-architecture) | High-level flow |
| 3 | [Quick Start](#-quick-start) | Get running in 3 steps |
| 4 | [Project Structure](#-project-structure) | Directory layout |
| 5 | [Tech Stack](#-tech-stack) | Technologies used |
| 6 | [Documentation](#-documentation) | Deep-dive doc links |

---

## 🚨 The Problem

During medical emergencies, ambulances are dispatched to the **nearest hospital** — only to arrive and find the required ventilator is occupied, the specialist is off-duty, or the ICU is at capacity. This reactive routing wastes the most critical minutes of a patient's **golden hour.**

The problem compounds during mass casualty events — a single accident floods one trauma center while capable facilities nearby sit underutilized.

| Challenge | Status Quo | Sentinel AI |
|-----------|-----------|-------------|
| **Routing Logic** | Geography-only | Capability-matched + constraint-optimised |
| **Equipment Availability** | Discovered on arrival | Pre-departure AI prediction |
| **Specialist On-Duty** | Unknown until arrival | Real-time constraint matching |
| **Mass Casualty** | Floods single center | Load-balanced across regional grid |
| **Decision Rationale** | None | Full AI explainability panel |
| **Bed Reservation** | Manual phone call | Automatic 15-min soft TTL hold |

> 📖 **[Full Problem Statement & Solution Context →](docs/problem-statement.md)**

---

## ⚙️ System Architecture

```
          ┌──────────────────────────────────────────────────────┐
          │  EMT FIELD INTERFACE  (/emt)                         │
          │  Vitals + Symptoms → POST /triage                    │
          └─────────────────────┬────────────────────────────────┘
                                │
          ┌─────────────────────▼────────────────────────────────┐
          │  ML SERVICE  (FastAPI · localhost:8000)               │
          │  1. Preprocess  →  KNN Impute + StandardScale        │
          │  2. Diagnose    →  XGBoost + LightGBM soft-vote      │
          │  3. Score       →  5-index severity formula          │
          │  4. Plan        →  Specialists + Equipment           │
          │  5. Route       →  Constraint-based hospital ranking  │
          │  6. Reserve     →  15-min soft bed TTL hold          │
          └─────────────────────┬────────────────────────────────┘
                                │  ranked hospitals + triage result
          ┌─────────────────────▼────────────────────────────────┐
          │  WEBSOCKET BRIDGE  (Node.js · localhost:8080)         │
          │  POST /dispatch-route  →  WS push to all clients     │
          └─────────────────────┬────────────────────────────────┘
                                │
          ┌─────────────────────▼────────────────────────────────┐
          │  COMMAND DASHBOARD  (/dashboard)                      │
          │  3D MapLibre GL  +  3D Ambulance (Three.js/WebGL)    │
          │  OSRM real-road routing  +  Decision Intel panel     │
          └──────────────────────────────────────────────────────┘
```

> 📖 **[Full ML Pipeline & Architecture →](docs/ml-pipeline.md)**

---

## 🚀 Quick Start

**Prerequisites:** Python 3.10+ · Node.js 18+ · npm 9+

### 1 — ML Service (AI Triage + Routing API)
```bash
cd ML_Service
pip install fastapi uvicorn xgboost lightgbm scikit-learn pandas numpy
python main.py
# → http://localhost:8000
```

### 2 — Backend (WebSocket Bridge)
```bash
cd Backend
npm install && npm run dev
# → ws://localhost:8080
```

### 3 — Frontend (React Dashboard)
```bash
cd Frontend
npm install && npm run dev
# → http://localhost:5173
```

> 📖 **[Detailed Installation & Configuration Guide →](docs/installation.md)**

---

## 📁 Project Structure

```
Eternum_Latest/
│
├── ML_Service/                     # 🧠 Python FastAPI — AI Triage + Routing
│   ├── main.py                     # Entry point — /triage endpoint
│   ├── models/                     # Pre-trained model files (.json, .pkl)
│   ├── src/
│   │   ├── inference.py            # TriagePredictor — full pipeline class
│   │   ├── feature_engineering.py  # Preprocessor (KNNImputer + StandardScaler)
│   │   ├── diagnosis_mappings.py   # Emergency configs, severity tiers, care plans
│   │   └── train_models.py         # XGBoost + LightGBM training script
│   └── hospital/
│       ├── hospitals_db.py         # 18 Pune hospitals, 3 tiers, live-simulated beds
│       └── router.py               # Constraint-based routing + soft reservation engine
│
├── Backend/                        # 🔌 Node.js — WebSocket Bridge
│   └── src/server.js               # Express + WS → /dispatch-route relay
│
├── Frontend/                       # 🖥️ React 19 + Vite + TailwindCSS
│   ├── src/
│   │   ├── App.jsx                 # React Router — 7 page routes
│   │   └── components/
│   │       ├── Map3D.jsx           # MapLibre GL + Three.js 3D ambulance layer
│   │       └── Userrouting.jsx     # OSRM routing hook + animation engine
│   └── pages/
│       ├── Dashboard/              # Dispatch command center
│       ├── EmtInterface/           # Patient vitals intake form
│       ├── MassCasualtyMode/       # Multi-patient MCI control room
│       ├── HospitalAdmin/          # Hospital bed management
│       ├── Landing/                # Product landing page
│       ├── LoginSelection/         # Role selector
│       └── ComingSoon/             # Feature placeholder
│
└── docs/                           # 📖 Detailed Documentation
    ├── problem-statement.md
    ├── ml-pipeline.md
    ├── routing-engine.md
    ├── api-reference.md
    ├── dashboard-guide.md
    └── installation.md
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **ML Models** | XGBoost + LightGBM | 8-class emergency diagnosis, soft-vote ensemble |
| **Preprocessing** | scikit-learn (KNNImputer, StandardScaler) | Missing vitals imputation + normalization |
| **API** | FastAPI + Uvicorn | `/triage` inference endpoint |
| **WS Bridge** | Node.js + `ws` + Express | HTTP → WebSocket relay for live map |
| **Frontend** | React 19 + Vite 8 | SPA dashboard framework |
| **Styling** | TailwindCSS 3.4 (Material Design 3) | Design system tokens |
| **3D Map** | MapLibre GL 5 + Three.js 0.183 | Pitched 3D map + ambulance WebGL layer |
| **Routing** | OSRM Public API | Real-road geometry for ambulance animation |
| **Icons** | Google Material Symbols | UI iconography |

---

## 📖 Documentation

| Document | Contents |
|----------|----------|
| [**Problem Statement**](docs/problem-statement.md) | Full problem context, solution rationale, expected outcomes |
| [**ML Pipeline**](docs/ml-pipeline.md) | Feature engineering, ensemble architecture, severity scoring, diagnosis mappings |
| [**Routing Engine**](docs/routing-engine.md) | Hospital database, scoring weights, hard filters, soft reservation system |
| [**API Reference**](docs/api-reference.md) | Full endpoint docs with request/response schemas and examples |
| [**Dashboard Guide**](docs/dashboard-guide.md) | All 7 pages — layout, components, interactions, data flow |
| [**Installation**](docs/installation.md) | Detailed setup, environment config, model training, troubleshooting |

---

<div align="center">

**Built for HC03 — Golden-Hour Emergency Triage & Hospital Routing**

*Sentinel AI · Ignisia Emergency Response Platform*

</div>
