# Database Generation Script - README

## File: `generate_data.py`

### Overview
This script creates the MySQL database schema and generates realistic synthetic data for the Military Vehicle Health Monitoring System.

### What It Does

**Created Tables (9):**
1. `vehicles` - Master vehicle registry with 5,000 records
2. `telemetry_data` - OBD-II sensor readings (sampled at 5%)
3. `diagnostic_codes` - Fault codes (to be added)
4. `maintenance_records` - Service history (to be added)
5. `operational_logs` - Trip/mission data (to be added)
6. `fuel_records` - Refueling events (to be added)
7. `health_scores` - ML predictions (populated by ml_pipeline.py)
8. `spare_parts_inventory` - 500 parts with stock levels
9. `users` - 50 personnel records

### Current Implementation Status

✅ **Completed:**
- MySQL schema creation with native ENUMs
- Vehicle generation (5,000 vehicles with Indian military context)
- Telemetry generation (5% sample = ~200K records for performance)
- User/personnel generation (50 users with ranks and roles)
- Spare parts inventory (500 parts)

⚠️ **To Be Extended (Optional):**
- Diagnostic codes generation
- Maintenance records generation
- Operational logs generation
- Fuel records generation

> **Note**: The core tables (vehicles, telemetry, users, parts) are sufficient for the ML pipeline to begin training. The additional tables can be generated later or created via the ML pipeline based on telemetry patterns.

### Configuration

**Before running, update these settings in `generate_data.py`:**

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'military_vehicle_health',
    'user': 'root',
    'password': 'YOUR_MYSQL_PASSWORD',  # <-- CHANGE THIS
    'charset': 'utf8mb4',
}
```

### Prerequisites

1. **MySQL Server 8.0+** installed and running
2. **Python packages**:
   ```bash
   pip install mysql-connector-python pandas numpy
   ```

3. **Create database** (script will auto-create, but you can pre-create):
   ```sql
   CREATE DATABASE military_vehicle_health CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### Usage

```bash
# Run the script
python generate_data.py
```

**Expected output:**
```
================================================================================
MILITARY VEHICLE HEALTH MONITORING SYSTEM
DATABASE GENERATION SCRIPT
================================================================================
...
✅ Connected to MySQL server and selected database: military_vehicle_health
✅ Created table: vehicles
✅ Created table: telemetry_data
...
✅ Generated 5000 vehicle records
✅ Generated 50 user records
✅ Generated 500 spare parts
  Progress: 10,000 telemetry records inserted...
  Progress: 20,000 telemetry records inserted...
...
✅ Generated 200,000+ telemetry records
================================================================================
DATABASE GENERATION COMPLETE
================================================================================
```

### Performance Optimizations

1. **Telemetry Sampling**: Uses 5% sampling (`sample_ratio=0.05`) to generate manageable data size
   - Full scale would be ~11M records
   - 5% sample = ~200K records (sufficient for ML training)
   - Adjust `sample_ratio` in `generate_telemetry_data()` call if needed

2. **Batch Inserts**: Uses batch size of 1,000 for telemetry inserts

3. **Estimated Runtime**: 
   - Schema creation: <1 second
   - Vehicle generation: ~10 seconds
   - Telemetry generation (5% sample): 2-5 minutes
   - Total: ~5-10 minutes

### Data Realism Features

✅ **Vehicles:**
- Indian military manufacturers (Ashok Leyland, Tata, Mahindra, BharatBenz)
- Realistic vehicle types (truck, armored_carrier, transport, ambulance, utility)
- Acquisition dates spread over 2005-2024
- Age-appropriate wear patterns

✅ **Telemetry:**
- Correlated engine metrics (RPM ↔ Speed ↔ Temperature)
- Realistic OBD-II value ranges:
  - Engine coolant: 75-105°C
  - RPM: 650-3500
  - Speed: 0-80 km/h
  - Battery: 12.2-14.4V
- Fuel consumption patterns
- GPS coordinates for Indian military regions

✅ **Users:**
- Indian military ranks (Major, Captain, Lieutenant, etc.)
- Roles: admin, maintenance_officer, driver, viewer
- Email format: user@military.gov.in

### Verification

After running, verify the data:

```sql
-- Connect to MySQL
mysql -u root -p

-- Use the database
USE military_vehicle_health;

-- Check table counts
SELECT COUNT(*) FROM vehicles;          -- Should be ~5000
SELECT COUNT(*) FROM telemetry_data;    -- Should be ~200K
SELECT COUNT(*) FROM users;              -- Should be 50
SELECT COUNT(*) FROM spare_parts_inventory;  -- Should be 500

-- Sample vehicle data
SELECT * FROM vehicles LIMIT 5;

-- Sample telemetry with correlations
SELECT 
    vehicle_id,
    timestamp,
    current_speed_kmph,
    engine_rpm,
    engine_coolant_temp_celsius,
    fuel_level_percent
FROM telemetry_data
ORDER BY timestamp DESC
LIMIT 10;
```

### Next Steps

✅ Once database generation is complete, proceed to`ml_pipeline.py`:
   - Feature engineering from telemetry data
   - Health status classification
   - Days-to-service prediction
   - Health scores population

### Troubleshooting

**Error: Access denied for user 'root'**
- Update `DB_CONFIG['password']` with your MySQL password

**Error: Unknown database 'military_vehicle_health'**
- Script auto-creates database, but ensure MySQL user has CREATE DATABASE permission

**Error: Too slow / Running out of memory**
- Reduce `NUM_VEHICLES` (e.g., to 1000)
- Reduce `sample_ratio` (e.g., to 0.01 for 1%)
- Reduce `DAYS_OF_HISTORY` (e.g., to 180 for 6 months)

**Want to regenerate data:**
- Script automatically drops existing tables and recreates them
- Safe to run multiple times
