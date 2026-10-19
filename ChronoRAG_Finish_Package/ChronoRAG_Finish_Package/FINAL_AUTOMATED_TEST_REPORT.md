# ChronoRAG Final Automated Test Report

**Previous test date:** 16 October 2026  
**Package tested:** `ChronoRAG_Finish_Package`  
**Post-removal validation status: PENDING.** This report predates the current source changes. Re-run `Run_Tests_Only.bat` before submission. The updated test code is expected to contain 64 core/data checks and 14 app-flow checks, plus the 3 known-case checks and 2 simulated HTTP checks; these expected counts have not been executed in this session.

## Results

| Test group | Result | Notes |
|---|---:|---|
| Python syntax compilation | Rerun pending | Compile app, evaluation scripts, and tests after the current source change. |
| Core/data/retrieval regression | 64 expected; not rerun | Includes schema checks, real revision records, family selection, chronological selection, known text changes, malformed CSV handling, and topic comparison. |
| App-flow smoke tests | 14 expected; not rerun | Streamlit API is stubbed; these check app logic/control flow, not actual UI rendering. |
| Known change-detection examples | 3 cases; rerun pending | Botswana changed text, Algeria unchanged-topic negative control for these two stored versions, and ChuChu TV ranking change. |
| HTTP health-check utility | Prior simulated check: 2/2 | Verified against a simulated local HTTP server, not against a running Streamlit process; rerun if needed. |
| Package archive | Not applicable | The stale bundled project ZIP was removed; use the current repository download or run from the project folder. |

## Retrieval evaluation

- Real data: 38 stored revisions across 19 document families (two revisions per family).
- Baseline selected the correct document family for 19/19 standardized title queries.
- Baseline selected the latest stored revision for 7/19 (36.8%).
- ChronoRAG selected the latest timestamp for 19/19 (100%) because that is its current version-selection rule.

**Interpretation:** The latest-version percentage is not contradiction-detection accuracy. The benchmark has 19 article families with only two stored versions each and uses standardized title-based queries; it does not establish performance on complete document histories or a broad set of independently labelled contradictions.

## Change-detection cases

1. **Botswana:** the removed passage includes `more than 100 people`, and the added passage includes `more than 50 people`.
2. **Algeria:** no topic-specific change was found in the two stored COVID-19 article revisions checked. This applies only to this pair of revisions.
3. **ChuChu TV:** the earlier 42nd-place ranking appears in removed text and the later 43rd-place ranking appears in added text.

Textual differences may be corrections, time-dependent updates, additions, or deletions; they are not automatically logical contradictions.

## What was not tested here

- The actual Streamlit runtime could not be launched in this environment because Streamlit was not installed and package-index network access was unavailable.
- The HTTP health-check script was tested against a simulated server. A check against the user's own running app must be executed on their Windows machine.
- No automated full browser interaction was run against the user's local browser.
- No broad, independently labelled contradiction benchmark was evaluated; therefore no general precision, recall, F1, or contradiction-accuracy claim is supported.

## Local verification on Windows

1. Keep `Install_and_Run.bat` running.
2. In another terminal opened in this package folder, run `Verify_Live_App.bat` or `python verify_live_app.py http://localhost:8501`.
3. Check the app with the Botswana, Algeria, and ChuChu TV questions in the browser.

The package includes reproducible scripts and CSV outputs for the tests listed above.
