# Military Vehicle Inventory Logistics Optimization and Prediction System

> **A full end-to-end Machine Learning pipeline for predictive health monitoring, logistics optimization, and operational readiness prediction of a 5,000-vehicle Indian Army fleet.**  
> Classifies each vehicle into one of 5 health statuses using an ensemble of XGBoost, LightGBM, TabNet, and a Bi-LSTM temporal channel — enabling proactive maintenance scheduling, spare parts inventory optimization, and mission-readiness forecasting.

---

## Repository Overview

This repository contains the **full ML pipeline source code** for the Military Vehicle Inventory Logistics Optimization and Prediction System. It is designed to connect to a **real (or pre-existing) Army vehicle database** — no synthetic data generation is required.

> **Note on `data_generation/`:** This folder (used during development to generate a synthetic MySQL database for testing) is **not included** in this repository. The pipeline starts from Step 3 onwards — it assumes a database already exists and is populated with real telemetry, maintenance, and operational data matching the required schema.

This repository does **not** include:
- `data_generation/` — synthetic data scripts (development-only, excluded by design)
- Pre-trained model `.pkl` / `.npy` files (you train them by running the pipeline)
- The 275 MB SQL export (use `database_utils/export_database.py` after running the pipeline)
- Virtual environment (`generate_data_env/`) — install dependencies yourself via `requirements.txt`

---

## Pipeline Architecture

```
run_pipeline.ps1  (Orchestrator)
      │
      │   ── Assumes real DB already has: vehicles, telemetry_data,
      │      maintenance_records, diagnostic_codes, operational_logs,
      │      fuel_records tables populated with real Army data ──
      │
      ├──[1. Army_ML_Pipeline_and_Files/assign_vehicle_status.py] → Assigns 5-class labels (run once on real DB)
      ├── 2. Army_ML_Pipeline_and_Files/feature_engineering.py   → vehicle_features.parquet
      ├── 3. Army_ML_Pipeline_and_Files/train_health_model.py    → XGBoost + LightGBM + TabNet
      ├──[4. Army_ML_Pipeline_and_Files/temporal_model.py]       → Bi-LSTM channel (run manually)
      ├── 5. Army_ML_Pipeline_and_Files/optimize_ensemble.py     → Champion ensemble selection
      ├── 6. Army_ML_Pipeline_and_Files/run_inference.py         → health_scores table populated
      └── 7. Army_ML_Pipeline_and_Files/evaluate_ensemble.py     → Final metrics + ROC curves
```

**Champion Ensemble Results:**
| Metric | Value |
|--------|-------|
| Strategy | Weighted Bayesian Blend (XGB 93.5% + TabNet 6.4% + LGBM 0.1%) |
| Macro F1 | **91.06%** |
| Macro AUC-ROC | **>0.97** |
| Fleet Coverage | 5,000 vehicles, 5 health classes |

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| MySQL Server | 8.0+ |
| Operating System | Windows (PowerShell for orchestrator) |
| RAM | 8 GB minimum (16 GB recommended for training) |
| GPU | Optional (CUDA-compatible for faster TabNet training) |

---

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/military-vehicle-health-ml.git
cd military-vehicle-health-ml
```

### 2. Create & Activate Virtual Environment
```powershell
python -m venv generate_data_env
generate_data_env\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r Army_ML_Pipeline_and_Files/requirements.txt
```

### 4. Configure Your Database Credentials

Update `DB_CONFIG` in **each** of these files with your MySQL credentials:

| File | Location |
|---|---|
| `generate_data.py` | `data_generation/` |
| `generate_synthetic_labels.py` | `data_generation/` |
| `assign_vehicle_status.py` | `Army_ML_Pipeline_and_Files/` |
| `feature_engineering.py` | `Army_ML_Pipeline_and_Files/` |
| `run_inference.py` | `Army_ML_Pipeline_and_Files/` |
| `temporal_model.py` | `Army_ML_Pipeline_and_Files/` |
| All `database_utils/*.py` | `database_utils/` |

```python
# Change this in each file:
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'military_vehicle_health',
    'user':     'root',
    'password': 'YOUR_PASSWORD_HERE',   # <-- Change this
    'charset':  'utf8mb4',
}
```

> ⚠️ **Never commit real credentials to GitHub.** The current scripts have placeholder credentials — replace them with yours before running.

### 5. Run the Full Pipeline
```powershell
# From the project root:
.\run_pipeline.ps1
```

This runs all 6 main steps sequentially and logs output to `.log` files.

### 6. Run Manual Steps (Between Pipeline Runs)

These two scripts must be run **manually** (not included in `run_pipeline.ps1`):

```powershell
# After generate_synthetic_labels.py — assigns 5-class vehicle_status labels:
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\assign_vehicle_status.py

# Optional — generates Bi-LSTM temporal probability channel (improves ensemble by 15%):
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\temporal_model.py
```

---

## Repository Structure

```
Army_ML_3_02_26/
│
├── run_pipeline.ps1                         # PowerShell orchestrator
│
├── data_generation/
│   ├── generate_data.py                     # Step 1: DB schema + synthetic data
│   ├── generate_synthetic_labels.py         # Step 2: Maintenance + DTC records
│   └── requirements_generate_data.txt
│
├── Army_ML_Pipeline_and_Files/
│   ├── assign_vehicle_status.py             # Step 3: 5-class label assignment
│   ├── feature_engineering.py              # Step 4: Feature matrix → .parquet
│   ├── train_health_model.py               # Step 5: XGBoost + LightGBM + TabNet
│   ├── temporal_model.py                   # Step 6: Bi-LSTM temporal channel
│   ├── optimize_ensemble.py                # Step 7: Ensemble tournament
│   ├── run_inference.py                    # Step 8: Inference → health_scores
│   ├── evaluate_ensemble.py                # Step 9: Final metrics
│   ├── mlops_tracker.py                    # MLOps JSON logger
│   ├── extracted_params.json               # Best Optuna hyperparameters
│   ├── requirements.txt                    # All Python dependencies
│   │
│   ├── models/                             # ← Generated after training (gitignored)
│   │   ├── ensemble_config.json            # Champion strategy config (committed)
│   │   ├── ensemble_weights.json           # Bayesian weights (committed)
│   │   ├── feature_names.json              # Feature column order (committed)
│   │   ├── temperature_scalars.json        # Calibration temps (committed)
│   │   └── tabpfn_config.json
│   │
│   └── reports/                            # ← Generated after training
│       ├── classification_report.txt
│       ├── confusion_matrix.png
│       ├── shap_global.png
│       └── ...
│
├── database_utils/
│   ├── export_database.py                  # Exports DB to SQL file
│   ├── export_db_stats.py                  # Saves table row counts to JSON
│   ├── verify_database.py                  # Schema + data verification
│   ├── verify_labels.py                    # Label distribution verification
│   └── find_db_location.py                 # MySQL data directory lookup
│
├── docs/
│   ├── README_DATABASE.md                  # DB schema documentation
│   ├── IMPORT_INSTRUCTIONS.md              # How to import the SQL export
│   ├── SHARING_INSTRUCTIONS.md
│   ├── QUICK_REFERENCE.md                  # One-page command cheat sheet
│   ├── VIRTUALENV_SETUP.md
│   └── ml_engineer_contributions.md
│
├── exports/                                # ← SQL exports land here (gitignored)
├── tmp/                                    # ← Empty temp directory (gitignored)
│
└── Army_ML_Pipeline_Documentation.pdf      # Full technical documentation (44 KB)
```

---

## Integration with Real Database

When connecting to a **real vehicle telemetry database** instead of synthetic data:

1. **Skip Steps 1 & 2** — `generate_data.py` and `generate_synthetic_labels.py` are only for synthetic data generation.
2. **Start from Step 3** — `assign_vehicle_status.py` — if your real DB already has maintenance records and DTC codes.
3. **Update DB_CONFIG** — point all scripts to your production MySQL host/database.
4. **Run the ML pipeline** — Steps 4–9 are data-agnostic and will work with any properly structured `military_vehicle_health` schema.

The **database schema** (9 tables) is defined in `generate_data.py → create_database_schema()`. Your real DB must match this schema for the pipeline to work without modification.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Update your `DB_CONFIG` credentials (do NOT commit real passwords)
4. Run the pipeline and verify your changes
5. Submit a pull request with a description of your changes

---

## Documentation

| Document | Description |
|---|---|
| 📄 [Army_ML_Pipeline_Documentation.pdf](./Army_ML_Pipeline_Documentation.pdf) | Full 21-page technical reference for every file, function, and design decision |
| 🔧 [DATABASE_INTEGRATION_GUIDE.md](./docs/DATABASE_INTEGRATION_GUIDE.md) | **Start here if you are the DB integration engineer** — step-by-step guide to connect the pipeline to a real database |
| 🗄️ [README_DATABASE.md](./docs/README_DATABASE.md) | Database schema definitions and table field descriptions |
| ⚡ [QUICK_REFERENCE.md](./docs/QUICK_REFERENCE.md) | One-page command cheat sheet |
| 📥 [IMPORT_INSTRUCTIONS.md](./docs/IMPORT_INSTRUCTIONS.md) | How to import the SQL export into a fresh MySQL instance |
| 🐍 [VIRTUALENV_SETUP.md](./docs/VIRTUALENV_SETUP.md) | Virtual environment setup on Windows |

---

## License

This project is intended for internal Indian Army research and development. Unauthorized distribution is restricted.
