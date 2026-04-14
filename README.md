<div align="center">

# 🪖 Military Vehicle Inventory Logistics Optimization and Prediction System

### Predictive Fleet Health Monitoring · Ensemble ML · Real-Time Risk Assessment

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-Champion-FF6600?style=for-the-badge)](https://xgboost.readthedocs.io)
[![LightGBM](https://img.shields.io/badge/LightGBM-Ensemble-00B140?style=for-the-badge)](https://lightgbm.readthedocs.io)
[![TabNet](https://img.shields.io/badge/TabNet-Attention--DL-8B5CF6?style=for-the-badge)](https://github.com/dreamquark-ai/tabnet)
[![PyTorch](https://img.shields.io/badge/PyTorch-BiLSTM-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![SHAP](https://img.shields.io/badge/SHAP-Explainability-FF4500?style=for-the-badge)](https://shap.readthedocs.io)
[![Optuna](https://img.shields.io/badge/Optuna-Bayesian--HPO-1B78BD?style=for-the-badge)](https://optuna.org)

**A production-grade ML pipeline that classifies every vehicle in a 5,000-strong Indian Army fleet into one of five health states — and writes actionable maintenance recommendations directly to the operational database.**

</div>

<div align="center">

| Metric | Value |
|---|---|
| 🎯 **Champion Macro F1** | **91.06%** |
| 📈 **Macro AUC-ROC** | **> 0.97** |
| 🚗 **Fleet Coverage** | **5,000 vehicles · assessed daily** |
| 🧠 **Ensemble Strategy** | **XGB 93.5% · TabNet 6.4% · LGBM 0.1%** |
| 📊 **Feature Dimensions** | **~59 engineered + 14 neural features** |
| 🗄️ **Database Tables** | **9 tables · ~1.89 million records** |

</div>

---

## 📋 Index

| # | Section | Description |
|---|---|---|
| 1 | [The Problem](#-the-problem) | Why this system exists |
| 2 | [System Architecture](#-system-architecture) | End-to-end pipeline flow |
| 3 | [Ensemble Results](#-ensemble-results) | Performance benchmarks |
| 4 | [Quick Start](#-quick-start) | Get running in 4 steps |
| 5 | [Project Structure](#-project-structure) | Directory layout |
| 6 | [Tech Stack](#-tech-stack) | Technologies used |
| 7 | [Documentation](#-documentation) | Deep-dive doc links |

---

## 🚨 The Problem

Military fleets rely on **fixed, calendar-based maintenance schedules** — a vehicle gets serviced every *N* kilometres or every *N* months, regardless of its actual condition. This fails in both directions:

| Challenge | Status Quo | This System |
|---|---|---|
| **Health Assessment** | Fixed-interval scheduling | Per-vehicle ML prediction daily |
| **Failure Detection** | Discovered on breakdown | Predicted days/weeks in advance |
| **DTC Fault Analysis** | Logged but manually reviewed | Algorithmically scored with temporal decay |
| **Sensor Degradation** | Noticed after threshold breach | Bi-LSTM detects gradual trends over 50 readings |
| **Maintenance Priority** | Calendar-driven queue | Risk-ranked by confidence-adjusted health score |
| **Decision Rationale** | None | Full SHAP explainability + Z-score risk evidence |
| **Class Imbalance** | Data skewed toward healthy vehicles | SMOTE per-fold balances training without leakage |
| **Model Confidence** | Binary pass/fail | MC Dropout uncertainty estimate per vehicle |

> 📖 **[Full Problem Statement & Design Decisions →](docs/problem-statement.md)**

---

## ⚙️ System Architecture

```
    ┌──────────────────────────────────────────────────────────────┐
    │  MySQL Database  (real Army vehicle telemetry)               │
    │  vehicles · telemetry_data · maintenance_records             │
    │  diagnostic_codes · operational_logs · fuel_records          │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  STAGE 1 — assign_vehicle_status.py                          │
    │  Temporal DTC decay scoring → quintile bucketing             │
    │  → Adds vehicle_status column  (5 balanced classes)          │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  STAGE 2 — feature_engineering.py                            │
    │  SQL aggregation → 45 tabular features                       │
    │  Neural autoencoder → 10 latent dims                         │
    │  MC Dropout → uncertainty estimate                           │
    │  → vehicle_features.parquet  (5,000 × ~59)                   │
    └─────────────┬────────────────────────────┬───────────────────┘
                  │                            │
    ┌─────────────▼──────────────┐  ┌──────────▼───────────────────┐
    │  STAGE 3 — Training        │  │  STAGE 4 — temporal_model.py  │
    │  XGBoost  (Optuna 50T)     │  │  Bi-LSTM · seq_len=50         │
    │  LightGBM (Optuna 50T)     │  │  8 sensor channels            │
    │  TabNet   (Optuna 50T)     │  │  → temporal_probs.npy         │
    │  5-fold OOF + SMOTE        │  │    (15% weight in ensemble)   │
    │  → OOF arrays (5000 × 5)  │  └──────────┬────────────────────┘
    └─────────────┬──────────────┘             │
                  └──────────┬─────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────────────┐
    │  STAGE 5 — optimize_ensemble.py                              │
    │  Temperature calibration per model                           │
    │  Stacked meta-learner (LogReg)                               │
    │  Bayesian weight search → 4-strategy tournament              │
    │  → Champion: Weighted Bayesian Blend  (F1 = 91.06%)          │
    │  → ensemble_config.json + ensemble_weights.json              │
    └────────────────────────┬─────────────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────────────┐
    │  STAGE 6 — run_inference.py                                  │
    │  Champion ensemble + temporal fusion (85/15 split)           │
    │  Data-anchored health scoring (0–100)                        │
    │  Z-score risk evidence per vehicle                           │
    │  → health_scores table  (5,000 rows written to DB)           │
    └────────────────────────┬─────────────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────────────┐
    │  STAGE 7 — evaluate_ensemble.py                              │
    │  Accuracy · Macro F1 · Macro AUC-ROC                         │
    │  5-class ROC curves · Classification report                  │
    │  → reports/ (metrics, confusion matrix, ROC plots)           │
    └──────────────────────────────────────────────────────────────┘
```

> 📖 **[Full ML Pipeline Deep-Dive →](docs/ml-pipeline.md)**

---

## 📊 Ensemble Results

### Tournament — Champion Selection

| Rank | Strategy | Macro F1 |
|---|---|---|
| 🥇 **Champion** | **Weighted Bayesian Blend** | **91.06%** |
| 🥈 | Non-linear Stacking (Random Forest) | 90.97% |
| 🥉 | Simple Average | 90.56% |
| 4th | Linear Stacking (Logistic Regression) | 90.19% |

### Champion Ensemble Composition

| Model | Architecture | OOF Weight |
|---|---|---|
| **XGBoost** | 811 trees · depth 6 · Bayesian HPO (50 trials) | **93.53%** |
| **TabNet** | Attention-based DL · n_d=32 · n_steps=5 | **6.37%** |
| **LightGBM** | 646 trees · 197 leaves · Bayesian HPO | **0.11%** |
| **Bi-LSTM** | 2-layer bidirectional · hidden=64 | **15% temporal fusion** |

### Per-Class Performance (AUC-ROC)

| Health Class | AUC-ROC |
|---|---|
| Critical | > 0.98 |
| Poor | > 0.97 |
| Attention | > 0.96 |
| Good | > 0.97 |
| Excellent | > 0.98 |

---

## 🚀 Quick Start

**Prerequisites:** Python 3.10+ · MySQL 8.0+ · Windows PowerShell

### 1 — Clone & Setup Environment
```powershell
git clone https://github.com/YOUR_USERNAME/military-vehicle-inventory-logistics-optimization.git
cd military-vehicle-inventory-logistics-optimization

python -m venv generate_data_env
generate_data_env\Scripts\Activate.ps1
pip install -r Army_ML_Pipeline_and_Files\requirements.txt
```

### 2 — Configure Database
Update `DB_CONFIG` in all pipeline scripts with your MySQL credentials.  
➔ See [Database Integration Guide](docs/db-integration.md) for the complete list of files.

### 3 — One-Time Label Setup
```powershell
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\assign_vehicle_status.py
```

### 4 — Run the Full Pipeline
```powershell
.\run_pipeline.ps1
```

> 📖 **[Detailed Installation Guide →](docs/installation.md)**

---

## 📁 Project Structure

```
military-vehicle-inventory-logistics-optimization/
│
├── run_pipeline.ps1                          # 🎮 PowerShell orchestrator — runs all stages
│
├── Army_ML_Pipeline_and_Files/
│   ├── assign_vehicle_status.py             # Stage 1 — 5-class label assignment
│   ├── feature_engineering.py               # Stage 2 — SQL → .parquet feature matrix
│   ├── train_health_model.py                # Stage 3 — XGBoost + LightGBM + TabNet training
│   ├── temporal_model.py                    # Stage 4 — Bi-LSTM temporal channel
│   ├── optimize_ensemble.py                 # Stage 5 — Temperature calibration + tournament
│   ├── run_inference.py                     # Stage 6 — Champion inference → DB write
│   ├── evaluate_ensemble.py                 # Stage 7 — Metrics + ROC curves
│   ├── mlops_tracker.py                     # MLOps — per-run JSON logging
│   ├── extracted_params.json                # Locked Optuna best hyperparameters
│   ├── requirements.txt                     # All Python dependencies
│   │
│   ├── models/                              # ← Regenerated after training (gitignored)
│   │   ├── ensemble_config.json             # Champion strategy configuration
│   │   ├── ensemble_weights.json            # Bayesian blend weights
│   │   ├── feature_names.json               # Feature column order
│   │   └── temperature_scalars.json         # Probability calibration temperatures
│   │
│   └── reports/                             # ← Regenerated after training
│       ├── ensemble_evaluation_detailed.txt
│       ├── ensemble_roc_curve.png
│       ├── confusion_matrix.png
│       ├── shap_global.png
│       ├── shap_per_class_critical.png
│       ├── shap_importance.csv
│       └── mlops/                           # Per-run JSON audit logs
│
├── database_utils/
│   ├── verify_database.py                   # Schema + row count verification
│   ├── verify_labels.py                     # Label distribution check
│   ├── export_database.py                   # Full DB → SQL file export
│   ├── export_db_stats.py                   # Table stats → JSON
│   └── find_db_location.py                  # MySQL data directory lookup
│
├── docs/                                    # 📖 Full documentation suite
│   ├── problem-statement.md                 # Why + design decisions
│   ├── ml-pipeline.md                       # Stage-by-stage pipeline reference
│   ├── database-schema.md                   # All 9 tables, columns, types
│   ├── db-integration.md                    # DB engineer integration guide
│   ├── installation.md                      # Setup + dependency guide
│   └── quick-reference.md                   # Commands cheat sheet
│
├── exports/                                 # ← SQL exports (gitignored, 275 MB)
├── tmp/                                     # ← Temp files (gitignored)
├── .gitignore
├── README.md
└── Army_ML_Pipeline_Documentation.pdf       # 21-page full technical reference
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Primary Classifier** | XGBoost 2.0+ | Gradient-boosted trees, champion base model |
| **Secondary Classifier** | LightGBM 4.0+ | Leaf-wise boosting, speed-optimised |
| **Neural Tabular** | pytorch-tabnet | Attention-based sequential tabular DL |
| **Temporal Channel** | PyTorch BiLSTM | Sequential degradation pattern detection |
| **Neural Enhancement** | PyTorch Autoencoder | Latent health embeddings (10 dims) |
| **Uncertainty** | MC Dropout | Epistemic uncertainty quantification |
| **HPO** | Optuna TPE + Hyperband | Bayesian hyperparameter search (50 trials each) |
| **Class Balancing** | imbalanced-learn SMOTE | Per-fold synthetic minority oversampling |
| **Explainability** | SHAP TreeExplainer | Global + per-class feature attributions |
| **Calibration** | Temperature Scaling | Probability calibration before ensemble stacking |
| **Database** | MySQL 8.0 + mysql-connector-python | 9-table fleet data warehouse |
| **Data Pipeline** | Pandas + PyArrow | SQL → parquet feature matrix |
| **Visualisation** | Matplotlib + Seaborn | ROC curves, confusion matrix, SHAP plots |

---

## 📖 Documentation

| Document | Contents |
|---|---|
| [**Problem Statement**](docs/problem-statement.md) | Why this system exists, the operational gap it fills, and all key design decisions explained |
| [**ML Pipeline**](docs/ml-pipeline.md) | Stage-by-stage deep dive: feature groups, model configurations, ensemble tournament, inference formula |
| [**Database Schema**](docs/database-schema.md) | All 9 tables with column types, indexes, DTC code catalogue, and SQL verification queries |
| [**DB Integration Guide**](docs/db-integration.md) | **For the DB engineer** — credentials, schema alignment, label assignment, pipeline execution, cleanup |
| [**Installation**](docs/installation.md) | Prerequisites, virtualenv, dependency table, MySQL setup, common issues |
| [**Quick Reference**](docs/quick-reference.md) | All pipeline commands, utility scripts, output file map, and health class definitions |
| [**Full Technical PDF**](Army_ML_Pipeline_Documentation.pdf) | 21-page comprehensive reference for every file, function, and design decision |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Update `DB_CONFIG` in changed files (do **not** commit real passwords)
4. Run the pipeline locally and verify outputs
5. Submit a pull request with a clear description of what changed and why

---

<div align="center">

**Military Vehicle Inventory Logistics Optimization and Prediction System**

*Built for the Indian Army — Predictive Maintenance · Fleet Intelligence · Operational Readiness*

</div>
