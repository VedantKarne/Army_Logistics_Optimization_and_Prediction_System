import mysql.connector
import sys

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
    # Connect to database
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("="*80)
    print("DATABASE VERIFICATION - military_vehicle_health")
    print("="*80)
    print()
    
    # Get list of all tables
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    
    print(f"✅ Total Tables Created: {len(tables)}")
    print()
    
    # Get row count for each table
    print("Table Statistics:")
    print("-" * 80)
    print(f"{'Table Name':<30} {'Row Count':>15} {'Status':>15}")
    print("-" * 80)
    
    total_rows = 0
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        total_rows += count
        status = "✅ Created" if count > 0 else "⚠️  Empty"
        print(f"{table:<30} {count:>15,} {status:>15}")
    
    print("-" * 80)
    print(f"{'TOTAL':<30} {total_rows:>15,}")
    print("=" * 80)
    
    # Get some sample data from vehicles table
    print("\n📊 Sample Vehicle Data (First 5 vehicles):")
    print("-" * 80)
    cursor.execute("""
        SELECT vehicle_id, vehicle_type, make, model, operational_status 
        FROM vehicles 
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  {row[0]} - {row[1]} - {row[2]} {row[3]} - Status: {row[4]}")
    
    print("\n✅ Database verification completed successfully!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error during verification: {e}")
    sys.exit(1)
