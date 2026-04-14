"""
============================================================
STEP 5: run_inference.py
============================================================
Runs the full trained ensemble on all 5,000 vehicles and
writes health predictions to the health_scores table.

Inference pipeline:
  1. Load all model artifacts from models/
  2. Apply temperature calibration to each model's probs
  3. Stack → meta-learner → final class probabilities
  4. Compute overall_health_score from data-anchored midpoints
  5. Derive health_status, confidence_level, risk_category,
     recommended_action per vehicle
  6. Write 5,000 rows to health_scores table

health_score formula:
  score = Σ P(class_i) × midpoint_i
  midpoints are anchored to the actual mean pre_service_health_score
  per vehicle_status class from maintenance_records.
============================================================
"""

import os
import json
import pickle
import warnings
import sys
import numpy as np
import pandas as pd
import mysql.connector
from mlops_tracker import MLOpsTracker

# Fix Windows CP1252 console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR    = os.path.join(BASE_DIR, 'models')
FEATURES_PATH = os.path.join(BASE_DIR, 'vehicle_features.parquet')

# ── DB Config ────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'military_vehicle_health',
    'user':     'root',
    'password': 'vedant@14',
    'charset':  'utf8mb4',
}

STATUS_ORDER = ['Critical', 'Poor', 'Attention', 'Good', 'Excellent']

# Recommended actions per status
RECOMMENDATIONS = {
    'Critical':  'Immediate grounding required. Schedule emergency inspection and repair.',
    'Poor':      'Withdraw from active duty. Plan corrective maintenance within 48 hours.',
    'Attention': 'Schedule corrective maintenance within 7 days. Monitor closely.',
    'Good':      'Proceed with next scheduled preventive maintenance.',
    'Excellent': 'Vehicle in good health. Continue normal operations.',
}

# Risk category mapping
RISK_MAP = {
    'Critical':  'critical',
    'Poor':      'high',
    'Attention': 'medium',
    'Good':      'low',
    'Excellent': 'low',
}

# Health status mapping to DB ENUM values
HEALTH_STATUS_MAP = {
    'Critical':  'critical',
    'Poor':      'poor',
    'Attention': 'fair',
    'Good':      'good',
    'Excellent': 'excellent',
}

MODEL_VERSION = 'v3.1-Temporal-Fusion'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def temperature_scale(probs: np.ndarray, T: float) -> np.ndarray:
    log_p  = np.log(probs.clip(1e-10))
    scaled = log_p / max(T, 0.01)
    exp_s  = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return exp_s / exp_s.sum(axis=1, keepdims=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOAD ARTIFACTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_artifacts():
    print("Loading model artifacts...")

    with open(os.path.join(MODELS_DIR, 'xgb_best.pkl'),      'rb') as f: xgb    = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'lgbm_best.pkl'),     'rb') as f: lgbm   = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'meta_learner.pkl'),  'rb') as f: meta   = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'label_encoder.pkl'), 'rb') as f: le     = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'feature_names.json'))   as f: feat_names = json.load(f)
    with open(os.path.join(MODELS_DIR, 'temperature_scalars.json')) as f: temps = json.load(f)

    # TabNet
    tabnet = None
    tabnet_path = os.path.join(MODELS_DIR, 'tabnet_best.zip')
    if os.path.exists(tabnet_path):
        try:
            from pytorch_tabnet.tab_model import TabNetClassifier
            tabnet = TabNetClassifier()
            tabnet.load_model(tabnet_path)
            print("  TabNet loaded.")
        except ImportError:
            print("  [WARN] pytorch-tabnet not installed — skipping TabNet.")

    # Temporal Channel (LSTM)
    temporal_probs = None
    tp_path = os.path.join(MODELS_DIR, 'temporal_probs.npy')
    if os.path.exists(tp_path):
        temporal_probs = np.load(tp_path)
        print("  Temporal Channel initialized.")

    # TabPFN is no longer used in this version.
    tabpfn_clf = None

    print("  Core artifacts loaded (XGBoost, LightGBM, meta-learner).")
    return xgb, lgbm, tabnet, tabpfn_clf, meta, le, feat_names, temps, temporal_probs


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANCHOR HEALTH SCORE MIDPOINTS FROM DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_score_midpoints():
    """
    Compute mean pre_service_health_score per vehicle_status class.
    These become the midpoints for the health score formula.
    Falls back to hard-coded values if data unavailable.
    """
    try:
        conn   = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT vehicle_status,
                   AVG(pre_service_health_score) AS avg_score
            FROM   maintenance_records
            WHERE  vehicle_status IS NOT NULL
              AND  pre_service_health_score IS NOT NULL
            GROUP BY vehicle_status
        """)
        rows = cursor.fetchall()
        conn.close()
        midpoints = {r['vehicle_status']: float(r['avg_score']) for r in rows}
        print(f"  Data-anchored midpoints: {midpoints}")
    except Exception as e:
        print(f"  [WARN] Could not fetch midpoints ({e}). Using defaults.")
        midpoints = {
            'Critical': 15.0, 'Poor': 35.0, 'Attention': 55.0,
            'Good': 75.0, 'Excellent': 92.0
        }
    return midpoints


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INFERENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_inference(xgb, lgbm, tabnet, tabpfn_clf, meta,
                  le, feat_names, temps, df_full, temporal_probs):

    vehicle_ids = df_full['vehicle_id'].values
    X           = df_full[feat_names].values.astype(np.float32)

    print(f"\nRunning inference on {len(X):,} vehicles...")

    # Base model probabilities
    p_xgb  = temperature_scale(xgb.predict_proba(X),  temps['xgb'])
    p_lgbm = temperature_scale(lgbm.predict_proba(X), temps['lgbm'])
    print("  XGBoost + LightGBM: done.")

    # TabNet (if available)
    if tabnet is not None:
        p_tabnet = temperature_scale(tabnet.predict_proba(X), temps['tabnet'])
        print("  TabNet: done.")
    else:
        p_tabnet = np.full_like(p_xgb, 1.0 / 5)   # uniform fallback

    # TabPFN is no longer used.
    # We MUST stack only valid models now (XGB, LGBM, TabNet).

    # --- New Champion Selection Logic ---
    config_path = os.path.join(MODELS_DIR, 'ensemble_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        strategy = config.get('champion_strategy', 'Linear Stacking (Logistic)')
        print(f"  Using Champion Strategy: {strategy}")
    else:
        strategy = 'Linear Stacking (Logistic)'
        print(f"  Warning: ensemble_config.json not found. Falling back to {strategy}.")

    # --- Base Ensemble Strategies ---
    if strategy == 'Simple Average':
        final_p = (p_xgb + p_lgbm + p_tabnet) / 3.0
    
    elif strategy == 'Weighted Bayesian Blend':
        w = config['weighted_blend_params']
        final_p = (w['w_xgb'] * p_xgb + w['w_lgbm'] * p_lgbm + w['w_tabnet'] * p_tabnet)
    
    elif strategy == 'Linear Stacking (Logistic)':
        meta_X   = np.hstack([p_xgb, p_lgbm, p_tabnet])
        final_p  = meta.predict_proba(meta_X)
    
    elif strategy == 'Non-linear Stacking (RF)':
        # Load RF meta-learner
        rf_path = os.path.join(MODELS_DIR, 'meta_learner_rf.pkl')
        with open(rf_path, 'rb') as f:
            meta_rf = pickle.load(f)
        meta_X   = np.hstack([p_xgb, p_lgbm, p_tabnet])
        final_p  = meta_rf.predict_proba(meta_X)
    
    else:
        # Final fallback
        print("  Error: unknown strategy. Falling back to simple average.")
        final_p = (p_xgb + p_lgbm + p_tabnet) / 3.0

    # --- Phase 2: Temporal Fusion ---
    if temporal_probs is not None:
        print("  Applying Temporal Fusion (15% weight)...")
        # Blend the champion probabilities with the temporal channel
        final_p = (final_p * 0.85) + (temporal_probs * 0.15)
        
    print(f"  {strategy} applied with Temporal Fusion. Output shape: {final_p.shape}")
    return vehicle_ids, X, final_p


def generate_risk_evidence(X, df_full, feat_names, pred_classes):
    """
    For each vehicle, identify the top 3 sensors most distant from their mean 
    (local Z-score) that might be driving the risk status.
    """
    print("  Generating Risk Evidence (Explainability Channel)...")
    # Precompute means/stds for all matching features
    means = df_full[feat_names].mean()
    stds  = df_full[feat_names].std().replace(0, 1.0)
    
    # Calculate Z-scores
    z_scores = (df_full[feat_names] - means) / stds
    
    evidence_strings = []
    for i in range(len(X)):
        status = STATUS_ORDER[pred_classes[i]]
        if status in ['Excellent', 'Good']:
            evidence_strings.append("Nominal sensor readings.")
            continue
            
        # Get absolute Z-scores for this vehicle
        v_z = z_scores.iloc[i]
        top_3 = v_z.abs().sort_values(ascending=False).head(3)
        
        parts = []
        for feat, z in top_3.items():
            direction = "High" if z > 0 else "Low"
            # Cleanup feature name (e.g. neuro_corr_engine_temp -> Engine Temp)
            clean_feat = feat.replace('neuro_corr_', '').replace('_', ' ').title()
            parts.append(f"{direction} {clean_feat} (Z={z:.1f})")
            
        evidence_strings.append(", ".join(parts))
        
    return evidence_strings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WRITE TO health_scores
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def write_health_scores(vehicle_ids, final_p, midpoints, uncertainty, evidence):
    from datetime import date
    today     = date.today()
    midpoint_vec = np.array([midpoints[s] for s in STATUS_ORDER])

    # Compute health score, predicted class, confidence
    scores       = final_p @ midpoint_vec                          # (N,)
    pred_classes = final_p.argmax(axis=1)
    
    # Base confidence from ensemble probabilities
    base_confidence = final_p.max(axis=1) * 100
    
    # Uncertainty adjustment (MC Dropout from feature engineering)
    # We scale uncertainty to a reasonable reduction factor (e.g., 0-10% reduction)
    adjusted_confidence = base_confidence * (1.0 - np.clip(uncertainty * 2.0, 0, 0.2))

    rows = []
    for i, vid in enumerate(vehicle_ids):
        status_name  = STATUS_ORDER[pred_classes[i]]
        health_score = float(np.clip(scores[i], 0, 100))
        conf_level   = float(adjusted_confidence[i])
        h_status     = HEALTH_STATUS_MAP[status_name]
        risk_cat     = RISK_MAP[status_name]
        action       = RECOMMENDATIONS[status_name]

        rows.append((
            vid,
            today,
            round(health_score, 2),
            h_status,
            None,    # engine_health_score — future use
            None,    # transmission_health_score
            None,    # brake_system_score
            None,    # electrical_system_score
            None,    # predicted_days_to_service
            None,    # predicted_service_date
            round(conf_level, 2),
            risk_cat,
            action,
            evidence[i],
            MODEL_VERSION,
        ))

    print(f"\nWriting {len(rows):,} rows to health_scores table...")
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Clear existing predictions for today (idempotent)
    cursor.execute("DELETE FROM health_scores WHERE assessment_date = %s", (today,))
    conn.commit()

    insert_sql = """
        INSERT INTO health_scores (
            vehicle_id, assessment_date, overall_health_score, health_status,
            engine_health_score, transmission_health_score, brake_system_score,
            electrical_system_score, predicted_days_to_service,
            predicted_service_date, confidence_level, risk_category,
            recommended_action, risk_evidence, model_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        cursor.executemany(insert_sql, rows[i:i + batch_size])
        conn.commit()
        print(f"  Inserted {min(i + batch_size, len(rows)):,}/{len(rows):,} rows...")

    cursor.close()
    conn.close()
    print(f"Done. {len(rows):,} health scores written.")
    return scores, pred_classes, adjusted_confidence


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    print("=" * 60)
    print("ENSEMBLE INFERENCE → health_scores TABLE")
    print("=" * 60)

    # Load artifacts
    xgb, lgbm, tabnet, tabpfn_clf, meta, le, feat_names, temps, temporal_probs = load_artifacts()

    # Load feature matrix
    df_full = pd.read_parquet(FEATURES_PATH)
    print(f"Feature matrix: {df_full.shape}")

    # Data-anchored score midpoints
    print("\nComputing data-anchored health score midpoints...")
    midpoints = get_score_midpoints()

    # Run inference
    vehicle_ids, X, final_p = run_inference(
        xgb, lgbm, tabnet, tabpfn_clf, meta, le, feat_names, temps, df_full, temporal_probs
    )

    # MLOps Initialization
    tracker = MLOpsTracker(experiment_name="VehicleHealth_v3_Deployment")
    tracker.log_param("model_version", MODEL_VERSION)
    tracker.log_param("use_temporal_fusion", temporal_probs is not None)

    # Advanced Explainability (Phase 4)
    pred_classes_raw = final_p.argmax(axis=1)
    evidence = generate_risk_evidence(X, df_full, feat_names, pred_classes_raw)

    # Write to DB
    uncertainty = df_full['neural_uncertainty'].values
    scores, pred_classes, adjusted_confidence = write_health_scores(
        vehicle_ids, final_p, midpoints, uncertainty, evidence
    )
    
    # Log deployment metrics
    tracker.log_metric("mean_health_score", scores.mean())
    tracker.log_metric("avg_confidence", adjusted_confidence.mean())
    tracker.log_metric("mean_uncertainty", uncertainty.mean())
    tracker.finalize()

    # Summary
    print("\n" + "=" * 60)
    print("HEALTH SCORE SUMMARY (v3.1 Temporal-Fusion Enabled)")
    print("=" * 60)
    print(f"  Score range : {scores.min():.1f} – {scores.max():.1f}")
    print(f"  Mean score  : {scores.mean():.1f}")
    print(f"  Std dev     : {scores.std():.1f}")
    print(f"  Avg confidence: {adjusted_confidence.mean():.1f}% (adjusted for uncertainty)")
    print(f"  Mean uncertainty: {uncertainty.mean():.4f}")
    print("\n  Class distribution:")
    unique, counts = np.unique(pred_classes, return_counts=True)
    for cls_idx, cnt in zip(unique, counts):
        bar = '█' * max(1, cnt // 100)
        print(f"    {STATUS_ORDER[cls_idx]:12} {cnt:5}  {bar}")

    print("\nPipeline complete. health_scores table is populated.")


if __name__ == '__main__':
    main()
