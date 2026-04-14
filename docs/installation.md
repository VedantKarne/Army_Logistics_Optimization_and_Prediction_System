# 🛠️ Installation & Setup

## Military Vehicle Inventory Logistics Optimization and Prediction System

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Download from python.org |
| MySQL Server | 8.0+ | Community edition is sufficient |
| Git | Any | For cloning the repo |
| RAM | 8 GB min | 16 GB recommended for TabNet training |
| Storage | 5 GB min | For models, parquet, reports |
| OS | Windows 10/11 | PowerShell 5.1+ required |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/military-vehicle-inventory-logistics-optimization.git
cd military-vehicle-inventory-logistics-optimization
```

---

## Step 2 — Create Virtual Environment

```powershell
# Create the virtual environment (named generate_data_env to match scripts)
python -m venv generate_data_env

# Activate it
generate_data_env\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Step 3 — Install Dependencies

```powershell
pip install -r Army_ML_Pipeline_and_Files\requirements.txt
```

Full dependency list:

| Package | Version | Purpose |
|---|---|---|
| `xgboost` | >=2.0 | Gradient boosted trees |
| `lightgbm` | >=4.0 | Fast gradient boosting |
| `pytorch-tabnet` | >=4.1 | Attention-based tabular DL |
| `torch` | >=2.0 | PyTorch (TabNet + BiLSTM) |
| `optuna` | >=3.5 | Bayesian hyperparameter optimisation |
| `imbalanced-learn` | >=0.12 | SMOTE for class balancing |
| `shap` | >=0.44 | Model explainability |
| `scikit-learn` | >=1.4 | ML utilities, preprocessing |
| `pandas` | >=2.1 | Data manipulation |
| `numpy` | >=1.26 | Numerical computing |
| `pyarrow` | >=15.0 | Parquet I/O |
| `mysql-connector-python` | >=8.3 | MySQL database driver |
| `matplotlib` | >=3.8 | Plotting ROC curves, SHAP |
| `seaborn` | >=0.13 | Statistical visualisation |

---

## Step 4 — Configure MySQL

Ensure your MySQL server is running and the database exists:

```sql
-- In MySQL client:
CREATE DATABASE IF NOT EXISTS military_vehicle_health
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Update the `DB_CONFIG` block in all pipeline scripts with your credentials.  
See the [Database Integration Guide](./db-integration.md) for the full list of files to update.

---

## Step 5 — Connect to Your Database

If you are connecting to a **real Army vehicle telemetry database** (not synthetic data):

1. Update credentials across all 11 files (see [db-integration.md](./db-integration.md))
2. Verify schema alignment against [database-schema.md](./database-schema.md)
3. Run `assign_vehicle_status.py` once to add health labels
4. Execute the pipeline

---

## Step 6 — Run the Pipeline

```powershell
# From the project root:
.\run_pipeline.ps1
```

Or run each step individually with detailed logging — see [quick-reference.md](./quick-reference.md).

---

## Common Setup Issues

| Issue | Fix |
|---|---|
| `execution policy` error on virtualenv activate | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `pip install` fails for `torch` | Install PyTorch separately: [pytorch.org](https://pytorch.org/get-started/locally/) |
| `mysql-connector` authentication error | Ensure MySQL native password auth: `ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';` |
| `ModuleNotFoundError` even after install | Ensure venv is activated: check `(generate_data_env)` prefix in terminal |
| `UnicodeEncodeError` when running scripts | Always use `-X utf8` flag (already embedded in `run_pipeline.ps1`) |
| TabNet training is very slow | Normal on CPU — GPU training: install CUDA-compatible PyTorch |

---

> 🔙 [Back to README](../README.md) | ⚡ [Quick Reference](./quick-reference.md)
