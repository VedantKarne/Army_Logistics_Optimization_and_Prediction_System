$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$python = "C:\Users\ADMIN\Documents\Army_ML_3_02_26\generate_data_env\Scripts\python.exe"

Write-Host "1. Running generate_data.py..."
& $python -X utf8 -u data_generation\generate_data.py > data_generation\generate_data.log 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "Error in generate_data.py"; exit $LASTEXITCODE }

Write-Host "2. Running generate_synthetic_labels.py..."
& $python -X utf8 -u data_generation\generate_synthetic_labels.py > data_generation\generate_labels.log 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "Error in generate_synthetic_labels.py"; exit $LASTEXITCODE }

Write-Host "3. Running feature_engineering.py..."
& $python -X utf8 -u Army_ML_Pipeline_and_Files\feature_engineering.py > Army_ML_Pipeline_and_Files\feature_engineering.log 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "Error in feature_engineering.py"; exit $LASTEXITCODE }

Write-Host "4. Running train_health_model.py..."
& $python -X utf8 -u Army_ML_Pipeline_and_Files\train_health_model.py > Army_ML_Pipeline_and_Files\train_health_model.log 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "Error in train_health_model.py"; exit $LASTEXITCODE }

Write-Host "5. Running optimize_ensemble.py..."
& $python -X utf8 -u Army_ML_Pipeline_and_Files\optimize_ensemble.py > Army_ML_Pipeline_and_Files\optimize_ensemble.log 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "Error in optimize_ensemble.py"; exit $LASTEXITCODE }

Write-Host "6. Running evaluate_ensemble.py..."
& $python -X utf8 -u Army_ML_Pipeline_and_Files\evaluate_ensemble.py > Army_ML_Pipeline_and_Files\evaluate_ensemble.log 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "Error in evaluate_ensemble.py"; exit $LASTEXITCODE }

Write-Host "Pipeline completed successfully!"
