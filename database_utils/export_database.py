"""
Database Export Script - Python Version
Exports military_vehicle_health database to SQL file using mysqldump
This version auto-detects mysqldump location, no PATH required!
"""

import subprocess
import os
import sys
from pathlib import Path

# Database configuration
DB_NAME = "military_vehicle_health"
DB_USER = "root"
DB_PASSWORD = "vedant@14"
DB_HOST = "localhost"

# Output file
SCRIPT_DIR = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR.parent / "exports" / "military_vehicle_health_export.sql"

def find_mysqldump():
    """Find mysqldump executable in common locations."""
    common_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.1\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.2\bin\mysqldump.exe",
        r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\xampp\mysql\bin\mysqldump.exe",
        r"C:\wamp\bin\mysql\mysql8.0.27\bin\mysqldump.exe",
    ]
    
    # Try common paths first
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Try to find it in PATH
    try:
        result = subprocess.run(
            ["where", "mysqldump"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None

def export_database(mysqldump_path):
    """Export the database using mysqldump."""
    print(f"\n🔄 Exporting database to: {OUTPUT_FILE}")
    print(f"📂 Using mysqldump: {mysqldump_path}\n")
    
    # Build the command
    cmd = [
        mysqldump_path,
        f"--host={DB_HOST}",
        f"--user={DB_USER}",
        f"--password={DB_PASSWORD}",
        "--single-transaction",
        "--quick",
        "--lock-tables=false",
        "--routines",
        "--triggers",
        DB_NAME
    ]
    
    try:
        # Run mysqldump and capture output
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
        
        # Check if file was created and has content
        if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
            file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
            
            print("=" * 80)
            print("✅ EXPORT SUCCESSFUL!")
            print("=" * 80)
            print(f"\n📄 Export file: {OUTPUT_FILE.name}")
            print(f"📊 File size: {file_size_mb:.2f} MB")
            print(f"📂 Location: {SCRIPT_DIR}")
            print("\n🎯 Next Steps:")
            print("  1. Share this file with your peers:")
            print(f"     → {OUTPUT_FILE.name}")
            print("  2. Also share: IMPORT_INSTRUCTIONS.md")
            print("\n💡 Tip: Compress the .sql file before sharing to reduce size!")
            print("=" * 80)
            return True
        else:
            print("❌ Export file was not created or is empty!")
            return False
            
    except subprocess.CalledProcessError as e:
        print("=" * 80)
        print("❌ EXPORT FAILED!")
        print("=" * 80)
        print(f"\nError: {e.stderr}")
        print("\nPossible issues:")
        print("  1. MySQL server is not running")
        print("  2. Incorrect password (check line 13 in this script)")
        print("  3. Database 'military_vehicle_health' doesn't exist")
        print("  4. Insufficient permissions")
        print("\nTo verify database exists, run: python export_db_stats.py")
        print("=" * 80)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("=" * 80)
    print("DATABASE EXPORT SCRIPT (Python Version)")
    print("=" * 80)
    print(f"\nDatabase: {DB_NAME}")
    print(f"Export to: {OUTPUT_FILE}\n")
    
    # Find mysqldump
    print("🔍 Searching for mysqldump...")
    mysqldump_path = find_mysqldump()
    
    if not mysqldump_path:
        print("=" * 80)
        print("❌ ERROR: mysqldump not found!")
        print("=" * 80)
        print("\nCould not locate mysqldump.exe")
        print("\nPlease install MySQL Server or specify the path manually.")
        print("\nCommon installation paths:")
        print("  • C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\")
        print("  • C:\\xampp\\mysql\\bin\\")
        print("\nOr add MySQL bin directory to your system PATH.")
        print("=" * 80)
        return False
    
    print(f"✅ Found mysqldump: {mysqldump_path}\n")
    
    # Export the database
    success = export_database(mysqldump_path)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Export cancelled by user.")
        sys.exit(1)
