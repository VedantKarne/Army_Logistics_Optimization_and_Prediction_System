"""
============================================================
STEP 2: feature_engineering.py
============================================================
Aggregates raw DB data into one feature vector per vehicle.

Feature groups:
  - Telemetry: all-time aggregates + multi-scale rolling (7d/30d/90d)
               + percentile extremes + interaction features
               + degradation velocity
  - Fuel:      efficiency stats + degradation slope
  - Ops:       mission/terrain/stress aggregates
  - DTC:       count-based signals per severity
  - Vehicle:   age, mileage rate, type (one-hot)

Output: vehicle_features.parquet  (5000 rows × ~45 features)
============================================================
"""

import mysql.connector
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from datetime import datetime
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# ── DB Config ────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'military_vehicle_health',
    'user':     'root',
    'password': 'vedant@14',
    'charset':  'utf8mb4',
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)


# ── Helper: linear slope of a series vs. time ────────────────
def compute_slope(series: pd.Series) -> float:
    """Returns linear regression slope (rate of change). 0 if <2 points."""
    vals = series.dropna().values
    if len(vals) < 2:
        return 0.0
    X = np.arange(len(vals)).reshape(-1, 1)
    return LinearRegression().fit(X, vals).coef_[0]


# ── 1. Telemetry features ─────────────────────────────────────
def compute_telemetry_features(conn) -> pd.DataFrame:
    print("  Loading telemetry data (may take a moment)...")
    query = """
        SELECT vehicle_id, timestamp,
               engine_coolant_temp_celsius  AS coolant,
               engine_oil_temp_celsius      AS oil_temp,
               battery_voltage              AS voltage,
               engine_rpm                  AS rpm,
               engine_load_percent         AS load_pct,
               fuel_consumption_lph        AS fuel_lph,
               idle_time_minutes           AS idle_min,
               current_speed_kmph          AS speed
        FROM telemetry_data
        ORDER BY vehicle_id, timestamp
    """
    tel = pd.read_sql(query, conn, parse_dates=['timestamp'])
    tel['date'] = tel['timestamp'].dt.date
    tel['date'] = pd.to_datetime(tel['date'])

    print(f"    Loaded {len(tel):,} telemetry rows for "
          f"{tel['vehicle_id'].nunique():,} vehicles.")

    # --- All-time aggregates per vehicle ---
    agg = tel.groupby('vehicle_id').agg(
        avg_coolant_temp  = ('coolant',  'mean'),
        max_coolant_temp  = ('coolant',  'max'),
        std_coolant_temp  = ('coolant',  'std'),
        overheat_count    = ('coolant',  lambda x: (x > 105).sum()),
        avg_voltage       = ('voltage',  'mean'),
        min_voltage       = ('voltage',  'min'),
        voltage_drop_count= ('voltage',  lambda x: (x < 12.0).sum()),
        avg_rpm           = ('rpm',      'mean'),
        avg_engine_load   = ('load_pct', 'mean'),
        high_load_count   = ('load_pct', lambda x: (x > 80).sum()),
        avg_fuel_lph      = ('fuel_lph', 'mean'),
        total_idle_min    = ('idle_min', 'sum'),
        total_speed_obs   = ('speed',    'count'),
        avg_speed         = ('speed',    'mean'),
        # 95th percentile extremes
        p95_coolant       = ('coolant',  lambda x: x.quantile(0.95)),
        p95_load          = ('load_pct', lambda x: x.quantile(0.95)),
        p05_voltage       = ('voltage',  lambda x: x.quantile(0.05)),
    ).reset_index()

    # Idle ratio
    tel['is_running']      = tel['speed'] > 0
    running = tel.groupby('vehicle_id')['is_running'].sum().reset_index(name='running_obs')
    agg = agg.merge(running, on='vehicle_id', how='left')
    agg['idle_ratio'] = 1 - (agg['running_obs'] / agg['total_speed_obs'].clip(lower=1))

    # --- Interaction features ---
    agg['thermal_stress_index'] = agg['avg_coolant_temp'] * agg['avg_engine_load'] / 100.0
    agg['elec_thermal_risk']    = agg['voltage_drop_count'] * agg['overheat_count']

    # --- Rolling windows (last 7 / 30 / 90 days) ---
    print("    Computing rolling window features...")
    today = tel['date'].max()

    def rolling_stats(days):
        cutoff = today - pd.Timedelta(days=days)
        sub    = tel[tel['date'] >= cutoff]
        r = sub.groupby('vehicle_id').agg(
            coolant_mean  = ('coolant',  'mean'),
            voltage_drops = ('voltage',  lambda x: (x < 12.0).sum()),
            load_mean     = ('load_pct', 'mean'),
            fuel_mean     = ('fuel_lph', 'mean'),
        ).reset_index()
        r.columns = ['vehicle_id'] + [f'r{days}d_{c}' for c in r.columns[1:]]
        return r

    for days in [7, 30, 90]:
        agg = agg.merge(rolling_stats(days), on='vehicle_id', how='left')

    # --- Degradation velocity: temp trend (90d mean − 7d mean) ---
    agg['temp_trend'] = agg['r90d_coolant_mean'] - agg['r7d_coolant_mean']

    # --- Fuel consumption slope (velocity) via weekly aggregation ---
    print("    Computing fuel consumption slope...")
    tel['week'] = tel['timestamp'].dt.to_period('W')
    weekly_fuel = (tel.groupby(['vehicle_id', 'week'])['fuel_lph']
                   .mean()
                   .reset_index())

    slopes = (weekly_fuel.groupby('vehicle_id')['fuel_lph']
              .apply(compute_slope)
              .reset_index(name='fuel_slope'))
    agg = agg.merge(slopes, on='vehicle_id', how='left')

    agg.drop(columns=['running_obs', 'total_speed_obs'], inplace=True)
    return agg


# ── 2. Fuel features ─────────────────────────────────────────
def compute_fuel_features(conn) -> pd.DataFrame:
    print("  Loading fuel records...")
    query = """
        SELECT vehicle_id, refuel_date, fuel_efficiency_kmpl
        FROM   fuel_records
        WHERE  fuel_efficiency_kmpl IS NOT NULL
        ORDER BY vehicle_id, refuel_date
    """
    fuel = pd.read_sql(query, conn, parse_dates=['refuel_date'])
    print(f"    Loaded {len(fuel):,} fuel records.")

    agg = fuel.groupby('vehicle_id').agg(
        avg_efficiency   = ('fuel_efficiency_kmpl', 'mean'),
        min_efficiency   = ('fuel_efficiency_kmpl', 'min'),
        max_efficiency   = ('fuel_efficiency_kmpl', 'max'),
        total_refuels    = ('fuel_efficiency_kmpl', 'count'),
    ).reset_index()

    # Efficiency degradation: first vs. last recorded efficiency
    first_last = fuel.groupby('vehicle_id').agg(
        first_eff = ('fuel_efficiency_kmpl', 'first'),
        last_eff  = ('fuel_efficiency_kmpl', 'last'),
    ).reset_index()
    first_last['efficiency_degradation'] = first_last['first_eff'] - first_last['last_eff']

    # Efficiency slope over time
    slopes = (fuel.groupby('vehicle_id')['fuel_efficiency_kmpl']
              .apply(compute_slope)
              .reset_index(name='efficiency_slope'))

    agg = agg.merge(first_last[['vehicle_id', 'efficiency_degradation']], on='vehicle_id', how='left')
    agg = agg.merge(slopes, on='vehicle_id', how='left')
    return agg


# ── 3. Operational features ──────────────────────────────────
def compute_ops_features(conn) -> pd.DataFrame:
    print("  Loading operational logs...")
    query = """
        SELECT vehicle_id, mission_type, terrain_difficulty_score,
               cargo_weight_kg, harsh_braking_count, harsh_acceleration_count,
               trip_distance_km, fuel_consumed_liters
        FROM   operational_logs
    """
    ops = pd.read_sql(query, conn)
    print(f"    Loaded {len(ops):,} operational records.")

    agg = ops.groupby('vehicle_id').agg(
        total_trips          = ('trip_distance_km',   'count'),
        avg_trip_distance    = ('trip_distance_km',   'mean'),
        avg_terrain_diff     = ('terrain_difficulty_score', 'mean'),
        avg_cargo_weight     = ('cargo_weight_kg',    'mean'),
        total_harsh_events   = ('harsh_braking_count', 'sum'),
    ).reset_index()

    # Combat mission ratio
    combat = (ops[ops['mission_type'] == 'combat']
              .groupby('vehicle_id').size()
              .reset_index(name='combat_trips'))
    agg = agg.merge(combat, on='vehicle_id', how='left')
    agg['combat_ratio'] = agg['combat_trips'] / agg['total_trips'].clip(lower=1)
    agg['abuse_rate']   = agg['total_harsh_events'] / agg['total_trips'].clip(lower=1)
    agg.drop(columns=['combat_trips'], inplace=True)
    return agg


# ── 4. DTC features ──────────────────────────────────────────
def compute_dtc_features(conn) -> pd.DataFrame:
    print("  Loading DTC counts...")
    query = """
        SELECT vehicle_id,
               COUNT(*) AS dtc_total,
               SUM(severity='critical') AS dtc_critical,
               SUM(severity='major')    AS dtc_major,
               SUM(severity='minor')    AS dtc_minor,
               SUM(is_active=1)         AS dtc_active
        FROM   diagnostic_codes
        GROUP BY vehicle_id
    """
    dtc = pd.read_sql(query, conn)
    print(f"    Loaded DTC aggregates for {len(dtc):,} vehicles.")
    return dtc


# ── 5. Vehicle meta features ──────────────────────────────────
def compute_vehicle_features(conn) -> pd.DataFrame:
    print("  Loading vehicle metadata...")
    query = """
        SELECT v.vehicle_id, v.vehicle_type, v.acquisition_date,
               MAX(t.odometer_km) AS total_mileage,
               MAX(t.engine_hours) AS total_engine_hours
        FROM   vehicles v
        LEFT   JOIN telemetry_data t ON v.vehicle_id = t.vehicle_id
        GROUP BY v.vehicle_id, v.vehicle_type, v.acquisition_date
    """
    veh = pd.read_sql(query, conn, parse_dates=['acquisition_date'])
    today = pd.Timestamp(datetime.now().date())
    veh['vehicle_age_years'] = ((today - veh['acquisition_date']).dt.days / 365.25)
    veh['mileage_per_year']  = veh['total_mileage'] / veh['vehicle_age_years'].clip(lower=0.1)

    # One-hot encode vehicle_type
    veh = pd.get_dummies(veh, columns=['vehicle_type'], prefix='vtype', drop_first=False)
    veh.drop(columns=['acquisition_date'], inplace=True)
    return veh


# ── 6. Labels ─────────────────────────────────────────────────
def load_labels(conn) -> pd.DataFrame:
    print("  Loading vehicle_status labels...")
    query = """
        SELECT vehicle_id, vehicle_status
        FROM   maintenance_records
        WHERE  vehicle_status IS NOT NULL
    """
    labels = pd.read_sql(query, conn)
    # One record per vehicle — deduplicate just in case
    labels = labels.drop_duplicates(subset='vehicle_id', keep='last')
    print(f"    Loaded {len(labels):,} labeled vehicles.")
    return labels


# ── 7. Neural Network Enhancements ────────────────────────────
class Autoencoder(nn.Module):
    def __init__(self, input_dim, latent_dim):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.1),  # Added for MC Dropout
            nn.Linear(32, latent_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.1),  # Added for MC Dropout
            nn.Linear(32, input_dim)
        )

    def forward(self, x):
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return latent, reconstructed

class FeatureScorerNN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(FeatureScorerNN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim)
        )

    def forward(self, x):
        return self.net(x)

class NeuralFeatureEnhancer:
    def __init__(self, latent_dim=8, epochs=50, batch_size=64):
        self.latent_dim = latent_dim
        self.epochs     = epochs
        self.batch_size = batch_size
        self.scaler     = StandardScaler()
        self.le         = LabelEncoder()
        self.device     = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.status_order = ['Critical', 'Poor', 'Attention', 'Good', 'Excellent']

    def enhance(self, df: pd.DataFrame) -> pd.DataFrame:
        print("\n[Neural Enhancement] Starting Smart Correlation analysis...")
        
        # Prepare data
        drop_cols = ['vehicle_id', 'vehicle_status']
        feature_cols = [c for c in df.columns if c not in drop_cols]
        X_raw = df[feature_cols].values.astype(np.float32)
        
        # Encode labels (using specific order to maintain consistency)
        self.le.classes_ = np.array(self.status_order)
        y = self.le.transform(df['vehicle_status'])
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_raw)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(y, dtype=torch.long).to(self.device)
        
        # 1. Train Autoencoder for Latent Health Embeddings
        print(f"  Training Autoencoder (latent_dim={self.latent_dim})...")
        ae = Autoencoder(X_scaled.shape[1], self.latent_dim).to(self.device)
        optimizer = optim.Adam(ae.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        dataset = TensorDataset(X_tensor)
        loader  = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        ae.train()
        for epoch in range(self.epochs):
            for batch in loader:
                x_b = batch[0]
                _, rec = ae(x_b)
                loss = criterion(rec, x_b)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        
        ae.eval()
        with torch.no_grad():
            latent_feats, _ = ae(X_tensor)
            latent_feats = latent_feats.cpu().numpy()
        
        # Add latent features to DF
        for i in range(self.latent_dim):
            df[f'latent_{i}'] = latent_feats[:, i]
            
        # 2. Neural Correlation Scoring (Importance)
        print("  Computing Neural Correlation Scores (MLP Importance)...")
        scorer = FeatureScorerNN(X_scaled.shape[1], len(self.status_order)).to(self.device)
        optimizer = optim.Adam(scorer.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        dataset = TensorDataset(X_tensor, y_tensor)
        loader  = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        scorer.train()
        for epoch in range(self.epochs):
            for x_b, y_b in loader:
                out = scorer(x_b)
                loss = criterion(out, y_b)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        
        # Gradient-based Saliency for Smart Correlation
        scorer.eval()
        X_tensor.requires_grad = True
        outputs = scorer(X_tensor)
        
        # Sum of absolute gradients across all classes/samples
        importance = torch.zeros(X_scaled.shape[1]).to(self.device)
        for i in range(len(self.status_order)):
            score = outputs[:, i].sum()
            scorer.zero_grad()
            score.backward(retain_graph=True)
            importance += X_tensor.grad.abs().sum(dim=0)
            X_tensor.grad.zero_()
        
        importance_scores = importance.cpu().detach().numpy()
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'neural_importance': importance_scores
        }).sort_values('neural_importance', ascending=False)
        
        # Save Neural Correlation Report
        rep_path = os.path.join(OUTPUT_DIR, 'reports', 'neural_correlation.csv')
        os.makedirs(os.path.dirname(rep_path), exist_ok=True)
        importance_df.to_csv(rep_path, index=False)
        print(f"    Neural Correlation Report saved → {rep_path}")
        
        # 3. Deep Feature Interactions (Layer 1 activations)
        # We take a few high-variance activations from the first layer as "Neural Interaction Features"
        with torch.no_grad():
            interactions = nn.Sequential(*list(scorer.net.children())[:2])(X_tensor).cpu().numpy()
            # Pick top 4 interactions by variance
            variances = np.var(interactions, axis=0)
            top_idx = np.argsort(variances)[-4:]
            for i, idx in enumerate(top_idx):
                df[f'neural_interaction_{i}'] = interactions[:, idx]
        
        # 4. Uncertainty Estimation via MC Dropout (stochastic forward passes)
        print("  Estimating prediction uncertainty (MC Dropout)...")
        n_passes = 30
        scorer.train()  # Keep dropout active!
        all_preds = []
        with torch.no_grad():
            for _ in range(n_passes):
                out = torch.softmax(scorer(X_tensor), dim=1)
                all_preds.append(out.cpu().numpy())
        
        preds_stack = np.stack(all_preds)  # (n_passes, n_samples, n_classes)
        uncertainty = np.std(preds_stack, axis=0).mean(axis=1)  # Mean std across classes
        df['neural_uncertainty'] = uncertainty

        print(f"  Added {self.latent_dim} latent features, 4 interaction features, and uncertainty score.")
        return df


# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("FEATURE ENGINEERING")
    print("=" * 60)

    conn = get_conn()

    print("\n[1/6] Telemetry features...")
    tel_feat = compute_telemetry_features(conn)

    print("\n[2/6] Fuel features...")
    fuel_feat = compute_fuel_features(conn)

    print("\n[3/6] Operational features...")
    ops_feat = compute_ops_features(conn)

    print("\n[4/6] DTC features...")
    dtc_feat = compute_dtc_features(conn)

    print("\n[5/6] Vehicle meta features...")
    veh_feat = compute_vehicle_features(conn)

    print("\n[6/6] Labels...")
    labels = load_labels(conn)
    conn.close()

    # ── Merge all ─────────────────────────────────────────────
    print("\nMerging feature groups...")
    df = veh_feat.copy()
    for feat_df in [tel_feat, fuel_feat, ops_feat, dtc_feat, labels]:
        df = df.merge(feat_df, on='vehicle_id', how='left')

    # ── Fill NaN with 0 (vehicles with no DTC / fuel / ops records) ──
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # ── Neural Enhancement ────────────────────────────────────
    enhancer = NeuralFeatureEnhancer(latent_dim=10, epochs=30)
    df = enhancer.enhance(df)

    # ── Drop rows with no label ───────────────────────────────
    before = len(df)
    df = df[df['vehicle_status'].notna()].copy()
    print(f"\n  Removed {before - len(df)} unlabeled vehicles. "
          f"Final: {len(df):,} vehicles × {len(df.columns)} columns.")

    # ── Save ─────────────────────────────────────────────────
    out_path = os.path.join(OUTPUT_DIR, 'vehicle_features.parquet')
    df.to_parquet(out_path, index=False)
    print(f"\nSaved → {out_path}")

    # ── Quick summary ─────────────────────────────────────────
    print("\n=== FEATURE MATRIX SUMMARY ===")
    print(f"  Shape     : {df.shape}")
    print(f"  Features  : {len(df.columns) - 2} (excl. vehicle_id, vehicle_status)")
    print("\n  Label distribution:")
    vc = df['vehicle_status'].value_counts()
    for status, cnt in vc.items():
        bar = '|' * max(1, cnt // 100)
        print(f"    {status:12} {cnt:5}  {bar}")

    print("\nDone. Run train_health_model.py next.")


if __name__ == '__main__':
    main()
