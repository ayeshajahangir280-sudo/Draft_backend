@echo off
setlocal
cd /d "%~dp0"

echo Installing backend requirements...
python -m pip install -r requirements.txt || exit /b 1

echo Applying database migrations...
python manage.py migrate || exit /b 1

echo Seeding demo draft data...
python manage.py seed_demo || exit /b 1

echo Starting Django backend at http://127.0.0.1:8000
python manage.py runserver 127.0.0.1:8000
