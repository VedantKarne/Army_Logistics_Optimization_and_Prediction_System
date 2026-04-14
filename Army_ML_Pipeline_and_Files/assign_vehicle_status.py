"""
============================================================
STEP 1: assign_vehicle_status.py
============================================================
Adds `vehicle_status` column to maintenance_records and assigns
5 ordinal class labels derived from ACTUAL OUTCOMES:
    service_type + DTC severity (with temporal decay weighting)

Labels are FULLY INDEPENDENT of the pre_service_health_score formula.

Classes (ordinal):
    Critical   (0) → emergency service OR active critical DTC
    Poor       (1) → corrective + multiple major DTCs
    Attention  (2) → corrective + minor/major DTCs
    Good       (3) → preventive + minor DTCs
    Excellent  (4) → preventive + none/warning DTCs
============================================================
"""

import mysql.connector
import numpy as np
from datetime import datetime, timedelta, date
from collections import defaultdict
import sys, io

# Fix Windows CP1252 console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── DB Config ────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'military_vehicle_health',
    'user':     'root',
    'password': 'vedant@14',
    'charset':  'utf8mb4',
}

SEVERITY_RANK = {'critical': 4, 'major': 3, 'minor': 2, 'warning': 1}
STATUS_ORDER  = ['Critical', 'Poor', 'Attention', 'Good', 'Excellent']


# ── Temporal decay DTC score ─────────────────────────────────
def temporal_severity_score(severity: str,
                             detected_ts,
                             resolved_ts,
                             today: date) -> float:
    """
    DTC severity score decayed by age.
    Active DTCs: 90-day half-life.
    Resolved DTCs: 45-day half-life (decay faster once fixed).
    """
    base_rank = SEVERITY_RANK.get(severity, 0)
    detected_date  = detected_ts.date() if hasattr(detected_ts, 'date') else detected_ts
    resolved_date  = resolved_ts.date() if (resolved_ts and hasattr(resolved_ts, 'date')) else resolved_ts

    if resolved_date:
        days_old = max((today - resolved_date).days, 0)
        decay    = np.exp(-days_old / 45.0)   # resolved: faster decay
    else:
        days_old = max((today - detected_date).days, 0)
        decay    = np.exp(-days_old / 90.0)   # active: slower decay

    return base_rank * decay


# ── Continuous composite health score ────────────────────────
# Lower score = worse health (Critical); higher = better (Excellent)

SVC_TYPE_BASE = {
    'emergency':  0.0,
    'corrective': 0.35,
    'preventive': 0.75,
}

def compute_health_score(service_type: str,
                         temporal_dtc_rank: float,
                         major_dtc_count: int,
                         total_dtc_score: float,
                         recent_corrective_count: int) -> float:
    """
    Continuous health score in [0, 1]. Lower = worse.
    Combines service type, DTC severity, major count, and recency.
    """
    svc_score   = SVC_TYPE_BASE.get(service_type, 0.35)
    dtc_pen     = min(temporal_dtc_rank / 4.0,          1.0) * 0.50
    major_pen   = min(np.log1p(major_dtc_count) / np.log1p(20), 1.0) * 0.30
    total_pen   = min(total_dtc_score / 20.0,            1.0) * 0.20
    recency_pen = min(recent_corrective_count / 6.0,     1.0) * 0.25
    score = svc_score - dtc_pen - major_pen * 0.4 - total_pen * 0.2 - recency_pen * 0.15
    return float(np.clip(score, 0.0, 1.0))


# ── Main ─────────────────────────────────────────────────────
def main():
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    today  = datetime.now().date()

    print("=" * 60)
    print("VEHICLE STATUS LABEL ASSIGNMENT")
    print("Based on: service_type + temporal DTC severity")
    print("=" * 60)

    # 1. Add column
    print("\n[1/5] Adding vehicle_status column to maintenance_records...")
    try:
        cursor.execute(
            "ALTER TABLE maintenance_records "
            "ADD COLUMN vehicle_status VARCHAR(20) DEFAULT NULL"
        )
        conn.commit()
        print("      Column added successfully.")
    except mysql.connector.Error as e:
        if 'Duplicate column' in str(e):
            print("      Column already exists — resetting values.")
            cursor.execute("UPDATE maintenance_records SET vehicle_status = NULL")
            conn.commit()
        else:
            raise

    # 2. Load maintenance records
    print("\n[2/5] Loading maintenance records...")
    cursor.execute("""
        SELECT maintenance_id, vehicle_id, service_date, service_type
        FROM   maintenance_records
        ORDER BY vehicle_id, service_date
    """)
    records = cursor.fetchall()
    print(f"      Loaded {len(records):,} records.")

    # 3. Load all DTC data
    print("\n[3/5] Loading diagnostic codes...")
    cursor.execute("""
        SELECT vehicle_id, severity, detected_timestamp, resolved_timestamp
        FROM   diagnostic_codes
    """)
    dtcs_raw = cursor.fetchall()

    vehicle_dtcs = defaultdict(list)
    for d in dtcs_raw:
        vehicle_dtcs[d['vehicle_id']].append(d)
    print(f"      Loaded {len(dtcs_raw):,} DTC records for "
          f"{len(vehicle_dtcs):,} vehicles.")

    # 4. Compute per-vehicle recency counts (load once)
    print("\n[4/5] Computing recency corrective counts...")
    cursor.execute("""
        SELECT vehicle_id, service_date, service_type
        FROM   maintenance_records
        WHERE  service_type = 'corrective'
        ORDER BY vehicle_id, service_date
    """)
    corrective_records = cursor.fetchall()

    corrective_by_vehicle = defaultdict(list)
    for r in corrective_records:
        sd = r['service_date']
        if hasattr(sd, 'date'):
            sd = sd.date()
        corrective_by_vehicle[r['vehicle_id']].append(sd)

    # 5. Compute health scores, then bucket into quintiles
    print("\n[5/5] Computing health scores and assigning labels...")
    scored = []   # (health_score, maintenance_id)

    for rec in records:
        vid      = rec['vehicle_id']
        svc_type = rec['service_type']
        svc_date = rec['service_date']
        if hasattr(svc_date, 'date'):
            svc_date = svc_date.date()

        dtcs = vehicle_dtcs.get(vid, [])
        max_temporal_rank = 0.0
        total_dtc_score   = 0.0
        major_count       = 0

        for d in dtcs:
            s = temporal_severity_score(
                d['severity'],
                d['detected_timestamp'],
                d['resolved_timestamp'],
                today
            )
            total_dtc_score += s
            if s > max_temporal_rank:
                max_temporal_rank = s
            if d['severity'] == 'major':
                major_count += 1

        cutoff = svc_date - timedelta(days=180)
        recent_corrective = sum(
            1 for sd in corrective_by_vehicle.get(vid, [])
            if cutoff <= sd <= svc_date
        )

        h = compute_health_score(
            svc_type, max_temporal_rank, major_count, total_dtc_score, recent_corrective
        )
        scored.append((h, rec['maintenance_id']))

    # Quintile bucketing by exact index
    # Sort ascending by health_score. Ties are arbitrarily broken by original order.
    scored.sort(key=lambda x: x[0])
    
    n = len(scored)
    updates = []
    for i, (h, mid) in enumerate(scored):
        if i < n * 0.2:
            status = 'Critical'
        elif i < n * 0.4:
            status = 'Poor'
        elif i < n * 0.6:
            status = 'Attention'
        elif i < n * 0.8:
            status = 'Good'
        else:
            status = 'Excellent'
        updates.append((status, mid))

    # Batch update
    cursor.executemany(
        "UPDATE maintenance_records SET vehicle_status=%s WHERE maintenance_id=%s",
        updates
    )
    conn.commit()
    print(f"      Updated {len(updates):,} records.")

    # ── Verification ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("LABEL DISTRIBUTION")
    print("=" * 60)
    cursor.execute("""
        SELECT vehicle_status,
               COUNT(*) AS cnt,
               ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM maintenance_records), 2) AS pct
        FROM   maintenance_records
        GROUP BY vehicle_status
        ORDER BY FIELD(vehicle_status,'Critical','Poor','Attention','Good','Excellent')
    """)
    for row in cursor.fetchall():
        bar = '#' * max(1, int(row['pct'] / 2))
        print(f"  {row['vehicle_status']:12} {row['cnt']:5}  ({row['pct']:5}%)  {bar}")

    cursor.close()
    conn.close()
    print("\nDone. Run feature_engineering.py next.")


if __name__ == '__main__':
    main()
