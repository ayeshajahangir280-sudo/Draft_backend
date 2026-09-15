$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Installing backend requirements..."
python -m pip install -r requirements.txt

Write-Host "Applying database migrations..."
python manage.py migrate

Write-Host "Seeding demo draft data..."
python manage.py seed_demo

Write-Host "Starting Django backend at http://127.0.0.1:8000"
python manage.py runserver 127.0.0.1:8000
