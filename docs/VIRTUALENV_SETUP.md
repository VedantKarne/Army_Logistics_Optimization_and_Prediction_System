# Virtual Environment Setup for `generate_data.py`

## Summary
A Python virtual environment named `generate_data_env` has been created with all necessary packages for running `generate_data.py`.

## Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| mysql-connector-python | 9.5.0 | MySQL database connectivity |
| pandas | 3.0.0 | Data manipulation and analysis |
| numpy | 2.4.2 | Numerical computing |

### Dependencies (Auto-installed)
- python-dateutil 2.9.0.post0
- six 1.17.0
- tzdata 2025.3

## How to Activate the Virtual Environment

### On Windows (PowerShell)
```powershell
.\generate_data_env\Scripts\Activate.ps1
```

### On Windows (Command Prompt)
```cmd
generate_data_env\Scripts\activate.bat
```

## Running the Script

After activating the virtual environment, run:

```powershell
python generate_data.py
```

## Deactivating the Virtual Environment

Simply run:
```powershell
deactivate
```

## Notes

> [!IMPORTANT]
> Before running `generate_data.py`, ensure you have:
> 1. MySQL server running on localhost:3306
> 2. Updated the password in `generate_data.py` (line 37) with your MySQL root password
> 3. Sufficient disk space for the database (the script will generate 5,000+ vehicles with telemetry data)

## Package Compatibility

All packages have been installed with compatible versions:
- ✅ mysql-connector-python 9.5.0 works with MySQL 8.0+
- ✅ pandas 3.0.0 is compatible with numpy 2.4.2
- ✅ All dependencies are inter-compatible

## Requirements File

A `requirements_generate_data.txt` file has been created for easy reinstallation:

```powershell
pip install -r requirements_generate_data.txt
```
