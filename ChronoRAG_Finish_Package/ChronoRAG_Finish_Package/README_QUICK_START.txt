CHRONORAG - QUICK START

SET UP, TEST, AND RUN
1. Extract this entire ZIP into a folder.
2. Double-click Install_and_Run.bat.
3. It creates .venv if needed, installs packages, checks Python syntax, runs core/data regression tests, runs app-flow smoke tests, runs three known-case change checks, and creates both evaluation CSV files.
4. Streamlit starts the app; open the local URL it prints (usually http://localhost:8501).
5. Keep the terminal open while using the app.

RUN TESTS WITHOUT OPENING THE APP
Double-click Run_Tests_Only.bat. It writes:
- CHRONORAG_TEST_REPORT.txt (66 core/data checks)
- APP_FLOW_TEST_REPORT.txt (14 mocked app-flow checks)
- chronorag_evaluation_results.csv (19 document-family revision-selection results)
- CHANGE_DETECTION_EVALUATION.md and change_detection_smoke_results.csv (2 known changes + 1 unchanged-topic control)

The app-flow tests use a mocked Streamlit API, so they check app logic but are not a real browser-rendering test.

LIVE SERVER CHECK
After the Streamlit app is running, double-click Verify_Live_App.bat. It checks the local HTTP health endpoint and app page shell; it is not full browser interaction automation.

BROWSER SMOKE TEST
1. The app starts with a fixed snapshot of real Wikipedia revisions. Click **Fetch latest Wikipedia revisions** in the sidebar to query the public English Wikipedia API for each article family.
2. After the refresh, confirm the app reports how many pages were checked and how many new revisions were appended.
3. Use **Download refreshed revision CSV** to save the refreshed data. Newly fetched revisions stay in the current Streamlit session until downloaded; the app does not write them back to GitHub.
4. Ask: What changed between versions of the COVID-19 pandemic in Africa article regarding Botswana?
   Expected: earlier text says more than 100 people; later text says more than 50 people.
5. Ask: What changed between versions of the COVID-19 pandemic in Africa article regarding Algeria?
   Expected for these two stored revisions: no Algeria-specific text difference found.
6. Ask: What changed between versions of the ChuChu TV article?
   Expected: it shows the stored revisions and a ranking/statistics change.
7. Switch between Baseline RAG retrieval and ChronoRAG version-aware retrieval; Botswana should select revision 946148507 under baseline and 946149857 under ChronoRAG if those revisions remain the best matches in the loaded dataset.
8. Enter unrelated random tokens, e.g. zxqvbn kjhgfds qqqqwwwee. Expected: the app warns that no lexical match was found rather than presenting an arbitrary result.

LIMITATIONS
The app uses TF-IDF and a version-aware latest-timestamp rule. It does not use an external LLM. The bundled dataset starts with 38 stored revisions across 19 article families; it is not a complete revision history.
The evaluation measures retrieval selection only. It does not measure contradiction-detection accuracy or prove that text differences are contradictions. Live refresh requires outbound network access to Wikipedia, and any failed page refresh is reported without deleting existing rows.

If Python is missing, install Python 3.10+ and enable Add Python to PATH, then double-click the BAT again.
