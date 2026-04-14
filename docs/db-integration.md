# 🔧 Database Integration Guide

## Military Vehicle Inventory Logistics Optimization and Prediction System

**For:** Database Engineer / Integration Specialist  
**Prerequisite:** MySQL 8.0+ running with the schema described in [database-schema.md](./database-schema.md)

---

## Overview

The ML pipeline reads **exclusively** from a MySQL database. It does not generate data. Your task is to:
1. Point all scripts at your real database
2. Verify the schema matches what the pipeline expects
3. Run a one-time label assignment
4. Execute the pipeline and confirm health scores are written

---

## Step 1 — Update Credentials in All 11 Files

Find the `DB_CONFIG` dict in each file below and replace with your real credentials:

```python
# BEFORE (dev placeholder):
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'military_vehicle_health',
    'user':     'root',
    'password': 'vedant@14',   # ← change this
    'charset':  'utf8mb4',
}

# AFTER:
DB_CONFIG = {
    'host':     'YOUR_HOST',
    'port':     3306,
    'database': 'YOUR_DB_NAME',
    'user':     'YOUR_USER',
    'password': 'YOUR_PASSWORD',
    'charset':  'utf8mb4',
}
```

| File | Path |
|---|---|
| `assign_vehicle_status.py` | `Army_ML_Pipeline_and_Files/` |
| `feature_engineering.py` | `Army_ML_Pipeline_and_Files/` |
| `train_health_model.py` | `Army_ML_Pipeline_and_Files/` |
| `temporal_model.py` | `Army_ML_Pipeline_and_Files/` |
| `run_inference.py` | `Army_ML_Pipeline_and_Files/` |
| `evaluate_ensemble.py` | `Army_ML_Pipeline_and_Files/` |
| `export_database.py` | `database_utils/` |
| `export_db_stats.py` | `database_utils/` |
| `verify_database.py` | `database_utils/` |
| `verify_labels.py` | `database_utils/` |
| `find_db_location.py` | `database_utils/` |

> ⚠️ **Do not commit real passwords to GitHub.** Use environment variables in production:  
> `'password': os.environ.get('DB_PASSWORD', '')`

---

## Step 2 — Schema Verification

Run the verification script:

```powershell
generate_data_env\Scripts\python.exe database_utils\verify_database.py
```

The pipeline queries these exact column names. If your real DB differs, use SQL `AS` aliases:

```sql
-- Example: remap your column names in feature_engineering.py queries
SELECT
    coolant_temp   AS engine_coolant_temp_celsius,
    volt           AS battery_voltage,
    load_pct       AS engine_load_percent,
    fuel_lph       AS fuel_consumption_lph,
    idle_mins      AS idle_time_minutes,
    speed_kph      AS current_speed_kmph,
    reading_time   AS timestamp
FROM your_telemetry_table
WHERE vehicle_id = %s
ORDER BY reading_time
```

### Critical Column Checklist

| Table | Must-Have Columns |
|---|---|
| `vehicles` | `vehicle_id`, `vehicle_type`, `acquisition_date` |
| `telemetry_data` | `vehicle_id`, `timestamp`, `engine_coolant_temp_celsius`, `battery_voltage`, `engine_rpm`, `engine_load_percent`, `fuel_consumption_lph`, `idle_time_minutes`, `current_speed_kmph` |
| `maintenance_records` | `vehicle_id`, `service_date`, `service_type` (`emergency`/`corrective`/`preventive`), `pre_service_health_score` |
| `diagnostic_codes` | `vehicle_id`, `severity` (`critical`/`major`/`minor`/`warning`), `detected_timestamp`, `resolved_timestamp`, `is_active` |
| `operational_logs` | `vehicle_id`, `mission_type`, `terrain_difficulty_score`, `harsh_braking_count`, `trip_distance_km` |
| `fuel_records` | `vehicle_id`, `refuel_date`, `fuel_efficiency_kmpl` |

### Create `health_scores` Table (if not exists)

```sql
CREATE TABLE IF NOT EXISTS health_scores (
    score_id                  INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id                VARCHAR(20) NOT NULL,
    assessment_date           DATE NOT NULL,
    overall_health_score      DECIMAL(5,2),
    health_status             ENUM('critical','poor','fair','good','excellent'),
    engine_health_score       DECIMAL(5,2),
    transmission_health_score DECIMAL(5,2),
    brake_system_score        DECIMAL(5,2),
    electrical_system_score   DECIMAL(5,2),
    predicted_days_to_service INT,
    predicted_service_date    DATE,
    confidence_level          DECIMAL(5,2),
    risk_category             ENUM('critical','high','medium','low'),
    recommended_action        TEXT,
    risk_evidence             TEXT,
    model_version             VARCHAR(50),
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vehicle_date    (vehicle_id, assessment_date)
);
```

---

## Step 3 — One-Time Label Assignment

Adds `vehicle_status` column to `maintenance_records` and assigns 5-class health labels:

```powershell
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\assign_vehicle_status.py
```

Expected output — perfectly balanced classes:
```
  Critical     xxxx  (20.00%)
  Poor         xxxx  (20.00%)
  Attention    xxxx  (20.00%)
  Good         xxxx  (20.00%)
  Excellent    xxxx  (20.00%)
```

---

## Step 4 — Run the Full Pipeline

```powershell
# Automatic (all steps):
.\run_pipeline.ps1

# Or step-by-step:
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\feature_engineering.py
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\train_health_model.py
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\temporal_model.py
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\optimize_ensemble.py
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\run_inference.py
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\evaluate_ensemble.py
```

---

## Step 5 — Verify Integration

```powershell
# Check feature matrix
generate_data_env\Scripts\python.exe -c "
import pandas as pd
df = pd.read_parquet('Army_ML_Pipeline_and_Files/vehicle_features.parquet')
print('Shape:', df.shape)          # Expected: (N_VEHICLES, ~59)
print('Null cols:', df.isnull().all().sum())   # Expected: 0
"

# Check health_scores table populated
generate_data_env\Scripts\python.exe database_utils\verify_database.py
```

---

## Step 6 — Delete Synthetic Artefacts

After confirmed success on real data:

```
DELETE:  Army_ML_Pipeline_and_Files/models/*.pkl
DELETE:  Army_ML_Pipeline_and_Files/models/*.npy
DELETE:  Army_ML_Pipeline_and_Files/models/*.zip
DELETE:  Army_ML_Pipeline_and_Files/vehicle_features.parquet
DELETE:  Army_ML_Pipeline_and_Files/reports/*.png  (regenerated from real training)
DELETE:  Army_ML_Pipeline_and_Files/reports/mlops/

KEEP:    All *.py scripts
KEEP:    models/*.json  (auto-overwritten by real training)
KEEP:    docs/, database_utils/, run_pipeline.ps1
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Unknown column 'engine_coolant_temp_celsius'` | Column name differs | Add SQL `AS` alias in query |
| `KeyError: 'vehicle_status'` | Step 3 not run | Run `assign_vehicle_status.py` first |
| Empty feature matrix / all-NaN | vehicle_id FK mismatch across tables | Verify FK consistency in DB |
| `SMOTE: n_samples < n_neighbors` | Class too small after labelling | Check quintile output from Step 3 |
| `UnicodeEncodeError` | Windows CP1252 console | Always use `-X utf8` flag |
| `health_scores` table missing | Not created in real DB | Run the CREATE TABLE SQL above |
| F1 drops below 0.70 | Real data distribution differs | Increase `N_TRIALS` to 100 in `train_health_model.py` |
| Connection refused / 2003 | MySQL not running or wrong host | Verify DB_CONFIG host/port |

---

> 🔙 [Back to README](../README.md) | 📖 [Database Schema](./database-schema.md)
