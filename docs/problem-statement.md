# 🎯 Problem Statement & Solution Architecture

## Military Vehicle Inventory Logistics Optimization and Prediction System

---

## The Problem

Modern military fleets run scheduled maintenance intervals — fixed odometer or calendar-based service windows — regardless of actual vehicle condition. This creates two critical failure modes:

| Failure Mode | Consequence |
|---|---|
| **Under-servicing** | A vehicle with degraded sensors, active DTCs, and high operational stress misses its service interval — and fails during a critical mission |
| **Over-servicing** | A vehicle in excellent condition gets pulled for unnecessary maintenance, reducing operational availability |

Additionally, when a fleet vehicle does fail:
- Diagnostic codes exist in the system but are **not algorithmically linked** to maintenance decisions
- Fuel efficiency degradation is tracked per transaction but **never aggregated** to predict imminent failure
- Thermal variance in coolant temperature — an early failure indicator — **goes undetected** until the engine overheats

---

## The Scale

| Metric | Value |
|---|---|
| Fleet size | 5,000 vehicles |
| Vehicle types | 5 (truck, armoured carrier, transport, ambulance, utility) |
| Operational regions | 5 (North, West, South, East, Northeast India) |
| Telemetry frequency | Every 15 minutes per vehicle |
| Maintenance types | Emergency, Corrective, Preventive |
| DTC codes tracked | 15 ISO 15031-compliant fault codes |
| Health assessment frequency | Daily (per inference run) |

---

## The Solution

A **predictive health classification system** that replaces fixed-interval maintenance with data-driven, per-vehicle health assessment.

### Core Capabilities

| Capability | How |
|---|---|
| **5-Class Health Status** | XGBoost + LightGBM + TabNet ensemble classifies each vehicle into Critical / Poor / Attention / Good / Excellent |
| **Uncertainty Quantification** | MC Dropout on a neural autoencoder produces a per-vehicle uncertainty estimate that adjusts confidence scores |
| **Temporal Degradation Detection** | Bi-LSTM processes the last 50 telemetry readings to detect gradual sensor degradation trends |
| **Explainability** | SHAP values per-class explain model decisions; Z-score anomaly detection explains each vehicle's risk evidence |
| **Data-Anchored Scoring** | Health scores (0–100) are calibrated against actual class-mean scores from historical maintenance records |
| **Automated Recommendations** | Plain-language action recommendations (from immediate grounding to routine PM) written to DB per vehicle |

### What Changes Day-to-Day

```
BEFORE (scheduled maintenance):
  Vehicle 1247 → next service in 850 km → no further information

AFTER (ML-driven health prediction):
  Vehicle 1247 → Status: Poor (confidence: 87.3%)
               → Score: 34.2 / 100
               → Risk: HIGH
               → Evidence: High Thermal Stress Index (Z=2.8),
                           Low Min Voltage (Z=-2.1),
                           High DTC Critical Count (Z=1.9)
               → Action: Withdraw from active duty.
                          Plan corrective maintenance within 48 hours.
```

---

## Design Decisions

### Why Weibull Distributions for Label Generation?

During synthetic data generation, failure probabilities for each vehicle component use Weibull CDF:

```
P(failure) = 1 − exp(−(km / scale)^shape)
```

This matches real-world component wear physics — rare early failures (infant mortality), increasing mid-life failure rate, and an upper wear-out bound — rather than a simple linear probability model.

### Why Union Probability for Overall Failure?

```
P(any component fails) = 1 − PROD(1 − P_i)
```

Naive summation of individual probabilities can exceed 1.0 for vehicles with many components. The union formula is statistically exact.

### Why Ensemble over Single Model?

- No single model architecture dominates tabular data across all distributions
- Stacking OOF predictions allows the meta-learner to learn each base model's strengths
- Temperature scaling corrects overconfident probability estimates before stacking
- Tournament selection removes the bias of manually choosing a strategy

### Why SMOTE per fold (not global)?

Applying SMOTE globally before cross-validation splits would cause **data leakage** — synthetic minority samples from training data would contaminate validation folds. Per-fold SMOTE generates synthetic samples only within each training split.

---

> 🔙 [Back to README](../README.md)
