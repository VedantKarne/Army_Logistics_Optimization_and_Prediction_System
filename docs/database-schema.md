# 🗄️ Database Schema Reference

## Military Vehicle Inventory Logistics Optimization and Prediction System

**Database:** `military_vehicle_health`  
**Engine:** MySQL 8.0+ · utf8mb4 · InnoDB  
**Tables:** 9 · **Total Records (synthetic baseline):** ~1.89 million

---

## Entity Relationship Overview

```
vehicles (PK: vehicle_id)
    │
    ├──< telemetry_data         (FK: vehicle_id)   ~740,000 rows
    ├──< maintenance_records    (FK: vehicle_id)   ~5,000–15,000 rows
    ├──< diagnostic_codes       (FK: vehicle_id)   ~8,000–25,000 rows
    ├──< operational_logs       (FK: vehicle_id)   ~15,000–50,000 rows
    ├──< fuel_records           (FK: vehicle_id)   ~10,000–30,000 rows
    └──< health_scores          (FK: vehicle_id)   5,000 rows (1 per vehicle per day)

spare_parts_inventory  (standalone — 500 parts)
users                  (standalone — 50 personnel)
```

---

## Table 1 — `vehicles`

Master fleet registry. One row per vehicle.

| Column | Type | Description |
|---|---|---|
| `vehicle_id` | VARCHAR(20) PK | Unique identifier (e.g. `VH-00001`) |
| `vin` | VARCHAR(17) UNIQUE | Vehicle Identification Number |
| `vehicle_type` | ENUM | `truck / armored_carrier / transport / ambulance / utility` |
| `make` | VARCHAR(50) | Manufacturer (Ashok Leyland, Tata, Mahindra, BharatBenz, Force Motors) |
| `model` | VARCHAR(100) | Model name (e.g. Stallion MK-III, LPT 2523) |
| `year` | YEAR | Manufacturing year |
| `acquisition_date` | DATE | Date inducted into service |
| `engine_type` | VARCHAR(50) | e.g. `Turbo Diesel BS-VI` |
| `fuel_type` | ENUM | `diesel / petrol / cng` |
| `fuel_capacity_litres` | DECIMAL(6,2) | Tank capacity |
| `max_load_kg` | INT | Maximum payload in kg |
| `location` | VARCHAR(100) | Assigned base/station |
| `operational_status` | ENUM | `active / maintenance / decommissioned` |
| `acquisition_cost` | DECIMAL(12,2) | Purchase cost in INR |
| `created_at` | TIMESTAMP | Record creation time |

**Indexes:** PK on `vehicle_id`, INDEX on `(location, operational_status)`

---

## Table 2 — `telemetry_data`

OBD-II sensor readings at 15-minute intervals (2% sampled for performance).

| Column | Type | Description |
|---|---|---|
| `telemetry_id` | BIGINT PK AUTO_INCREMENT | |
| `vehicle_id` | VARCHAR(20) FK | References `vehicles` |
| `timestamp` | DATETIME | Reading timestamp |
| **Engine** | | |
| `engine_coolant_temp_celsius` | DECIMAL(5,2) | Normal: 75–105°C |
| `engine_rpm` | INT | Normal: 700–3500 |
| `engine_load_percent` | DECIMAL(5,2) | 0–100% |
| `engine_hours` | DECIMAL(10,2) | Cumulative engine hours |
| **Drivetrain** | | |
| `current_speed_kmph` | DECIMAL(5,2) | 0–85 km/h |
| `odometer_km` | DECIMAL(10,2) | Cumulative km |
| `gear_position` | TINYINT | 0–6 |
| **Fuel** | | |
| `fuel_level_percent` | DECIMAL(5,2) | 0–100% |
| `fuel_consumption_lph` | DECIMAL(6,3) | Litres per hour |
| **Electrical** | | |
| `battery_voltage` | DECIMAL(5,2) | Normal: 12.2–14.4V |
| `alternator_voltage` | DECIMAL(5,2) | |
| **Other sensors** | | |
| `oil_pressure_psi` | DECIMAL(6,2) | Normal: 25–65 psi |
| `tire_pressure_psi_avg` | DECIMAL(5,2) | Average across 4 tyres |
| `idle_time_minutes` | DECIMAL(6,2) | Idle time in interval |
| **GPS** | | |
| `gps_latitude` | DECIMAL(9,6) | |
| `gps_longitude` | DECIMAL(9,6) | |

**Indexes:** `(vehicle_id, timestamp)` composite — primary query pattern

---

## Table 3 — `maintenance_records`

Full service history with outcome labels added by the ML pipeline.

| Column | Type | Description |
|---|---|---|
| `maintenance_id` | INT PK AUTO_INCREMENT | |
| `vehicle_id` | VARCHAR(20) FK | |
| `service_date` | DATE | |
| `service_type` | ENUM | `emergency / corrective / preventive` |
| `service_category` | VARCHAR(100) | e.g. `Oil Change`, `Brake Service`, `Engine Overhaul` |
| `odometer_at_service` | DECIMAL(10,2) | Km reading at time of service |
| `parts_replaced` | JSON | List of part codes replaced |
| `service_cost` | DECIMAL(10,2) | Cost in INR |
| `technician_id` | INT FK | References `users` |
| `pre_service_health_score` | DECIMAL(5,2) | Health score before service (0–100) |
| `post_service_health_score` | DECIMAL(5,2) | Health score after service (0–100) |
| `next_service_km` | DECIMAL(10,2) | Predicted next service odometer |
| `next_service_date` | DATE | Predicted next service date |
| `vehicle_status` | VARCHAR(20) | **Added by assign_vehicle_status.py** — `Critical/Poor/Attention/Good/Excellent` |

---

## Table 4 — `diagnostic_codes`

ISO 15031-compliant DTC fault records.

| Column | Type | Description |
|---|---|---|
| `dtc_id` | INT PK AUTO_INCREMENT | |
| `vehicle_id` | VARCHAR(20) FK | |
| `code` | VARCHAR(10) | DTC code (e.g. `P0300`, `C0035`) |
| `description` | VARCHAR(255) | Human-readable fault description |
| `severity` | ENUM | `critical / major / minor / warning` |
| `system_affected` | VARCHAR(50) | `Engine / Electrical / Transmission / Brakes / Emissions / Fuel` |
| `detected_timestamp` | DATETIME | When fault was first detected |
| `resolved_timestamp` | DATETIME | When resolved (NULL if still active) |
| `is_active` | BOOLEAN | 1=active, 0=resolved |
| `resolution_notes` | TEXT | Technician notes on resolution |

### DTC Codes in System (15 codes)

| Code | Description | Severity | System |
|---|---|---|---|
| P0300 | Random/Multiple Cylinder Misfire | major | Engine |
| P0171 | System Too Lean Bank 1 | minor | Engine |
| P0420 | Catalyst Efficiency Below Threshold | minor | Emissions |
| P0562 | System Voltage Low | major | Electrical |
| P0715 | Turbine Speed Sensor Malfunction | critical | Transmission |
| P0340 | Camshaft Position Sensor Circuit | critical | Engine |
| P0201 | Fuel Injector Circuit — Cylinder 1 | critical | Engine |
| C0035 | Left Front Wheel Speed Sensor | major | Brakes |
| P0128 | Coolant Temperature Below Thermostat | minor | Engine |
| P0442 | Evaporative Emission System Leak | warning | Emissions |
| P0505 | Idle Control System Malfunction | minor | Engine |
| P0401 | Exhaust Gas Recirculation Insufficient | minor | Emissions |
| P0135 | O2 Sensor Heater Circuit Bank 1 | minor | Engine |
| P0455 | Evaporative Emission System Leak (Large) | warning | Emissions |
| P0113 | Intake Air Temperature Sensor High | warning | Engine |

---

## Table 5 — `operational_logs`

Trip/mission-level operational data.

| Column | Type | Description |
|---|---|---|
| `log_id` | INT PK AUTO_INCREMENT | |
| `vehicle_id` | VARCHAR(20) FK | |
| `trip_start` | DATETIME | |
| `trip_end` | DATETIME | |
| `mission_type` | ENUM | `combat_training / transport / patrol / logistics / medical / maintenance` |
| `terrain_type` | ENUM | `paved / off_road / mixed / sand / mountain` |
| `terrain_difficulty_score` | TINYINT | 1–10 rating |
| `trip_distance_km` | DECIMAL(8,2) | |
| `avg_speed_kmph` | DECIMAL(5,2) | |
| `cargo_weight_kg` | DECIMAL(8,2) | |
| `harsh_braking_count` | INT | |
| `harsh_acceleration_count` | INT | |
| `fuel_consumed_litres` | DECIMAL(8,2) | |
| `driver_id` | INT FK | References `users` |

---

## Table 6 — `fuel_records`

Refuelling transaction log.

| Column | Type | Description |
|---|---|---|
| `fuel_id` | INT PK AUTO_INCREMENT | |
| `vehicle_id` | VARCHAR(20) FK | |
| `refuel_date` | DATE | |
| `litres_filled` | DECIMAL(8,2) | |
| `fuel_cost_inr` | DECIMAL(10,2) | |
| `odometer_at_refuel` | DECIMAL(10,2) | |
| `fuel_efficiency_kmpl` | DECIMAL(6,3) | km/litre since last refuel |
| `station_location` | VARCHAR(100) | |

---

## Table 7 — `health_scores` (ML Output)

Written by `run_inference.py` — one row per vehicle per assessment date.

| Column | Type | Description |
|---|---|---|
| `score_id` | INT PK AUTO_INCREMENT | |
| `vehicle_id` | VARCHAR(20) FK | |
| `assessment_date` | DATE | |
| `overall_health_score` | DECIMAL(5,2) | 0–100 composite score |
| `health_status` | ENUM | `critical / poor / fair / good / excellent` |
| `engine_health_score` | DECIMAL(5,2) | Future use |
| `transmission_health_score` | DECIMAL(5,2) | Future use |
| `brake_system_score` | DECIMAL(5,2) | Future use |
| `electrical_system_score` | DECIMAL(5,2) | Future use |
| `predicted_days_to_service` | INT | RUL in days |
| `predicted_service_date` | DATE | Predicted next service |
| `confidence_level` | DECIMAL(5,2) | Uncertainty-adjusted confidence % |
| `risk_category` | ENUM | `critical / high / medium / low` |
| `recommended_action` | TEXT | Maintenance recommendation |
| `risk_evidence` | TEXT | Top-3 anomalous sensor Z-scores |
| `model_version` | VARCHAR(50) | e.g. `v3.1-Temporal-Fusion` |
| `created_at` | TIMESTAMP | |

---

## Table 8 — `spare_parts_inventory`

500 parts catalogue with stock management.

| Column | Type | Description |
|---|---|---|
| `part_id` | INT PK | |
| `part_number` | VARCHAR(50) UNIQUE | |
| `part_name` | VARCHAR(200) | |
| `category` | VARCHAR(50) | `Engine / Brakes / Electrical / Transmission / Body` |
| `compatible_vehicle_types` | JSON | Which vehicle types use this part |
| `stock_quantity` | INT | Current stock |
| `minimum_stock` | INT | Reorder trigger level |
| `unit_cost_inr` | DECIMAL(10,2) | |
| `supplier_name` | VARCHAR(100) | |
| `lead_time_days` | INT | Delivery lead time |
| `last_restocked` | DATE | |

---

## Table 9 — `users`

50 system personnel with role-based access.

| Column | Type | Description |
|---|---|---|
| `user_id` | INT PK | |
| `username` | VARCHAR(50) UNIQUE | |
| `email` | VARCHAR(100) | Format: `user@military.gov.in` |
| `role` | ENUM | `admin / maintenance_officer / driver / viewer` |
| `rank` | VARCHAR(50) | Indian Army rank |
| `unit` | VARCHAR(100) | Assigned unit/formation |
| `phone` | VARCHAR(15) | |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMP | |

---

## Useful Verification Queries

```sql
-- Row counts across all tables
SELECT 'vehicles'              AS tbl, COUNT(*) AS rows FROM vehicles
UNION SELECT 'telemetry_data',               COUNT(*) FROM telemetry_data
UNION SELECT 'maintenance_records',          COUNT(*) FROM maintenance_records
UNION SELECT 'diagnostic_codes',             COUNT(*) FROM diagnostic_codes
UNION SELECT 'operational_logs',             COUNT(*) FROM operational_logs
UNION SELECT 'fuel_records',                 COUNT(*) FROM fuel_records
UNION SELECT 'health_scores',                COUNT(*) FROM health_scores
UNION SELECT 'spare_parts_inventory',        COUNT(*) FROM spare_parts_inventory
UNION SELECT 'users',                        COUNT(*) FROM users;

-- Check label distribution after assign_vehicle_status.py
SELECT vehicle_status, COUNT(*) AS cnt,
       ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM maintenance_records),2) AS pct
FROM maintenance_records
GROUP BY vehicle_status
ORDER BY FIELD(vehicle_status,'Critical','Poor','Attention','Good','Excellent');

-- Latest health scores per vehicle (today's inference)
SELECT v.vehicle_type, h.health_status, COUNT(*) AS cnt
FROM health_scores h JOIN vehicles v USING(vehicle_id)
WHERE h.assessment_date = CURDATE()
GROUP BY v.vehicle_type, h.health_status
ORDER BY v.vehicle_type, h.health_status;
```

---

> 🔙 [Back to README](../README.md)
