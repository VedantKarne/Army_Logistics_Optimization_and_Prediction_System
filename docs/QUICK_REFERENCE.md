# Quick Reference: Database Sharing

## 🎯 Quick Steps for You

1. **Double-click:** `export_database.bat`
2. **Enter password:** `vedant@14`
3. **Wait:** 2-5 minutes
4. **Share these files with peers:**
   - ✅ `military_vehicle_health_export.sql` (the database)
   - ✅ `IMPORT_INSTRUCTIONS.md` (for your peers)

---

## 📦 Files Created for Database Sharing

| File | Purpose | For Whom |
|------|---------|----------|
| `export_database.bat` | Export script - run this! | **YOU** |
| `SHARING_INSTRUCTIONS.md` | How to export and share | **YOU** |
| `IMPORT_INSTRUCTIONS.md` | How to import database | **YOUR PEERS** |
| `military_vehicle_health_export.sql` | The actual database dump | **YOUR PEERS** |

---

## 🚀 What Happens Next

### You Do:
1. Run `export_database.bat`
2. Get `military_vehicle_health_export.sql` file
3. Share it with peers

### Your Peers Do:
1. Download the SQL file
2. Run: `mysql -u root -p < military_vehicle_health_export.sql`
3. Start using the database!

---

## 💡 Pro Tips

**Compress before sharing:**
- Right-click `military_vehicle_health_export.sql`
- Select "Send to > Compressed (zipped) folder"
- Share the ZIP file (much smaller!)

**Verify before sharing:**
- Check file size (should be 200-500 MB)
- Ensure export completed successfully
- Look for "✅ EXPORT SUCCESSFUL!" message

**Speed up transfer:**
- Use USB drive for local sharing
- Use cloud storage (Google Drive/OneDrive) for remote sharing

---

## ⚠️ Important Notes

✅ **DO share:** The exported SQL file  
❌ **DON'T share:** MySQL's Data folder  
✅ **Safe:** This is synthetic test data  
❌ **Avoid:** Sharing production databases without authorization  

---

## 📊 Database Size

- **Tables:** 9
- **Total Records:** ~1.89 million
- **Largest Table:** telemetry_data (1.74M records)
- **Export File:** ~200-500 MB (text-based SQL)
- **Compressed:** ~50-150 MB (ZIP)

---

## ❓ Quick Troubleshooting

**Export fails?**
- Check MySQL is running
- Verify password: `vedant@14`
- Ensure database exists: run `export_db_stats.py`

**File too large?**
- Normal! 1.89M records = large file
- Compress it before sharing
- Or share via cloud storage

**Need to re-export?**
- Just run `export_database.bat` again
- Overwrites the old file
