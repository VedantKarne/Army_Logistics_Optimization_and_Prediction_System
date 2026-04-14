"""
Verification script for generated synthetic labels
"""

import mysql.connector
import json

DB_CONFIG = {
    'host': 'localhost',
    'database': 'military_vehicle_health',
    'user': 'root',
    'password': 'vedant@14',
    'port': 3306
}

def run_verification():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    print("="*80)
    print("SYNTHETIC LABEL VERIFICATION")
    print("="*80)
    
    # 1. Table counts
    print("\n📊 TABLE COUNTS:")
    cursor.execute("SELECT COUNT(*) as cnt FROM maintenance_records")
    maint_count = cursor.fetchone()['cnt']
    print(f"  Maintenance Records: {maint_count:,}")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM diagnostic_codes")
    diag_count = cursor.fetchone()['cnt']
    print(f"  Diagnostic Codes:    {diag_count:,}")
    print(f"  Total Labels:        {maint_count + diag_count:,}")
    
    # 2. Service type distribution
    print("\n📋 MAINTENANCE SERVICE TYPE DISTRIBUTION:")
    cursor.execute("""
        SELECT service_type, COUNT(*) as cnt, 
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM maintenance_records), 2) as pct
        FROM maintenance_records
        GROUP BY service_type
        ORDER BY cnt DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row['service_type']:15} {row['cnt']:6,} ({row['pct']:5.1f}%)")
    
    # 3. DTC severity distribution
    print("\n⚠️  DIAGNOSTIC CODE SEVERITY DISTRIBUTION:")
    cursor.execute("""
        SELECT severity, COUNT(*) as cnt,
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM diagnostic_codes), 2) as pct
        FROM diagnostic_codes
        GROUP BY severity
        ORDER BY FIELD(severity, 'critical', 'major', 'minor', 'warning')
    """)
    for row in cursor.fetchall():
        print(f"  {row['severity']:10} {row['cnt']:6,} ({row['pct']:5.1f}%)")
    
    # 4. Health score distribution
    print("\n💚 HEALTH SCORE DISTRIBUTION:")
    cursor.execute("""
        SELECT 
            ROUND(AVG(pre_service_health_score), 2) as avg_pre,
            ROUND(AVG(post_service_health_score), 2) as avg_post,
            ROUND(MIN(pre_service_health_score), 2) as min_pre,
            ROUND(MAX(pre_service_health_score), 2) as max_pre,
            ROUND(STDDEV(pre_service_health_score), 2) as std_pre
        FROM maintenance_records
    """)
    health = cursor.fetchone()
    print(f"  Pre-Service Health:  Avg={health['avg_pre']:.1f}, Min={health['min_pre']:.1f}, Max={health['max_pre']:.1f}, Std={health['std_pre']:.1f}")
    print(f"  Post-Service Health: Avg={health['avg_post']:.1f}")
    
    # 5. Top diagnostic codes
    print("\n🔧 TOP 10 DIAGNOSTIC CODES:")
    cursor.execute("""
        SELECT code, description, COUNT(*) as cnt
        FROM diagnostic_codes
        GROUP BY code, description
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row['code']:8} {row['cnt']:5,}  {row['description'][:50]}")
    
    # 6. System affected distribution
    print("\n🔩 SYSTEMS AFFECTED:")
    cursor.execute("""
        SELECT system_affected, COUNT(*) as cnt
        FROM diagnostic_codes
        GROUP BY system_affected
        ORDER BY cnt DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row['system_affected']:15} {row['cnt']:6,}")
    
    # 7. Active vs resolved codes
    print("\n✅ CODE STATUS:")
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as resolved
        FROM diagnostic_codes
    """)
    status = cursor.fetchone()
    total = float(status['active'] or 0) + float(status['resolved'] or 0)
    if total > 0:
        print(f"  Active:   {status['active']:6,} ({float(status['active'])*100.0/total:.1f}%)")
        print(f"  Resolved: {status['resolved']:6,} ({float(status['resolved'])*100.0/total:.1f}%)")
    else:
        print(f"  No data")
    
    # 8. Cost analysis
    print("\n💰 SERVICE COST ANALYSIS:")
    cursor.execute("""
        SELECT service_type, 
               ROUND(AVG(service_cost), 2) as avg_cost,
               ROUND(MIN(service_cost), 2) as min_cost,
               ROUND(MAX(service_cost), 2) as max_cost
        FROM maintenance_records
        GROUP BY service_type
    """)
    for row in cursor.fetchall():
        print(f"  {row['service_type']:15} Avg=₹{row['avg_cost']:8,.0f}, Min=₹{row['min_cost']:8,.0f}, Max=₹{row['max_cost']:8,.0f}")
    
    print("\n" + "="*80)
    print("✅ VERIFICATION COMPLETE")
    print("="*80)
    
    conn.close()

if __name__ == "__main__":
    run_verification()
