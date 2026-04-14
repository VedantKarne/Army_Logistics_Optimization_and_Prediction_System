# Database Sharing Instructions

## 📦 For You (Data Provider)

### Step 1: Export the Database

Run the export script:
```bash
export_database.bat
```

- **Password:** When prompted, enter `vedant@14`
- **Output:** Creates `military_vehicle_health_export.sql` in the same folder
- **Time:** Takes 2-5 minutes depending on data size (~1.89M records)

### Step 2: Share These Files with Your Peers

Share the following files from `C:\Users\ADMIN\Documents\Army_ML_3_02_26\`:

1. ✅ **`military_vehicle_health_export.sql`** - The database dump (REQUIRED)
2. ✅ **`IMPORT_INSTRUCTIONS.md`** - Instructions for your peers (REQUIRED)
3. ✅ **`generate_data.py`** - Data generation script (Optional - for reference)
4. ✅ **`README_DATABASE.md`** - Database documentation (Optional)
5. ✅ **`requirements_generate_data.txt`** - Python dependencies (Optional)

### File Transfer Methods:

- **USB Drive** - Best for large files
- **Cloud Storage** - Google Drive, OneDrive, Dropbox
- **File Sharing** - WeTransfer, Send Anywhere
- **Network Share** - If on same network

---

## 📊 Database Contents Summary

Your peers will receive a database with:

| Table | Records | Description |
|-------|---------|-------------|
| `vehicles` | 5,000 | Military vehicle records |
| `telemetry_data` | 1,744,739 | Vehicle sensor readings |
| `fuel_records` | 98,118 | Refueling events |
| `operational_logs` | 42,831 | Trip/mission data |
| `users` | 50 | Personnel records |
| `spare_parts_inventory` | 500 | Parts inventory |
| `maintenance_records` | 0 | Empty (for future use) |
| `diagnostic_codes` | 0 | Empty (for future use) |
| `health_scores` | 0 | Empty (ML pipeline populates) |

**Total Records:** ~1.89 million

---

## 🔐 Security Note

The SQL export file contains:
- ✅ All table structures and data
- ✅ Sample user accounts with hashed passwords
- ⚠️ No actual sensitive production data (it's synthetic/test data)

If this were production data, you would need to:
- Remove or anonymize sensitive records
- Use encryption for transfer
- Obtain proper authorization

---

## ❓ Common Questions

**Q: How large is the export file?**
A: Approximately 200-500 MB (text-based, compresses well with zip)

**Q: Can I compress it?**
A: Yes! Right-click the `.sql` file and "Send to > Compressed (zipped) folder"

**Q: What if the export fails?**
A: Check that:
- MySQL is running
- Password is correct: `vedant@14`
- Database exists (run `export_db_stats.py` to verify)

**Q: How do I re-export if I update the data?**
A: Just run `export_database.bat` again - it will overwrite the old export

---

## 📞 Support

If your peers have issues importing, share this checklist:
- [ ] MySQL 8.0+ installed
- [ ] MySQL service is running
- [ ] They have root/admin access
- [ ] They followed IMPORT_INSTRUCTIONS.md exactly
- [ ] No firewall blocking MySQL (port 3306)
