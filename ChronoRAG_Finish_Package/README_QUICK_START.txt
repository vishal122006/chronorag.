CHRONORAG - QUICK START

1. Extract this entire ZIP into a folder.
2. Double-click Install_and_Run.bat.
3. Wait while it creates .venv, installs packages, and runs the revision-selection evaluation.
4. Streamlit starts the app; open the local URL it prints (usually http://localhost:8501).
5. Evaluation results are saved to chronorag_evaluation_results.csv.

The app uses TF-IDF and a version-aware latest-timestamp rule. It does not use an external LLM.
The real dataset contains 38 stored revisions across 19 document families (two versions per family), not complete histories.
The evaluation measures revision selection only. It does not measure contradiction-detection accuracy or prove that text differences are contradictions.

If Python is missing, install Python 3.10+ and enable Add Python to PATH, then double-click the BAT again.
