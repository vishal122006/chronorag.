@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo ChronoRAG - run all automated tests and reports
echo ==============================================
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
echo Installing required packages...
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo [1/5] Checking syntax...
python -m py_compile app.py evaluate_chronorag.py test_chronorag.py test_app_smoke.py evaluate_change_detection.py verify_live_app.py
if errorlevel 1 goto fail
echo [2/5] Data/retrieval regression tests...
python test_chronorag.py
if errorlevel 1 goto fail
echo [3/5] App-flow smoke tests (Streamlit UI is stubbed; no browser test)...
python test_app_smoke.py
if errorlevel 1 goto fail
echo [4/5] Revision-selection evaluation...
python evaluate_chronorag.py data\real_documents.csv --output chronorag_evaluation_results.csv
if errorlevel 1 goto fail
echo [5/5] Known change-detection smoke evaluation...
python evaluate_change_detection.py
if errorlevel 1 goto fail
echo.
echo SUCCESS: automated tests completed. See CHRONORAG_TEST_REPORT.txt, APP_FLOW_TEST_REPORT.txt,
echo CHANGE_DETECTION_EVALUATION.md and both CSV result files.
pause
goto end
:fail
echo.
echo TESTS FAILED. Copy the error above and send it to ChatGPT.
pause
exit /b 1
:end
endlocal
