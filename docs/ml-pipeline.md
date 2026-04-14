# 🧠 ML Pipeline — Deep Dive

## Military Vehicle Inventory Logistics Optimization and Prediction System

---

## Pipeline Overview

The ML pipeline is a **7-stage sequential system** that transforms raw vehicle telemetry and maintenance records into actionable health predictions for every vehicle in the fleet. Each stage produces an artifact consumed by the next.

```
MySQL Database (real Army telemetry)
        │
        ▼
[Stage 1]  assign_vehicle_status.py   → Adds 5-class labels to maintenance_records
        │
        ▼
[Stage 2]  feature_engineering.py     → vehicle_features.parquet  (5,000 × ~59 features)
        │
        ▼
[Stage 3]  train_health_model.py      → xgb_best.pkl · lgbm_best.pkl · tabnet_best.zip
        │                               oof_xgb.npy · oof_lgbm.npy · oof_tabnet.npy
        ▼
[Stage 4]  temporal_model.py          → temporal_probs.npy  (Bi-LSTM channel)
        │
        ▼
[Stage 5]  optimize_ensemble.py       → ensemble_config.json  (champion strategy)
        │
        ▼
[Stage 6]  run_inference.py           → health_scores table  (5,000 rows written)
        │
        ▼
[Stage 7]  evaluate_ensemble.py       → reports/  (metrics + ROC curves)
```

---

## Stage 1 — Vehicle Status Label Assignment

**Script:** `Army_ML_Pipeline_and_Files/assign_vehicle_status.py`

The pipeline uses **outcome-derived labels** — labels are computed from actual service events and DTC fault severity, not from sensor readings. This prevents target leakage.

### Label Classes (Ordinal, 5-class)

| Class | Index | Assigned When |
|---|---|---|
| `Critical` | 0 | Emergency service OR active critical DTC |
| `Poor` | 1 | Corrective service + multiple major DTCs |
| `Attention` | 2 | Corrective service + minor/major DTCs |
| `Good` | 3 | Preventive service + minor DTCs |
| `Excellent` | 4 | Preventive service + no/warning DTCs only |

### Temporal DTC Severity Scoring

DTCs are not binary flags. Each code gets a **time-decayed severity score**:

```
Active DTC:   score = severity_rank × exp(−days_since_detection / 90)
Resolved DTC: score = severity_rank × exp(−days_since_resolution / 45)

Severity ranks: critical=4  major=3  minor=2  warning=1
```

### Health Score Formula

```
svc_score    = {emergency: 0.0,  corrective: 0.35,  preventive: 0.75}
dtc_penalty  = min(max_temporal_rank / 4.0,  1.0) × 0.50
major_penalty = min(log1p(major_count)/ log1p(20), 1.0) × 0.30
total_penalty = min(total_dtc_score / 20.0,  1.0) × 0.20
recency_pen  = min(corrective_in_180d / 6.0, 1.0) × 0.25

health_score = svc_score − 0.50×dtc_pen − 0.12×major_pen
                         − 0.04×total_pen − 0.15×recency_pen
```

**Bucketing:** All records sorted ascending → exact quintiles (20% per class) → perfectly balanced dataset.

---

## Stage 2 — Feature Engineering

**Script:** `Army_ML_Pipeline_and_Files/feature_engineering.py`  
**Output:** `vehicle_features.parquet` — 5,000 rows × ~59 columns

### Feature Groups

| Group | Features | Count |
|---|---|---|
| **Telemetry** | avg/max/std coolant_temp, p95_coolant, overheat_count, avg/min voltage, voltage_drop_count, avg_rpm, avg_engine_load, high_load_count, avg_fuel_lph, total_idle_min, avg_speed, idle_ratio | 16 |
| **Telemetry Interactions** | thermal_stress_index, elec_thermal_risk | 2 |
| **Rolling Windows** | r7d/r30d/r90d for coolant_mean, voltage_drops, load_mean, fuel_mean | 12 |
| **Degradation Velocity** | temp_trend (r90d − r7d coolant), fuel_slope (linear regression) | 2 |
| **Fuel** | avg_efficiency, min_efficiency, max_efficiency, efficiency_degradation, efficiency_slope, total_refuels | 6 |
| **Operational** | total_trips, avg_trip_distance, avg_terrain_difficulty, avg_cargo_weight, total_harsh_events, combat_ratio, abuse_rate | 7 |
| **DTC** | dtc_total, dtc_critical, dtc_major, dtc_minor, dtc_active | 5 |
| **Vehicle Meta** | vehicle_age_years, total_mileage, total_engine_hours, mileage_per_year, vtype_* (5 one-hot cols) | 9 |
| **Neural Latent** | latent_0 … latent_9 (Autoencoder bottleneck) | 10 |
| **Neural Interactions** | neural_interaction_0 … 3 (layer-1 activation variance) | 4 |
| **Uncertainty** | neural_uncertainty (MC Dropout std) | 1 |

**Total: ~74 features** (some vehicles may have fewer rolling window features if data is sparse)

### Neural Enhancement (NeuralFeatureEnhancer)

Three neural passes run after SQL aggregation:

1. **Autoencoder** `[input → 32 → 10 → 32 → input]`  
   Trained 30 epochs on StandardScaler-normalised data.  
   The 10-dimensional bottleneck becomes `latent_0…latent_9`.

2. **FeatureScorerNN** `[input → 64 → ReLU → Dropout(0.2) → 32 → 5]`  
   Gradient-based saliency computed (sum of |∂output/∂input| per feature).  
   Top-4 high-variance layer-1 neurons saved as `neural_interaction_0…3`.

3. **MC Dropout uncertainty** — 30 stochastic forward passes, std of softmax outputs → `neural_uncertainty`.

---

## Stage 3 — Model Training

**Script:** `Army_ML_Pipeline_and_Files/train_health_model.py`

Three base classifiers trained via **5-fold stratified OOF** with SMOTE applied per fold (preventing leakage):

### Model 1 — XGBoost

| Parameter | Value | Source |
|---|---|---|
| `objective` | `multi:softprob` | Fixed |
| `n_estimators` | **811** | Optuna TPE, 50 trials |
| `max_depth` | **6** | Optuna |
| `learning_rate` | **0.01564** | Optuna |
| `gamma` | **2.569** | Optuna |
| `reg_alpha` | **8.115** | Optuna |
| `subsample` | **0.709** | Optuna |
| `colsample_bytree` | **0.960** | Optuna |
| `tree_method` | `hist` | Fixed (CPU efficient) |

### Model 2 — LightGBM

| Parameter | Value |
|---|---|
| `n_estimators` | **646** |
| `num_leaves` | **197** |
| `max_depth` | **4** |
| `learning_rate` | **0.0649** |
| `min_child_samples` | **68** |
| `reg_alpha` | **9.879** |

### Model 3 — TabNet

| Parameter | Value |
|---|---|
| `n_d` / `n_a` | **32 / 32** |
| `n_steps` | **5** |
| `gamma` | **1.6** |
| `lambda_sparse` | **0.0001** |
| `max_epochs` | 300 (patience=20) |

### SHAP Explainability

- `shap.TreeExplainer` applied to XGBoost model post-training
- Global feature importance beeswarm plot → `reports/shap_global.png`
- Per-class plot for Critical status → `reports/shap_per_class_critical.png`
- Feature importance rankings → `reports/shap_importance.csv`

---

## Stage 4 — Temporal Channel (Bi-LSTM)

**Script:** `Army_ML_Pipeline_and_Files/temporal_model.py`

Captures **sequential sensor degradation patterns** invisible to static tabular models.

### Architecture

```
Input:  (batch, seq_len=50, features=8)
          8 sensors: coolant_temp · fuel_level · odometer
                     speed · oil_pressure · battery_voltage
                     tire_pressure · engine_rpm

LSTM:   Bidirectional, hidden_dim=64, n_layers=2, dropout=0.2
        → output: (batch, 50, 128)   [64 fwd + 64 bwd]

Pool:   Last hidden state: lstm_out[:, -1, :]  → (batch, 128)

FC:     Linear(128, 5) → logits → softmax → (batch, 5)
```

Output `temporal_probs.npy` contributes **15% weight** in Stage 6 ensemble fusion.

---

## Stage 5 — Ensemble Optimisation

**Script:** `Army_ML_Pipeline_and_Files/optimize_ensemble.py`

### Temperature Scaling

For each model's OOF probabilities, finds scalar `T` minimising NLL:

```
scaled = log(probs.clip(1e-10)) / T
output = softmax(scaled − max(scaled))   # numerically stable
T* = argmin_T  −mean(log(P_true))
```

### Meta-Learner Stacking

`LogisticRegression(C=0.5, multi_class='multinomial')` trained on horizontally stacked calibrated OOF matrices `(5000, 15)`.

### Ensemble Tournament Results

| Strategy | Macro F1 | Rank |
|---|---|---|
| **Weighted Bayesian Blend** | **0.9106** | 🥇 Champion |
| Non-linear Stacking (RF) | 0.9097 | 2nd |
| Simple Average | 0.9056 | 3rd |
| Linear Stacking (Logistic) | 0.9019 | 4th |

**Champion weights:** XGB = 93.53% · TabNet = 6.37% · LGBM = 0.11%

---

## Stage 6 — Inference

**Script:** `Army_ML_Pipeline_and_Files/run_inference.py`  
**Output:** `health_scores` MySQL table — 5,000 rows

### Health Score Formula

```
midpoints = data-anchored class means from maintenance_records
            {Critical: ~15, Poor: ~35, Attention: ~55, Good: ~75, Excellent: ~92}

overall_health_score = Σ P(class_i) × midpoint_i   [0–100 scale]
```

### Confidence Adjustment

```
base_confidence     = max(P_class) × 100
adjusted_confidence = base_confidence × (1 − clip(neural_uncertainty × 2, 0, 0.2))
```

### Explainability (Risk Evidence)

For every Attention/Poor/Critical vehicle, top-3 anomalous features identified via fleet Z-scores:
```
z = (vehicle_value − fleet_mean) / fleet_std
evidence = "High Thermal Stress Index (Z=2.3), Low Min Voltage (Z=-1.9), ..."
```

### Recommendations Written to DB

| Status | Recommended Action |
|---|---|
| Critical | Immediate grounding required. Schedule emergency inspection and repair. |
| Poor | Withdraw from active duty. Plan corrective maintenance within 48 hours. |
| Attention | Schedule corrective maintenance within 7 days. Monitor closely. |
| Good | Proceed with next scheduled preventive maintenance. |
| Excellent | Vehicle in good health. Continue normal operations. |

---

## Stage 7 — Evaluation

**Script:** `Army_ML_Pipeline_and_Files/evaluate_ensemble.py`

| Metric | Synthetic Baseline | Description |
|---|---|---|
| Overall Accuracy | ~91% | % correctly classified |
| Macro Precision | ~91% | Avg precision, equal class weight |
| Macro Recall | ~91% | Avg recall, equal class weight |
| **Macro F1** | **91.06%** | Harmonic mean P/R |
| Macro AUC-ROC | **>0.97** | One-vs-Rest across 5 classes |

**Outputs:**
- `reports/ensemble_evaluation_detailed.txt` — full per-class classification report
- `reports/ensemble_roc_curve.png` — 5-class ROC curves with AUC values

---

> 🔙 [Back to README](../README.md)
