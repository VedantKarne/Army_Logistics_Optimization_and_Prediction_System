"""
============================================================
STEP 4: optimize_ensemble.py
============================================================
Builds the final Delphi-style ensemble from OOF predictions:

  1. Stacked meta-learner: LogisticRegression trained on
     (5000 × 20) OOF matrix [4 models × 5 classes].

  2. Temperature scaling calibration for XGBoost, LightGBM,
     and TabNet.

  3. Bayesian weight backup (Optuna, 50 trials, Macro F1):
     finds optimal w_xgb, w_lgbm, w_tabnet.
     Stored as fallback if meta-learner overfits.

Outputs (saved to models/):
  meta_learner.pkl
  temperature_scalars.json       ← {model: T}
  ensemble_weights.json          ← Bayesian weight backup
  model_contribution_weights.png ← meta-learner coefficient plot
============================================================
"""

import os
import json
import pickle
import warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings('ignore')

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import f1_score
from scipy.optimize import minimize_scalar

# ── Paths ────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(BASE_DIR, 'models')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

STATUS_ORDER = ['Critical', 'Poor', 'Attention', 'Good', 'Excellent']
N_TRIALS     = 300
RANDOM_SEED  = 42


# -----------------------------------------------------------
# LOAD OOF PREDICTIONS
# -----------------------------------------------------------
def load_oof():
    print("Loading OOF predictions...")
    oof_xgb    = np.load(os.path.join(MODELS_DIR, 'oof_xgb.npy'))
    oof_lgbm   = np.load(os.path.join(MODELS_DIR, 'oof_lgbm.npy'))
    oof_tabnet = np.load(os.path.join(MODELS_DIR, 'oof_tabnet.npy'))

    with open(os.path.join(MODELS_DIR, 'label_encoder.pkl'), 'rb') as f:
        le = pickle.load(f)

    import pandas as pd
    import pyarrow  # noqa — just verify parquet dep
    df    = pd.read_parquet(os.path.join(BASE_DIR, 'vehicle_features.parquet'))
    y     = le.transform(df['vehicle_status'].values)

    print(f"  OOF shapes: XGB={oof_xgb.shape}, LGBM={oof_lgbm.shape}, "
          f"TabNet={oof_tabnet.shape}")
    return oof_xgb, oof_lgbm, oof_tabnet, y, le


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEMPERATURE SCALING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def temperature_scale(probs: np.ndarray, T: float) -> np.ndarray:
    """Apply temperature scaling to probability matrix."""
    log_p = np.log(probs.clip(1e-10))
    scaled = log_p / T
    # Softmax
    exp_s  = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return exp_s / exp_s.sum(axis=1, keepdims=True)


def find_temperature(probs: np.ndarray, y: np.ndarray) -> float:
    """Find T that minimises NLL on OOF predictions."""
    def nll(T):
        p_cal = temperature_scale(probs, max(T, 0.01))
        p_true = p_cal[np.arange(len(y)), y]
        return -np.mean(np.log(p_true.clip(1e-10)))

    result = minimize_scalar(nll, bounds=(0.1, 10.0), method='bounded')
    return float(result.x)


def calibrate_models(oof_xgb, oof_lgbm, oof_tabnet, y):
    print("\n[1/3] Temperature scaling calibration...")
    temp_scalars = {}

    for name, oof in [('xgb', oof_xgb), ('lgbm', oof_lgbm), ('tabnet', oof_tabnet)]:
        T = find_temperature(oof, y)
        temp_scalars[name] = T
        print(f"  {name:8} → T = {T:.4f}")

    # TabPFN is already calibrated — set T=1.0
    # temp_scalars['tabpfn'] = 1.0
    # print(f"  tabpfn   → T = 1.0 (pre-calibrated by design)")

    with open(os.path.join(MODELS_DIR, 'temperature_scalars.json'), 'w') as f:
        json.dump(temp_scalars, f, indent=2)
    print("  Saved → models/temperature_scalars.json")
    return temp_scalars


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STACKED META-LEARNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def train_meta_learner(oof_xgb, oof_lgbm, oof_tabnet,
                       temp_scalars, y):
    print("\n[2/3] Stacked meta-learner training...")

    # Apply temperature calibration to each OOF
    cal_xgb    = temperature_scale(oof_xgb,    temp_scalars['xgb'])
    cal_lgbm   = temperature_scale(oof_lgbm,   temp_scalars['lgbm'])
    cal_tabnet = temperature_scale(oof_tabnet,  temp_scalars['tabnet'])
    # Stack OOF: (5000, 15)
    meta_X = np.hstack([cal_xgb, cal_lgbm, cal_tabnet])
    print(f"  Meta-feature matrix shape: {meta_X.shape}")

    # Cross-validate meta-learner to verify it adds value
    skf    = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    meta   = LogisticRegression(C=0.5, max_iter=2000, multi_class='multinomial',
                                 random_state=RANDOM_SEED)
    scores = cross_val_score(meta, meta_X, y, cv=skf, scoring='f1_macro')
    print(f"  Meta-learner 5-fold Macro F1: {scores.mean():.4f} ± {scores.std():.4f}")

    # Train final meta-learner on all OOF data
    meta.fit(meta_X, y)

    with open(os.path.join(MODELS_DIR, 'meta_learner.pkl'), 'wb') as f:
        pickle.dump(meta, f)
    print("  Saved → models/meta_learner.pkl")

    # Model contribution plot from meta-learner coefficients
    _plot_model_contributions(meta)

    return meta


def _plot_model_contributions(meta):
    """Plot meta-learner coefficients showing each model's contribution per class."""
    coefs  = meta.coef_   # (n_classes, 15)
    models = ['XGBoost'] * 5 + ['LightGBM'] * 5 + ['TabNet'] * 5
    labels = STATUS_ORDER * 3
    x      = np.arange(15)

    fig, axes = plt.subplots(1, len(STATUS_ORDER), figsize=(20, 5), sharey=False)
    colors = {'XGBoost': '#2196F3', 'LightGBM': '#4CAF50',
              'TabNet': '#FF9800'}

    for cls_idx, ax in enumerate(axes):
        bar_colors = [colors[m] for m in models]
        ax.bar(x, coefs[cls_idx], color=bar_colors)
        ax.set_title(STATUS_ORDER[cls_idx])
        ax.set_xticks([2, 7, 12])
        ax.set_xticklabels(['XGB', 'LGBM', 'TabNet'])
        ax.axhline(0, color='black', linewidth=0.8)

    axes[0].set_ylabel('Meta-learner coefficient')
    plt.suptitle('Model Contribution Weights per Class', fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'model_contribution_weights.png'),
                dpi=120, bbox_inches='tight')
    plt.close()
    print("  Saved → reports/model_contribution_weights.png")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BAYESIAN WEIGHT BACKUP (Optuna, 50 trials)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def bayesian_weight_search(oof_xgb, oof_lgbm, oof_tabnet,
                            temp_scalars, y):
    print("\n[3/3] Bayesian ensemble weight search (50 trials)...")

    cal_xgb    = temperature_scale(oof_xgb,    temp_scalars['xgb'])
    cal_lgbm   = temperature_scale(oof_lgbm,   temp_scalars['lgbm'])
    cal_tabnet = temperature_scale(oof_tabnet,  temp_scalars['tabnet'])

    def objective(trial):
        w_xgb    = trial.suggest_float('w_xgb',    0.0, 1.0)
        w_lgbm   = trial.suggest_float('w_lgbm',   0.0, 1.0)
        w_tabnet = trial.suggest_float('w_tabnet',  0.0, 1.0)

        total = w_xgb + w_lgbm + w_tabnet
        if total < 1e-8:
            return 0.0

        # Normalise weights to sum to 1
        w_xgb /= total; w_lgbm /= total; w_tabnet /= total

        blended = (w_xgb    * cal_xgb   +
                   w_lgbm   * cal_lgbm  +
                   w_tabnet * cal_tabnet)
        y_pred = blended.argmax(axis=1)
        return f1_score(y, y_pred, average='macro')

    study = optuna.create_study(direction='maximize',
                                 sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED))
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

    best = study.best_params
    total = sum(best.values())
    weights = {k: round(v / total, 4) for k, v in best.items()}
    print(f"\n  Best Macro F1 (weighted blend): {study.best_value:.4f}")
    print(f"  Weights: {weights}")

    with open(os.path.join(MODELS_DIR, 'ensemble_weights.json'), 'w') as f:
        json.dump(weights, f, indent=2)
    print("  Saved → models/ensemble_weights.json")
    return weights


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENSEMBLE TOURNAMENT (THE "CHAMPION" SELECTION)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_tournament(oof_xgb, oof_lgbm, oof_tabnet, y, 
                   temp_scalars, meta_logistic, bayesian_weights):
    print("\n" + "="*60)
    print("ENSEMBLE TOURNAMENT: FINDING THE CHAMPION")
    print("="*60)

    cal_xgb    = temperature_scale(oof_xgb,    temp_scalars['xgb'])
    cal_lgbm   = temperature_scale(oof_lgbm,   temp_scalars['lgbm'])
    cal_tabnet = temperature_scale(oof_tabnet,  temp_scalars['tabnet'])
    # Stack OOF: (5000, 15)
    meta_X = np.hstack([cal_xgb, cal_lgbm, cal_tabnet])

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    leaderboard = {}

    # 1. SIMPLE AVERAGE (BASELINE)
    print("Evaluating Strategy: Simple Average...")
    simple_blend = (cal_xgb + cal_lgbm + cal_tabnet) / 3.0
    f1_simple = f1_score(y, simple_blend.argmax(axis=1), average='macro')
    leaderboard['Simple Average'] = f1_simple

    # 2. BAYESIAN WEIGHTED BLEND
    print("Evaluating Strategy: Bayesian Weighted Blend...")
    w = bayesian_weights
    weighted_blend = (w['w_xgb'] * cal_xgb + w['w_lgbm'] * cal_lgbm + w['w_tabnet'] * cal_tabnet)
    f1_weighted = f1_score(y, weighted_blend.argmax(axis=1), average='macro')
    leaderboard['Weighted Bayesian Blend'] = f1_weighted

    # 3. LINEAR STACKING (LOGISTIC REGRESSION)
    print("Evaluating Strategy: Linear Stacking (Logistic)...")
    scores_log = cross_val_score(meta_logistic, meta_X, y, cv=skf, scoring='f1_macro')
    leaderboard['Linear Stacking (Logistic)'] = np.mean(scores_log)

    # 4. NON-LINEAR STACKING (RANDOM FOREST)
    print("Evaluating Strategy: Non-linear Stacking (RF)...")
    meta_rf = RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=10,
                                      random_state=RANDOM_SEED)
    scores_rf = cross_val_score(meta_rf, meta_X, y, cv=skf, scoring='f1_macro')
    leaderboard['Non-linear Stacking (RF)'] = np.mean(scores_rf)
    
    # Train final RF meta-learner
    meta_rf.fit(meta_X, y)
    with open(os.path.join(MODELS_DIR, 'meta_learner_rf.pkl'), 'wb') as f:
        pickle.dump(meta_rf, f)

    # IDENTIFY CHAMPION
    champion_name = max(leaderboard, key=leaderboard.get)
    champion_score = leaderboard[champion_name]

    print("\n" + "-"*40)
    print(f"{'Strategy':30} | {'Macro F1':>10}")
    print("-"*40)
    for name, score in sorted(leaderboard.items(), key=lambda x: x[1], reverse=True):
        marker = " [CHAMPION]" if name == champion_name else ""
        print(f"{name:30} | {score:10.4f}{marker}")
    print("-"*40)

    # SAVE TOURNAMENT CONFIG
    config = {
        'champion_strategy': champion_name,
        'champion_f1': float(champion_score),
        'weighted_blend_params': bayesian_weights,
        'leaderboard': {k: float(v) for k, v in leaderboard.items()}
    }
    
    config_path = os.path.join(MODELS_DIR, 'ensemble_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"APPOINTED CHAMPION: {champion_name}")
    print(f"Tournament config saved → models/ensemble_config.json")
    return champion_name


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    print("=" * 60)
    print("ENSEMBLE OPTIMIZATION")
    print("Meta-learner + Temperature Calibration + Bayesian Weights")
    print("=" * 60)

    oof_xgb, oof_lgbm, oof_tabnet, y, le = load_oof()
    temp_scalars = calibrate_models(oof_xgb, oof_lgbm, oof_tabnet, y)
    meta         = train_meta_learner(oof_xgb, oof_lgbm, oof_tabnet,
                                      temp_scalars, y)
    weights      = bayesian_weight_search(oof_xgb, oof_lgbm, oof_tabnet,
                                          temp_scalars, y)
    
    # NEW: Run Tournament Phase
    run_tournament(oof_xgb, oof_lgbm, oof_tabnet, y, 
                   temp_scalars, meta, weights)

    print("\n" + "=" * 60)
    print("Ensemble optimized with Tournament Selection.")
    print("Run run_inference.py next.")
    print("=" * 60)


if __name__ == '__main__':
    main()
