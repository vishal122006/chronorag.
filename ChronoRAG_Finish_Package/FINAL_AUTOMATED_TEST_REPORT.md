# ChronoRAG Final Automated Test Report

**Test date:** 16 October 2026  
**Package tested:** `ChronoRAG_Finish_Package`  
**Overall result:** 86 automated checks passed; 0 failures across the available code/data and simulated HTTP test suites.

## Results

| Test group | Result | Notes |
|---|---:|---|
| Python syntax compilation | PASS | App, evaluation scripts, and test scripts compiled successfully. |
| Core/data/retrieval regression | 66/66 | Includes schema checks, record counts, revision pairs, family selection, chronological selection, known text changes, malformed CSV handling, and topic comparison. |
| App-flow smoke tests | 15/15 | Streamlit API is stubbed; these check app logic/control flow, not actual UI rendering. |
| Known change-detection examples | 3/3 | Botswana changed text, Algeria unchanged-topic negative control for these two stored versions, and ChuChu TV ranking change. |
| HTTP health-check utility | 2/2 | Verified against a simulated local HTTP server, not against a running Streamlit process. |
| ZIP archive integrity | PASS | The final ZIP was verified with `unzip -t`. |

## Retrieval evaluation

- Real data: 38 stored revisions across 19 document families (two revisions per family).
- Synthetic demo: 12 rows.
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
