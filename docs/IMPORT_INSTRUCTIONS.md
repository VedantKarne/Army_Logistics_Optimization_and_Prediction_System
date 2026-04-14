# Database Import Instructions for Peers

## 📥 How to Import the Military Vehicle Health Database

### Prerequisites

Before importing, ensure you have:

1. ✅ **MySQL Server 8.0+** installed and running
   - Download from: https://dev.mysql.com/downloads/mysql/
   - Or use: `winget install Oracle.MySQL` (Windows 11)

2. ✅ **MySQL root password** set up during installation

3. ✅ **Sufficient disk space**
   - Database size: ~2-3 GB
   - Ensure at least 5 GB free space

---

## 🚀 Import Methods

### Method 1: Command Line (Recommended)

#### Step 1: Open Command Prompt or PowerShell

Press `Win + R`, type `cmd`, press Enter

#### Step 2: Navigate to the folder containing the SQL file

```bash
cd C:\Path\To\Downloaded\Files
```

#### Step 3: Import the database

```bash
mysql -u root -p < military_vehicle_health_export.sql
```

- When prompted, enter your MySQL root password
- Wait 2-5 minutes for import to complete

#### Step 4: Verify the import

```bash
mysql -u root -p
```

Then in MySQL prompt:
```sql
SHOW DATABASES;
USE military_vehicle_health;
SHOW TABLES;
SELECT COUNT(*) FROM vehicles;
SELECT COUNT(*) FROM telemetry_data;
EXIT;
```

Expected results:
- `vehicles`: 5,000 records
- `telemetry_data`: 1,744,739 records

---

### Method 2: MySQL Workbench (GUI)

1. Open **MySQL Workbench**
2. Connect to your local MySQL server
3. Go to **Server** → **Data Import**
4. Select **Import from Self-Contained File**
5. Browse to `military_vehicle_health_export.sql`
6. Under **Default Target Schema**, select **New** and name it `military_vehicle_health`
7. Click **Start Import**
8. Wait for completion

---

## ⚙️ Configuration for Your Projects

After importing, update your project's database configuration:

### If using Python (mysql-connector-python):

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'military_vehicle_health',
    'user': 'root',
    'password': 'YOUR_MYSQL_PASSWORD',  # ← Change this
    'charset': 'utf8mb4',
}
```

### If using other languages:

**Connection String Format:**
```
mysql://root:YOUR_PASSWORD@localhost:3306/military_vehicle_health
```

---

## 🗂️ Database Structure

After import, you'll have 9 tables:

| Table | Records | Status |
|-------|---------|--------|
| `vehicles` | 5,000 | ✅ Populated |
| `telemetry_data` | 1,744,739 | ✅ Populated |
| `fuel_records` | 98,118 | ✅ Populated |
| `operational_logs` | 42,831 | ✅ Populated |
| `users` | 50 | ✅ Populated |
| `spare_parts_inventory` | 500 | ✅ Populated |
| `maintenance_records` | 0 | ⚠️ Empty |
| `diagnostic_codes` | 0 | ⚠️ Empty |
| `health_scores` | 0 | ⚠️ Empty |

---

## 🧪 Sample Queries to Test

```sql
-- View sample vehicles
SELECT * FROM vehicles LIMIT 10;

-- Get telemetry for a specific vehicle
SELECT * FROM telemetry_data 
WHERE vehicle_id = 'MIL-TRU-00001' 
ORDER BY timestamp DESC 
LIMIT 20;

-- Check fuel efficiency
SELECT 
    vehicle_id,
    AVG(fuel_efficiency_kmpl) as avg_efficiency
FROM fuel_records
GROUP BY vehicle_id
LIMIT 10;

-- View user accounts
SELECT user_id, username, full_name, `rank`, role 
FROM users;

-- Operational statistics
SELECT 
    mission_type,
    COUNT(*) as mission_count,
    AVG(trip_distance_km) as avg_distance
FROM operational_logs
GROUP BY mission_type;
```

---

## ❌ Troubleshooting

### Error: "Access denied for user 'root'"
**Solution:** Use the correct MySQL password for your local installation

### Error: "Unknown database 'military_vehicle_health'"
**Solution:** The database wasn't created. Try:
```sql
CREATE DATABASE military_vehicle_health CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Then re-run the import command.

### Error: "MySQL command not found"
**Solution:** Add MySQL to your system PATH
- Windows: `C:\Program Files\MySQL\MySQL Server 8.0\bin`
- Or use full path: `"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < file.sql`

### Import takes too long (>10 minutes)
**Solution:** 
- Normal for 1.89M records
- If stuck, check CPU/disk usage
- Try importing in MySQL Workbench instead

### Error: "Table already exists"
**Solution:** Drop the existing database first:
```sql
DROP DATABASE IF EXISTS military_vehicle_health;
CREATE DATABASE military_vehicle_health CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Then re-import.

---

## 🔄 Alternative: Regenerate Data

Instead of importing, you can regenerate the data yourself:

1. Get `generate_data.py` from your peer
2. Install requirements: `pip install mysql-connector-python pandas numpy`
3. Update the password in the script (line 48)
4. Run: `python generate_data.py`

This will create fresh data with the same structure.

---

## 📞 Need Help?

Contact your peer who shared this database with any import issues.

**Useful information to share when asking for help:**
- MySQL version: `mysql --version`
- Operating system
- Error message (full text)
- What method you tried (CLI or Workbench)
