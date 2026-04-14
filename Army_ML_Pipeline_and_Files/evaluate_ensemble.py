"""
============================================================
STEP 6: evaluate_ensemble.py
============================================================
Evaluates the final ensemble model using comprehensive metrics:
  1. Accuracy, Precision, Recall, F1-score (all in percentages)
  2. Multi-class AUC-ROC (One-vs-Rest)
  3. Visualizes ROC curves for each class

Uses Out-of-Fold (OOF) predictions stored in models/
============================================================
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             roc_auc_score, roc_curve, auc, classification_report)
from sklearn.preprocessing import label_binarize

# ── Paths ────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR    = os.path.join(BASE_DIR, 'models')
REPORTS_DIR   = os.path.join(BASE_DIR, 'reports')
FEATURES_PATH = os.path.join(BASE_DIR, 'vehicle_features.parquet')

STATUS_ORDER  = ['Critical', 'Poor', 'Attention', 'Good', 'Excellent']
N_CLASSES     = 5

def temperature_scale(probs: np.ndarray, T: float) -> np.ndarray:
    """Apply temperature scaling to probability matrix."""
    log_p = np.log(probs.clip(1e-10))
    scaled = log_p / max(T, 0.01)
    exp_s  = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return exp_s / exp_s.sum(axis=1, keepdims=True)

def main():
    print("=" * 60)
    print("ENSEMBLE EVALUATION")
    print("=" * 60)

    # 1. Load Data & Artifacts
    print("Loading OOF predictions and labels...")
    oof_xgb    = np.load(os.path.join(MODELS_DIR, 'oof_xgb.npy'))
    oof_lgbm   = np.load(os.path.join(MODELS_DIR, 'oof_lgbm.npy'))
    oof_tabnet = np.load(os.path.join(MODELS_DIR, 'oof_tabnet.npy'))

    with open(os.path.join(MODELS_DIR, 'label_encoder.pkl'), 'rb') as f:
        le = pickle.load(f)
    
    # Load Meta-learner for Linear Stacking
    with open(os.path.join(MODELS_DIR, 'meta_learner.pkl'), 'rb') as f:
        meta_learner = pickle.load(f)

    # Load Tournament Config
    config_path = os.path.join(MODELS_DIR, 'ensemble_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        strategy = config.get('champion_strategy', 'Linear Stacking (Logistic)')
    else:
        strategy = 'Linear Stacking (Logistic)'
        config = {'weighted_blend_params': {'w_xgb': 0.33, 'w_lgbm': 0.33, 'w_tabnet': 0.34}}

    with open(os.path.join(MODELS_DIR, 'temperature_scalars.json'), 'r') as f:
        temps = json.load(f)

    df = pd.read_parquet(FEATURES_PATH)
    y_true = le.transform(df['vehicle_status'].values)

    # 2. Ensemble Reconstruction
    print("Calibrating and stacking OOF predictions...")
    cal_xgb    = temperature_scale(oof_xgb,    temps['xgb'])
    cal_lgbm   = temperature_scale(oof_lgbm,   temps['lgbm'])
    cal_tabnet = temperature_scale(oof_tabnet, temps['tabnet'])

    # --- Champion Strategy Application ---
    print(f"Applying Champion Strategy: {strategy}")
    
    if strategy == 'Simple Average':
        y_prob = (cal_xgb + cal_lgbm + cal_tabnet) / 3.0
    
    elif strategy == 'Weighted Bayesian Blend':
        w = config['weighted_blend_params']
        y_prob = (w['w_xgb'] * cal_xgb + w['w_lgbm'] * cal_lgbm + w['w_tabnet'] * cal_tabnet)
    
    elif strategy == 'Linear Stacking (Logistic)':
        meta_X = np.hstack([cal_xgb, cal_lgbm, cal_tabnet])
        y_prob = meta_learner.predict_proba(meta_X)
    
    elif strategy == 'Non-linear Stacking (RF)':
        # Load RF meta-learner
        rf_path = os.path.join(MODELS_DIR, 'meta_learner_rf.pkl')
        with open(rf_path, 'rb') as f:
            meta_rf = pickle.load(f)
        meta_X = np.hstack([cal_xgb, cal_lgbm, cal_tabnet])
        y_prob = meta_rf.predict_proba(meta_X)
    
    else:
        print("Unknown strategy. Falling back to simple average.")
        y_prob = (cal_xgb + cal_lgbm + cal_tabnet) / 3.0

    y_pred = y_prob.argmax(axis=1)

    # 3. Metrics Calculation
    print(f"\nCalculating metrics for {strategy}...")
    
    # Simple Accuracy
    acc = accuracy_score(y_true, y_pred) * 100

    # Precision, Recall, F1 (Macro)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='macro')
    
    # Multi-class AUC-ROC
    # Binarize labels for per-class AUC-ROC / Macro AUC-ROC
    y_true_bin = label_binarize(y_true, classes=np.arange(N_CLASSES))
    auc_roc_macro = roc_auc_score(y_true_bin, y_prob, multi_class='ovr', average='macro')

    # 4. Detailed Report
    print(f"\n{'='*40}")
    print(f"{'Metric':20} | {'Value (%)':>10}")
    print(f"{'-'*40}")
    print(f"{'Overall Accuracy':20} | {acc:10.2f}%")
    print(f"{'Macro Precision':20} | {(precision*100):10.2f}%")
    print(f"{'Macro Recall':20} | {(recall*100):10.2f}%")
    print(f"{'Macro F1-Score':20} | {(f1*100):10.2f}%")
    print(f"{'Macro AUC-ROC':20} | {auc_roc_macro:10.4f}")
    print(f"{'='*40}")

    # Generate full classification report
    full_report = classification_report(y_true, y_pred, target_names=STATUS_ORDER, digits=4)
    
    # Save report to file
    report_path = os.path.join(REPORTS_DIR, 'ensemble_evaluation_detailed.txt')
    with open(report_path, 'w') as f:
        f.write("ENSEMBLE EVALUATION REPORT\n")
        f.write(f"Champion Strategy: {strategy}\n")
        f.write("=" * 30 + "\n")
        f.write(f"Accuracy: {acc:.2f}%\n")
        f.write(f"Precision (Macro): {(precision*100):.2f}%\n")
        f.write(f"Recall (Macro): {(recall*100):.2f}%\n")
        f.write(f"F1-Score (Macro): {(f1*100):.2f}%\n")
        f.write(f"AUC-ROC (Macro): {auc_roc_macro:.4f}\n\n")
        f.write("Detailed Per-Class Performance:\n")
        f.write(full_report)

    print(f"\nSaved detailed report to: {report_path}")

    # 5. ROC Curve Visualization
    print("Generating ROC Curve plot...")
    plt.figure(figsize=(10, 8))
    
    colors = ['red', 'orange', 'blue', 'green', 'magenta']
    for i in range(N_CLASSES):
        fpr, tpr, _ = roc_curve(y_true_bin[:, i], y_prob[:, i])
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, color=colors[i], lw=2,
                 label=f'{STATUS_ORDER[i]} (AUC = {roc_auc:.4f})')

    plt.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Ensemble Multi-Class ROC Curves (One-vs-Rest)')
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    
    roc_plot_path = os.path.join(REPORTS_DIR, 'ensemble_roc_curve.png')
    plt.savefig(roc_plot_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"Saved ROC curve plot to: {roc_plot_path}")

    print("\nEvaluation complete.")

if __name__ == '__main__':
    main()
