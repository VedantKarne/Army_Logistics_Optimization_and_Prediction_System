import mysql.connector
import json
import os

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'military_vehicle_health',
    'user': 'root',
    'password': 'vedant@14',
    'charset': 'utf8mb4',
    'use_unicode': True
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    
    results = {
        "database": "military_vehicle_health",
        "total_tables": len(tables),
        "tables": {}
    }
    
    # Get row count for each table
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        results["tables"][table] = count
    
    # Save to JSON
    export_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exports', 'database_stats.json')
    with open(export_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Database statistics saved to {export_path}")
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
