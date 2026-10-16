@echo off
setlocal
cd /d "%~dp0"
echo ======================================================
echo ChronoRAG - setup, automated tests, evaluation, and app
echo ======================================================
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found. Install Python 3.10 or newer first.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto fail
)
call ".venv\Scripts\activate.bat"
echo.
echo [1/6] Installing required packages...
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo [2/6] Checking Python syntax...
python -m py_compile app.py evaluate_chronorag.py test_chronorag.py test_app_smoke.py evaluate_change_detection.py verify_live_app.py
if errorlevel 1 goto fail
echo.
echo [3/6] Running data and retrieval regression tests...
python test_chronorag.py
if errorlevel 1 goto fail
echo.
echo [4/6] Running app-flow smoke tests...
python test_app_smoke.py
if errorlevel 1 goto fail
echo.
echo [5/6] Running revision-selection evaluation...
python evaluate_chronorag.py data\real_documents.csv --output chronorag_evaluation_results.csv
if errorlevel 1 goto fail
echo.
echo [6/6] Running change-detection smoke evaluation...
python evaluate_change_detection.py
if errorlevel 1 goto fail
echo All automated checks passed. Reports and CSV results are saved in this folder.
echo Starting ChronoRAG web app...
python -m streamlit run app.py
if errorlevel 1 goto fail
goto end
:fail
echo.
echo Setup, testing, or run failed. Copy the error above and send it to ChatGPT.
pause
exit /b 1
:end
endlocal
