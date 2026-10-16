@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: The project's .venv was not found.
  echo First run Install_and_Run.bat, then leave the app running.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python verify_live_app.py %*
pause
endlocal
