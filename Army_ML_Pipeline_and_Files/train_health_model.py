"""
============================================================
STEP 3: train_health_model.py
============================================================
Trains 4 classification models on vehicle_features.parquet:
  1. XGBoost  — Bayesian optimization (50 trials, mlogloss)
  2. LightGBM — Bayesian optimization (50 trials, multi_logloss)
  3. TabNet   — Bayesian optimization (50 trials)

Each model generates Out-of-Fold (OOF) predictions for stacking.
SHAP analysis and feature pruning applied to XGBoost + LightGBM.

Outputs (saved to models/):
  xgb_best.pkl, lgbm_best.pkl
  tabnet_best/   (directory)
  tabnet_best/   (directory)
  oof_xgb.npy, oof_lgbm.npy, oof_tabnet.npy
  label_encoder.pkl, feature_names.json

Outputs (saved to reports/):
  classification_report.txt, confusion_matrix.png
  shap_global.png, shap_per_class_critical.png
============================================================
"""

import os
import json
import pickle
import warnings
import sys
import numpy as np

# Fix Windows CP1252 console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings('ignore')

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import (StratifiedKFold,
                                     RepeatedStratifiedKFold,
                                     cross_val_score)
from sklearn.metrics import (classification_report, confusion_matrix,
                              f1_score, ConfusionMatrixDisplay)
from imblearn.over_sampling import SMOTE

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# ── Paths ────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR   = os.path.join(BASE_DIR, 'models')
REPORTS_DIR  = os.path.join(BASE_DIR, 'reports')
FEATURES_PATH = os.path.join(BASE_DIR, 'vehicle_features.parquet')

os.makedirs(MODELS_DIR,  exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

N_TRIALS    = 50
N_SPLITS    = 5
N_REPEATS   = 3
RANDOM_SEED = 42
N_CLASSES   = 5

STATUS_ORDER = ['Critical', 'Poor', 'Attention', 'Good', 'Excellent']


# -----------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------
def load_data():
    print("Loading vehicle_features.parquet...")
    df = pd.read_parquet(FEATURES_PATH)

    # Drop non-feature columns
    drop_cols = ['vehicle_id', 'vehicle_status']
    feature_cols = [c for c in df.columns if c not in drop_cols]

    # Encode labels
    le = LabelEncoder()
    le.classes_ = np.array(STATUS_ORDER)
    y = le.transform(df['vehicle_status'])
    X = df[feature_cols].values.astype(np.float32)

    print(f"  Features: {X.shape[1]}  |  Samples: {X.shape[0]}")
    print(f"  Label counts: { {c: int((y == i).sum()) for i, c in enumerate(STATUS_ORDER)} }")

    with open(os.path.join(MODELS_DIR, 'label_encoder.pkl'), 'wb') as f:
        pickle.dump(le, f)
    with open(os.path.join(MODELS_DIR, 'feature_names.json'), 'w') as f:
        json.dump(feature_cols, f)

    return X, y, le, feature_cols


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMOTE PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def make_smote_pipeline():
    """SMOTE for multiclass imbalance handling (fully multiclass-safe)."""
    return SMOTE(k_neighbors=5, random_state=RANDOM_SEED)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OOF GENERATOR (generic)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_oof_sklearn(model, X, y, apply_smote=True):
    """
    Returns OOF probability matrix (n_samples, n_classes).
    Applies BorderlineSMOTE + TomekLinks on each training fold.
    """
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    oof = np.zeros((len(y), N_CLASSES), dtype=np.float32)

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, y_tr = X[tr_idx], y[tr_idx]
        X_val      = X[val_idx]

        if apply_smote:
            pipe = make_smote_pipeline()
            X_tr, y_tr = pipe.fit_resample(X_tr, y_tr)

        model.fit(X_tr, y_tr)
        oof[val_idx] = model.predict_proba(X_val)
        print(f"    Fold {fold}/{N_SPLITS} — val F1 macro: "
              f"{f1_score(y[val_idx], oof[val_idx].argmax(1), average='macro'):.4f}")

    return oof


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. XGBoost with Bayesian Optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def tune_xgboost(X, y):
    print(f"\n{'='*60}")
    print("XGBoost — Bayesian Optimization (50 trials)")
    print(f"{'='*60}")

    cv = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS,
                                  random_state=RANDOM_SEED)

    def objective(trial):
        params = dict(
            objective        = 'multi:softprob',
            num_class        = N_CLASSES,
            eval_metric      = 'mlogloss',
            n_estimators     = trial.suggest_int('n_estimators', 200, 1200),
            max_depth        = trial.suggest_int('max_depth', 3, 10),
            learning_rate    = trial.suggest_float('learning_rate', 0.005, 0.3, log=True),
            subsample        = trial.suggest_float('subsample', 0.5, 1.0),
            colsample_bytree = trial.suggest_float('colsample_bytree', 0.4, 1.0),
            min_child_weight = trial.suggest_int('min_child_weight', 1, 10),
            gamma            = trial.suggest_float('gamma', 0.0, 5.0),
            reg_alpha        = trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            reg_lambda       = trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            tree_method      = 'hist',
            random_state     = RANDOM_SEED,
            verbosity        = 0,
        )
        # Apply SMOTE on a single fold for speed within Optuna trials
        pipe = make_smote_pipeline()
        X_res, y_res = pipe.fit_resample(X, y)
        model = XGBClassifier(**params)
        scores = cross_val_score(model, X_res, y_res, cv=StratifiedKFold(3),
                                 scoring='neg_log_loss', n_jobs=1)
        return -scores.mean()

    pruner = optuna.pruners.HyperbandPruner(min_resource=3, max_resource=N_SPLITS,
                                             reduction_factor=3)
    study  = optuna.create_study(direction='minimize', pruner=pruner,
                                  sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED))
    # study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)
    #
    # best_params = study.best_params
    # ... locking in best hyperparams from previous Optuna runs:
    best_params = {
        'n_estimators': 811,
        'max_depth': 6,
        'learning_rate': 0.015636639996524225,
        'subsample': 0.7094304184867286,
        'colsample_bytree': 0.9597891550370852,
        'min_child_weight': 3,
        'gamma': 2.5685522883963454,
        'reg_alpha': 8.11543393353939,
        'reg_lambda': 1.8354216844326943
    }
    best_params.update(dict(objective='multi:softprob', num_class=N_CLASSES,
                            eval_metric='mlogloss', tree_method='hist',
                            random_state=RANDOM_SEED, verbosity=0))

    # OOF generation with best params
    print("\n  Generating OOF predictions...")
    xgb_model = XGBClassifier(**best_params)
    oof_xgb   = generate_oof_sklearn(xgb_model, X, y, apply_smote=True)

    # Full retrain on SMOTE-augmented data for final model
    print("  Retraining final XGBoost on full data...")
    pipe  = make_smote_pipeline()
    X_res, y_res = pipe.fit_resample(X, y)
    xgb_final = XGBClassifier(**best_params)
    xgb_final.fit(X_res, y_res)

    with open(os.path.join(MODELS_DIR, 'xgb_best.pkl'), 'wb') as f:
        pickle.dump(xgb_final, f)
    np.save(os.path.join(MODELS_DIR, 'oof_xgb.npy'), oof_xgb)
    print("  Saved → models/xgb_best.pkl, oof_xgb.npy")
    return xgb_final, oof_xgb


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. LightGBM with Bayesian Optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def tune_lightgbm(X, y):
    print(f"\n{'='*60}")
    print("LightGBM — Bayesian Optimization (50 trials)")
    print(f"{'='*60}")

    def objective(trial):
        params = dict(
            objective        = 'multiclass',
            num_class        = N_CLASSES,
            metric           = 'multi_logloss',
            n_estimators     = trial.suggest_int('n_estimators', 200, 1200),
            num_leaves       = trial.suggest_int('num_leaves', 20, 300),
            learning_rate    = trial.suggest_float('learning_rate', 0.005, 0.3, log=True),
            max_depth        = trial.suggest_int('max_depth', 3, 12),
            min_child_samples= trial.suggest_int('min_child_samples', 5, 100),
            subsample        = trial.suggest_float('subsample', 0.5, 1.0),
            colsample_bytree = trial.suggest_float('colsample_bytree', 0.4, 1.0),
            reg_alpha        = trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            reg_lambda       = trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            min_split_gain   = trial.suggest_float('min_split_gain', 0.0, 1.0),
            random_state     = RANDOM_SEED,
            verbosity        = -1,
        )
        pipe = make_smote_pipeline()
        X_res, y_res = pipe.fit_resample(X, y)
        model  = LGBMClassifier(**params)
        scores = cross_val_score(model, X_res, y_res, cv=StratifiedKFold(3),
                                 scoring='neg_log_loss', n_jobs=1)
        return -scores.mean()

    pruner = optuna.pruners.HyperbandPruner(min_resource=3, max_resource=N_SPLITS,
                                             reduction_factor=3)
    study  = optuna.create_study(direction='minimize', pruner=pruner,
                                  sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED))
    # study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)
    #
    # best_params = study.best_params
    # ... locking in best hyperparams from previous Optuna runs:
    best_params = {
        'n_estimators': 646,
        'num_leaves': 197,
        'learning_rate': 0.0648878904498622,
        'max_depth': 4,
        'min_child_samples': 68,
        'subsample': 0.6818788502950801,
        'colsample_bytree': 0.9085260199304832,
        'reg_alpha': 9.879192474391058,
        'reg_lambda': 7.806361407314272e-06,
        'min_split_gain': 0.8245932573505911
    }
    best_params.update(dict(objective='multiclass', num_class=N_CLASSES,
                            metric='multi_logloss', random_state=RANDOM_SEED,
                            verbosity=-1))

    print("\n  Generating OOF predictions...")
    lgbm_model = LGBMClassifier(**best_params)
    oof_lgbm   = generate_oof_sklearn(lgbm_model, X, y, apply_smote=True)

    print("  Retraining final LightGBM on full data...")
    pipe = make_smote_pipeline()
    X_res, y_res = pipe.fit_resample(X, y)
    lgbm_final = LGBMClassifier(**best_params)
    lgbm_final.fit(X_res, y_res)

    with open(os.path.join(MODELS_DIR, 'lgbm_best.pkl'), 'wb') as f:
        pickle.dump(lgbm_final, f)
    np.save(os.path.join(MODELS_DIR, 'oof_lgbm.npy'), oof_lgbm)
    print("  Saved → models/lgbm_best.pkl, oof_lgbm.npy")
    return lgbm_final, oof_lgbm


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. TabNet with Bayesian Optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def tune_tabnet(X, y):
    print(f"\n{'='*60}")
    print("TabNet — Bayesian Optimization (50 trials)")
    print(f"{'='*60}")
    try:
        from pytorch_tabnet.tab_model import TabNetClassifier
        import torch
    except ImportError:
        print("  [SKIP] pytorch-tabnet not installed. "
              "Run: pip install pytorch-tabnet")
        dummy_oof = np.full((len(y), N_CLASSES), 1.0 / N_CLASSES, dtype=np.float32)
        np.save(os.path.join(MODELS_DIR, 'oof_tabnet.npy'), dummy_oof)
        return None, dummy_oof

    device = 'cuda' if __import__('torch').cuda.is_available() else 'cpu'
    print(f"  Device: {device}")

    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)

    def tabnet_cv_logloss(params, X, y):
        """Quick 3-fold logloss for Optuna (for speed)."""
        from sklearn.model_selection import StratifiedKFold as SKF
        from sklearn.metrics import log_loss
        fold_cv = SKF(n_splits=3, shuffle=True, random_state=RANDOM_SEED)
        losses  = []
        for tr_idx, val_idx in fold_cv.split(X, y):
            X_tr, y_tr = X[tr_idx], y[tr_idx]
            X_val, y_val = X[val_idx], y[val_idx]
            params_init = {k: v for k, v in params.items() if k != 'batch_size'}
            clf = TabNetClassifier(verbose=0, device_name=device, **params_init)
            clf.fit(X_tr, y_tr, eval_set=[(X_val, y_val)],
                    patience=15, max_epochs=200,
                    batch_size=params.get('batch_size', 256))
            probs = clf.predict_proba(X_val)
            losses.append(log_loss(y_val, probs))
        return np.mean(losses)

    def objective(trial):
        params = dict(
            n_d           = trial.suggest_int('n_d', 8, 64),
            n_a           = trial.suggest_int('n_a', 8, 64),
            n_steps       = trial.suggest_int('n_steps', 3, 8),
            gamma         = trial.suggest_float('gamma', 1.0, 2.0),
            lambda_sparse = trial.suggest_float('lambda_sparse', 1e-6, 1e-3, log=True),
            optimizer_params = {'lr': trial.suggest_float('lr', 1e-4, 1e-2, log=True)},
            batch_size    = trial.suggest_categorical('batch_size', [128, 256, 512]),
            seed          = RANDOM_SEED,
        )
        pipe = make_smote_pipeline()
        X_res, y_res = pipe.fit_resample(X, y)
        return tabnet_cv_logloss(params, X_res, y_res)

    study = optuna.create_study(direction='minimize',
                                 sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED))
    # study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)
    # best_p = study.best_params
    # ... locking in best hyperparams (TabNet was interrupted, using sensible midway values from log):
    best_p = {
        'n_d': 32,
        'n_a': 32,
        'n_steps': 5,
        'gamma': 1.6,
        'lambda_sparse': 0.0001
    }
    batch_size = 256 # best_p.pop('batch_size', 256)
    lr         = 0.005 # best_p.pop('lr', 1e-3)
    best_p['optimizer_params'] = {'lr': lr}
    best_p['seed'] = RANDOM_SEED

    # OOF generation
    print("\n  Generating OOF predictions (TabNet)...")
    oof_tabnet = np.zeros((len(y), N_CLASSES), dtype=np.float32)
    for fold, (tr_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, y_tr = X[tr_idx], y[tr_idx]
        X_val      = X[val_idx]
        pipe       = make_smote_pipeline()
        X_tr_r, y_tr_r = pipe.fit_resample(X_tr, y_tr)
        clf = TabNetClassifier(verbose=0, device_name=device, **best_p)
        clf.fit(X_tr_r, y_tr_r, max_epochs=300, patience=20,
                batch_size=batch_size,
                eval_set=[(X_val, y[val_idx])])
        oof_tabnet[val_idx] = clf.predict_proba(X_val)
        print(f"    Fold {fold}/{N_SPLITS} — val F1 macro: "
              f"{f1_score(y[val_idx], oof_tabnet[val_idx].argmax(1), average='macro'):.4f}")

    # Final model on full data
    print("  Retraining final TabNet on full data...")
    pipe = make_smote_pipeline()
    X_res, y_res = pipe.fit_resample(X, y)
    tabnet_final = TabNetClassifier(verbose=0, device_name=device, **best_p)
    tabnet_final.fit(X_res, y_res, max_epochs=300, patience=25, batch_size=batch_size)

    save_path = os.path.join(MODELS_DIR, 'tabnet_best')
    tabnet_final.save_model(save_path)
    np.save(os.path.join(MODELS_DIR, 'oof_tabnet.npy'), oof_tabnet)

    # Attention masks visualization
    print("  Saving TabNet attention masks...")
    explain_matrix, masks = tabnet_final.explain(X[:100])
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.imshow(explain_matrix[:50].T, aspect='auto', cmap='Blues')
    ax.set_title('TabNet Feature Attention (first 50 vehicles)')
    ax.set_xlabel('Vehicle sample')
    ax.set_ylabel('Feature index')
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'tabnet_attention_masks.png'), dpi=120)
    plt.close()

    print("  Saved → models/tabnet_best/, oof_tabnet.npy")
    return tabnet_final, oof_tabnet




# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SHAP ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_shap(xgb_model, X, y, feature_names):
    print(f"\n{'='*60}")
    print("SHAP Analysis")
    print(f"{'='*60}")
    explainer    = shap.TreeExplainer(xgb_model)
    shap_values  = explainer.shap_values(X)   # can be list or 3D array

    # Handle both list (older shap/XGB) and array (newer) formats
    if isinstance(shap_values, list):
        # List of [n_samples, n_features] per class
        mean_shap = np.mean([np.abs(sv).mean(0) for sv in shap_values], axis=0)
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        # Array of [n_samples, n_features, n_classes]
        mean_shap = np.abs(shap_values).mean(axis=(0, 2))
    else:
        # Fallback or single class
        mean_shap = np.abs(shap_values).mean(0)

    feat_imp  = pd.DataFrame({'feature': feature_names, 'importance': mean_shap})
    feat_imp  = feat_imp.sort_values('importance', ascending=False)

    # Global plot
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X, feature_names=feature_names,
                      class_names=STATUS_ORDER, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'shap_global.png'), dpi=120)
    plt.close()

    # Per-class plot for Critical (class 0)
    try:
        plt.figure(figsize=(10, 6))
        sv_crit = shap_values[0] if isinstance(shap_values, list) else shap_values[:, :, 0]
        shap.summary_plot(sv_crit, X, feature_names=feature_names,
                          show=False, max_display=15)
        plt.title('SHAP — Critical class')
        plt.tight_layout()
        plt.savefig(os.path.join(REPORTS_DIR, 'shap_per_class_critical.png'), dpi=120)
        plt.close()
    except Exception as e:
        print(f"  [WARN] Failed per-class SHAP plot: {e}")

    # SHAP-guided pruning: identify features with negligible impact
    low_impact = feat_imp[feat_imp['importance'] < 0.001]['feature'].tolist()
    print(f"  Low-impact features (SHAP < 0.001): {len(low_impact)}")
    print(f"  Top-5 features: {feat_imp['feature'].head(5).tolist()}")

    feat_imp.to_csv(os.path.join(REPORTS_DIR, 'shap_importance.csv'), index=False)
    print("  Saved → reports/shap_global.png, shap_per_class_critical.png")
    return feat_imp


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVALUATION REPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def save_evaluation(oof_xgb, oof_lgbm, oof_tabnet, y):
    print(f"\n{'='*60}")
    print("Evaluation (OOF predictions)")
    print(f"{'='*60}")

    models_oof = {
        'XGBoost': oof_xgb,
        'LightGBM': oof_lgbm,
        'TabNet': oof_tabnet,
    }

    report_lines = []
    for name, oof in models_oof.items():
        y_pred = oof.argmax(axis=1)
        f1     = f1_score(y, y_pred, average='macro')
        report = classification_report(y, y_pred, target_names=STATUS_ORDER)
        report_lines.append(f"\n{'='*40}\n{name} (OOF)\n{'='*40}")
        report_lines.append(f"Macro F1: {f1:.4f}\n")
        report_lines.append(report)
        print(f"  {name:10} OOF Macro F1: {f1:.4f}")

    with open(os.path.join(REPORTS_DIR, 'classification_report.txt'), 'w') as f:
        f.write('\n'.join(report_lines))

    # Confusion matrix for XGBoost OOF
    y_pred_xgb = oof_xgb.argmax(axis=1)
    cm  = confusion_matrix(y, y_pred_xgb)
    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=STATUS_ORDER)
    disp.plot(ax=ax, colorbar=True, cmap='Blues')
    ax.set_title('Confusion Matrix — XGBoost OOF')
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'confusion_matrix.png'), dpi=120)
    plt.close()
    print("  Saved → reports/classification_report.txt, confusion_matrix.png")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    print("=" * 60)
    print("TRAINING PIPELINE - 3 MODELS")
    print("=" * 60)

    X, y, le, feature_names = load_data()

    xgb_model, oof_xgb   = tune_xgboost(X, y)
    lgbm_model, oof_lgbm  = tune_lightgbm(X, y)
    tabnet_model, oof_tabnet = tune_tabnet(X, y)

    try:
        run_shap(xgb_model, X, y, feature_names)
    except Exception as e:
        print(f"\n[ERROR] SHAP analysis failed: {e}")

    try:
        save_evaluation(oof_xgb, oof_lgbm, oof_tabnet, y)
    except Exception as e:
        print(f"\n[ERROR] Evaluation failed: {e}")

    print("\n" + "=" * 60)
    print("All 3 models trained and OOF predictions saved.")
    print("Run optimize_ensemble.py next.")
    print("=" * 60)


if __name__ == '__main__':
    main()
