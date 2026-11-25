@echo off
cd /d "%~dp0"
echo ======================================
echo          SMARTATTEND STARTING
echo ======================================
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Python/pip install nahi hua. README file dekhein.
  pause
  exit /b 1
)
echo.
echo Browser mein http://127.0.0.1:5000 khulega.
start "" http://127.0.0.1:5000
py app.py
pause
