import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='vedant@14'
    )
    cursor = conn.cursor()
    
    # Get MySQL data directory
    cursor.execute("SHOW VARIABLES LIKE 'datadir'")
    datadir = cursor.fetchone()[1]
    
    print(f"MySQL Data Directory: {datadir}")
    print(f"\nDatabase files are stored in: {datadir}military_vehicle_health\\")
    
    # Get database size
    cursor.execute("""
        SELECT 
            table_schema AS 'Database',
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
        FROM information_schema.tables 
        WHERE table_schema = 'military_vehicle_health'
        GROUP BY table_schema
    """)
    
    result = cursor.fetchone()
    if result:
        print(f"Database Size: {result[1]} MB")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
