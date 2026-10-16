@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo ChronoRAG - automatic setup and evaluation
echo ================================================
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
echo.
echo Running revision-selection evaluation...
python evaluate_chronorag.py data\real_documents.csv --output chronorag_evaluation_results.csv
if errorlevel 1 goto fail
echo.
echo Evaluation completed. Results saved to chronorag_evaluation_results.csv.
echo Starting ChronoRAG web app...
python -m streamlit run app.py
if errorlevel 1 goto fail
goto end
:fail
echo.
echo Setup or run failed. Read the error above, then send it to ChatGPT.
pause
exit /b 1
:end
endlocal
