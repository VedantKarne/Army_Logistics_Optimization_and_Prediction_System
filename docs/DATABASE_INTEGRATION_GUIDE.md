# Database Integration Guide
## Military Vehicle Inventory Logistics Optimization and Prediction System

**For:** Database Engineer / Integration Specialist  
**Purpose:** Step-by-step instructions to connect the ML pipeline to a real Army vehicle database  
**Estimated Time:** 2–4 hours (depending on schema differences)

---

## Overview

This ML pipeline was developed and validated on a synthetic database that mirrors a real Army
vehicle telemetry system. Your job is to point all ML scripts at the **real production database**
and verify the schema matches what the pipeline expects.

The pipeline does **not generate any data** — it only reads from the database via SQL queries.
Once your DB credentials and schema are confirmed, the pipeline runs identically on real data.

---

## Step 1 — Update Database Credentials in All ML Files

Change the `DB_CONFIG` block in **every file listed below**.  
Find the block that looks like this and replace with your real credentials:

```python
# BEFORE (synthetic/dev credentials — change these):
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'military_vehicle_health',
    'user':     'root',
    'password': 'vedant@14',        # <-- CHANGE THIS
    'charset':  'utf8mb4',
}
```

```python
# AFTER (your real database credentials):
DB_CONFIG = {
    'host':     'YOUR_DB_HOST',     # e.g. '192.168.1.100' or 'db.army.mil.in'
    'port':     3306,               # change if your MySQL runs on a different port
    'database': 'YOUR_DB_NAME',     # your actual database name
    'user':     'YOUR_DB_USER',
    'password': 'YOUR_DB_PASSWORD',
    'charset':  'utf8mb4',
}
```

### Files That Require This Change

| File | Path |
|------|------|
| `assign_vehicle_status.py` | `Army_ML_Pipeline_and_Files/` |
| `feature_engineering.py`   | `Army_ML_Pipeline_and_Files/` |
| `train_health_model.py`    | `Army_ML_Pipeline_and_Files/` |
| `temporal_model.py`        | `Army_ML_Pipeline_and_Files/` |
| `run_inference.py`         | `Army_ML_Pipeline_and_Files/` |
| `evaluate_ensemble.py`     | `Army_ML_Pipeline_and_Files/` |
| `export_database.py`       | `database_utils/` |
| `export_db_stats.py`       | `database_utils/` |
| `verify_database.py`       | `database_utils/` |
| `verify_labels.py`         | `database_utils/` |
| `find_db_location.py`      | `database_utils/` |

> **Security Note:** Do not commit real passwords to GitHub.  
> Consider using environment variables: `os.environ.get('DB_PASSWORD')` instead of hardcoding.

---

## Step 2 — Verify Your Database Schema

The ML pipeline queries **6 core tables** with specific column names.  
Run the verification script first:

```powershell
generate_data_env\Scripts\python.exe database_utils\verify_database.py
```

Then cross-check your real DB against the **required schema** listed below.

---

### Required Schema: Table-by-Table

#### Table 1: `vehicles`
| Column Name | Type | Used By |
|---|---|---|
| `vehicle_id` | VARCHAR / INT (Primary Key) | All scripts |
| `vehicle_type` | VARCHAR | `feature_engineering.py` |
| `acquisition_date` | DATE | `feature_engineering.py` (age calculation) |
| `operational_status` | VARCHAR | `verify_database.py` |

**If your real table uses different names**, find and replace in `feature_engineering.py`:
```python
# Example: if your column is named 'acq_date' instead of 'acquisition_date'
# Find this line in feature_engineering.py:
df['vehicle_age_years'] = (datetime.now() - pd.to_datetime(df['acquisition_date'])).dt.days / 365
# Change 'acquisition_date' to your actual column name
```

---

#### Table 2: `telemetry_data`
This is the most critical table. The pipeline queries these columns:

| Expected Column Name | Description | If Your Column is Named Differently |
|---|---|---|
| `vehicle_id` | FK to vehicles | Rename in SQL query |
| `timestamp` | Reading timestamp | Change ORDER BY / GROUP BY references |
| `engine_coolant_temp_celsius` | Coolant temp in °C | Update in `feature_engineering.py` line ~95 |
| `battery_voltage` | Voltage reading | Update in `feature_engineering.py` line ~102 |
| `engine_rpm` | Engine RPM | Update in `temporal_model.py` line ~19 |
| `engine_load_percent` | 0-100% load | Update in `feature_engineering.py` |
| `fuel_consumption_lph` | Liters per hour | Update in `feature_engineering.py` |
| `idle_time_minutes` | Idle minutes per record | Update in `feature_engineering.py` |
| `current_speed_kmph` | Speed in km/h | Update in `feature_engineering.py` |
| `oil_pressure_psi` | Oil pressure | Update in `temporal_model.py` |
| `tire_pressure_psi_avg` | Avg tire pressure | Update in `temporal_model.py` |
| `odometer_km` | Total km reading | Update in `temporal_model.py` |
| `fuel_level_percent` | Fuel tank % | Update in `temporal_model.py` |

#### How to Update Telemetry Column Names in `feature_engineering.py`

Search for the `compute_telemetry_features` function (around line 80) and update the SQL:

```python
# ORIGINAL query (example):
df = pd.read_sql("""
    SELECT vehicle_id,
           engine_coolant_temp_celsius,
           battery_voltage,
           engine_load_percent,
           fuel_consumption_lph,
           idle_time_minutes,
           current_speed_kmph,
           timestamp
    FROM telemetry_data
    WHERE vehicle_id = %s
    ORDER BY timestamp
""", conn, params=(vehicle_id,))

# UPDATED (if your columns have different names):
df = pd.read_sql("""
    SELECT vehicle_id,
           coolant_temp        AS engine_coolant_temp_celsius,  -- map your name → expected name
           volt                AS battery_voltage,
           load_pct            AS engine_load_percent,
           fuel_lph            AS fuel_consumption_lph,
           idle_mins           AS idle_time_minutes,
           speed_kph           AS current_speed_kmph,
           reading_time        AS timestamp
    FROM vehicle_telemetry                                       -- if table name differs
    WHERE vehicle_id = %s
    ORDER BY reading_time
""", conn, params=(vehicle_id,))
```

Using SQL `AS` aliases lets you rename columns **in the query** without touching any downstream code.

---

#### Table 3: `maintenance_records`
| Expected Column Name | Description |
|---|---|
| `maintenance_id` | Primary key |
| `vehicle_id` | FK to vehicles |
| `service_date` | Date of service |
| `service_type` | 'emergency' / 'corrective' / 'preventive' |
| `pre_service_health_score` | Health score before service (0–100) |
| `post_service_health_score` | Health score after service |
| `service_cost` | Cost of service |
| `vehicle_status` | **ADDED BY the pipeline** — 5-class label column (see Step 3) |

> If your `service_type` uses different values (e.g., 'urgent' instead of 'emergency'),
> update `assign_vehicle_status.py` → `SVC_TYPE_BASE` dictionary.

---

#### Table 4: `diagnostic_codes`
| Expected Column Name | Description |
|---|---|
| `vehicle_id` | FK to vehicles |
| `code` | DTC code (e.g., 'P0300') |
| `severity` | 'critical' / 'major' / 'minor' / 'warning' |
| `system_affected` | e.g., 'Engine', 'Electrical' |
| `detected_timestamp` | When code was detected |
| `resolved_timestamp` | When resolved (NULL if still active) |
| `is_active` | BOOLEAN (1=active, 0=resolved) |

---

#### Table 5: `operational_logs`
| Expected Column Name | Description |
|---|---|
| `vehicle_id` | FK to vehicles |
| `mission_type` | e.g., 'combat_training', 'transport', 'patrol' |
| `terrain_difficulty_score` | 1–10 difficulty rating |
| `harsh_braking_count` | Number of harsh braking events per trip |
| `trip_distance_km` | Distance of the trip in km |
| `cargo_weight_kg` | Cargo load in kg |

---

#### Table 6: `fuel_records`
| Expected Column Name | Description |
|---|---|
| `vehicle_id` | FK to vehicles |
| `refuel_date` | Date of refuel |
| `fuel_efficiency_kmpl` | Km per litre at this refuel |

---

#### Table 7: `health_scores` (OUTPUT table — written by the pipeline)
This table is **written to by `run_inference.py`**. Create it in your real DB if it doesn't exist:

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
    INDEX idx_vehicle_date (vehicle_id, assessment_date)
);
```

---

## Step 3 — Run the One-Time Label Assignment

Before training the ML models, you must add a `vehicle_status` classification column
to your `maintenance_records` table. This is a **one-time setup step**:

```powershell
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\assign_vehicle_status.py
```

This script:
- Adds `vehicle_status VARCHAR(20)` column to `maintenance_records`
- Scores every maintenance record using DTC severity + service type
- Assigns one of: `Critical`, `Poor`, `Attention`, `Good`, `Excellent`
- Uses exact quintile bucketing (20% per class) → perfectly balanced labels

**Expected output:**
```
==============================
LABEL DISTRIBUTION
==============================
  Critical     xxxx  (20.00%)  ##########
  Poor         xxxx  (20.00%)  ##########
  Attention    xxxx  (20.00%)  ##########
  Good         xxxx  (20.00%)  ##########
  Excellent    xxxx  (20.00%)  ##########
```

If you see errors, check that `service_type` values in your DB are exactly:
`'emergency'`, `'corrective'`, or `'preventive'` (lowercase).

---

## Step 4 — Run the Full ML Pipeline

Once credentials and schema are verified:

```powershell
# From the project root:
.\run_pipeline.ps1
```

Or run each step individually for more control:

```powershell
# Step 1: Build feature matrix from real DB
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\feature_engineering.py

# Step 2: Train all three models (takes 20–60 min depending on data size)
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\train_health_model.py

# Step 3 (Optional): Run Bi-LSTM temporal channel
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\temporal_model.py

# Step 4: Optimise and select champion ensemble
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\optimize_ensemble.py

# Step 5: Run inference — writes to health_scores table
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\run_inference.py

# Step 6: Evaluate results
generate_data_env\Scripts\python.exe -X utf8 Army_ML_Pipeline_and_Files\evaluate_ensemble.py
```

---

## Step 5 — Verify Integration Success

### 5a. Check the feature matrix was built correctly
```powershell
generate_data_env\Scripts\python.exe -c "
import pandas as pd
df = pd.read_parquet('Army_ML_Pipeline_and_Files/vehicle_features.parquet')
print('Shape:', df.shape)
print('Columns:', list(df.columns))
print(df.head(3))
"
```
Expected: `Shape: (N_VEHICLES, ~59)` — one row per vehicle.  
If N_VEHICLES is correct and no columns are all-zero or all-NaN, the DB integration is working.

### 5b. Check health_scores table was populated
```powershell
generate_data_env\Scripts\python.exe database_utils\verify_database.py
```
The `health_scores` table row count should now equal your total vehicle count.

### 5c. Check evaluation metrics
Open `Army_ML_Pipeline_and_Files/reports/ensemble_evaluation_detailed.txt`  
Expected metrics on real data: Macro F1 > 0.85 (may differ from synthetic 91.06% baseline).

---

## Step 6 — Files to Delete After Successful Integration

Once the pipeline is running successfully on real data, you may delete these development artifacts:

### Delete (no longer needed):
```
data_generation/                        ← Entire folder (synthetic data scripts)
  generate_data.py                      ← Only used to build fake DB
  generate_synthetic_labels.py          ← Only used to create fake labels
  requirements_generate_data.txt
  *.log

Army_ML_Pipeline_and_Files/
  vehicle_features.parquet              ← Will be regenerated from real DB
  reports/                              ← Will be regenerated after real training
    confusion_matrix.png
    shap_global.png
    shap_per_class_critical.png
    classification_report.txt
    ensemble_roc_curve.png
    mlops/run_*.json

  models/                               ← OLD synthetic-trained models — delete these
    xgb_best.pkl                        ← Pipeline will regenerate from real data
    lgbm_best.pkl
    tabnet_best.zip
    meta_learner.pkl
    meta_learner_rf.pkl
    oof_xgb.npy
    oof_lgbm.npy
    oof_tabnet.npy
    temporal_probs.npy
    temporal_sequences.npy
```

### KEEP (these are code/config — not data-dependent):
```
Army_ML_Pipeline_and_Files/
  *.py                                  ← All Python scripts — KEEP
  models/
    ensemble_config.json                ← Will be overwritten by real training
    ensemble_weights.json               ← Will be overwritten
    feature_names.json                  ← Will be overwritten
    temperature_scalars.json            ← Will be overwritten
  requirements.txt                      ← KEEP

database_utils/                         ← All scripts — KEEP
docs/                                   ← All documentation — KEEP
run_pipeline.ps1                        ← KEEP
README.md                               ← KEEP
.gitignore                              ← KEEP
Army_ML_Pipeline_Documentation.pdf     ← KEEP
```

> **Note:** The `.json` files in `models/` will automatically be **overwritten** when you run
> `optimize_ensemble.py` on real data. You do not need to manually delete them — the pipeline
> replaces them with real-data-trained values.

---

## Troubleshooting Common Issues

| Error | Likely Cause | Fix |
|---|---|---|
| `mysql.connector.errors.ProgrammingError: Unknown column 'engine_coolant_temp_celsius'` | Real DB uses a different column name | Add SQL `AS` alias in the query (see Step 2) |
| `KeyError: 'vehicle_status'` in feature_engineering.py | `assign_vehicle_status.py` not run yet | Run Step 3 first |
| `Empty feature matrix` or all-NaN columns | `maintenance_records` has no matching vehicle IDs with telemetry | Verify FK relationships in your DB |
| `SMOTE error: n_samples < n_neighbors` | Too few samples in one class | Check label distribution after `assign_vehicle_status.py` |
| `UnicodeEncodeError` | Windows console encoding | Always run with `-X utf8` flag |
| `health_scores table doesn't exist` | Table not created in real DB | Run the CREATE TABLE SQL from Step 2 |
| XGBoost/LightGBM F1 drops significantly | Real data distribution differs from synthetic | Retune Optuna HPO — increase `N_TRIALS` in `train_health_model.py` |

---

## Contact / Questions

For questions about the ML pipeline architecture, model choices, or feature engineering logic,
refer to:
- **Full Technical Documentation:** `Army_ML_Pipeline_Documentation.pdf` (21-page reference)
- **Database Schema Reference:** `docs/README_DATABASE.md`
- **Quick Command Reference:** `docs/QUICK_REFERENCE.md`
