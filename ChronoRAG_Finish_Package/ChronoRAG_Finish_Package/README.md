# ChronoRAG: Contradiction-Aware Retrieval for Changing Documents

ChronoRAG is a Streamlit research prototype for comparing ordinary similarity-based retrieval with a simple version-aware retrieval strategy over documents that have multiple stored revisions.

> **Scope note:** The current app is a retrieval-and-comparison prototype. It uses TF-IDF, not an external large language model. It shows text differences; it does not automatically prove that the differences are contradictions.

## Features

- Choose between a synthetic HR/IT policy demo and historical Wikipedia revision data.
- Upload a versioned CSV.
- Compare **Baseline RAG retrieval** (highest TF-IDF similarity) with **ChronoRAG version-aware retrieval** (find the best-matching document family, then select its latest stored timestamp).
- Review stored revision history and top retrieval results.
- Compare earlier and later stored text, with heuristic topic/section filtering.
- Run reproducible regression tests, revision-selection evaluation, and a small known-case text-change evaluation.

## Data schema

Uploaded CSV files must contain these columns:

| Column | Meaning |
|---|---|
| `doc_id` | Stable identifier shared by versions of the same document |
| `title` | Human-readable document title |
| `version` | Revision/version identifier |
| `effective_date` | Timestamp used to order versions |
| `source` | Source or provenance label |
| `text` | Document content for that revision |

The included real-data collection has 38 revision records across 19 Wikipedia article families (two stored versions per family). These are not complete histories. The synthetic demo has 12 rows and is not a source of real policy advice.

## Setup on Windows

1. Extract the project folder.
2. Double-click `Install_and_Run.bat`. It installs packages, checks syntax, runs both automated suites and the known-case change evaluation, writes both results CSVs, and then starts the app.
3. Open the local URL printed in the terminal, usually `http://localhost:8501`.
4. Keep the terminal open while using the app.

To run automated checks without launching the browser, double-click `Run_Tests_Only.bat`.

Manual setup from this folder:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python evaluate_chronorag.py data/real_documents.csv
python evaluate_change_detection.py
python test_chronorag.py
python -m streamlit run app.py
```

## Run the tests

```bat
python test_chronorag.py
python test_app_smoke.py
python evaluate_chronorag.py data/real_documents.csv
python evaluate_change_detection.py
```

The regression script writes `CHRONORAG_TEST_REPORT.txt`; the app-flow stub tests write `APP_FLOW_TEST_REPORT.txt`; the revision-selection script writes `chronorag_evaluation_results.csv`; the known-case change evaluation writes `change_detection_smoke_results.csv` and `CHANGE_DETECTION_EVALUATION.md`. The app-flow tests exercise app code paths with a stub Streamlit API and do not replace manual browser checks. Once the app is running, double-click `Verify_Live_App.bat` for a local HTTP health check.

## Current evaluation

The included standardized title-based evaluation found:

- **Baseline selected the correct document family:** 19/19 (100%) for these title-style queries.
- **Baseline selected the latest revision of the target family:** 7/19 (36.8%).
- **ChronoRAG selected the latest stored revision:** 19/19 (100%), as its rule explicitly chooses the maximum stored timestamp after selecting a family.
- **Core/data regression checks:** 66 passed, 0 failed. **App-flow smoke checks:** 15 passed, 0 failed with a mocked Streamlit API. **Known-case change checks:** 3/3 passed (two changed-text examples, one unchanged-topic negative control).

These results measure document-family/revision selection under this small standardized test, not contradiction-detection accuracy, answer correctness, or superiority on arbitrary natural-language questions. The 100% ChronoRAG figure is expected from the algorithm's latest-timestamp rule and should not be presented as contradiction accuracy.

## Live app health check

After `Install_and_Run.bat` has started Streamlit, use `Verify_Live_App.bat` to check the local HTTP health endpoint and the app page shell. This health check verifies that the server responds; it is not full click-by-click browser automation.

## Suggested browser smoke test

Choose **Real Wikipedia revisions** and **ChronoRAG version-aware retrieval**, then try:

1. `What changed between versions of the COVID-19 pandemic in Africa article regarding Botswana?`
   - Expected: text difference from “more than 100 people” to “more than 50 people”.
2. `What changed between versions of the COVID-19 pandemic in Africa article regarding Algeria?`
   - Expected for these two stored revisions: no Algeria-specific text difference found.
3. `What changed between versions of the ChuChu TV article?`
   - Expected: the earlier/later versions and a ranking/statistics text difference are shown.
4. Switch the same Botswana question between Baseline and ChronoRAG.
   - Expected: baseline selects revision `946148507`; ChronoRAG selects `946149857`.

## Known limitations and future work

- No external LLM generates an answer; the displayed revision is text retrieved from the selected document.
- TF-IDF uses lexical overlap and may fail when a question paraphrases the document. If a query has zero lexical overlap, the app now warns rather than displaying an arbitrary document. This guard only detects zero-overlap cases; it is not a calibrated relevance threshold.
- ChronoRAG assumes that the latest stored timestamp is the version wanted by the user. The newest stored revision may not be the current source version.
- Topic extraction and section parsing are keyword-based heuristics.
- Text changes can be corrections, additions, deletions, or normal time-dependent updates—not necessarily contradictions.
- Only two revisions per real-data document family are available in this collection.
- A verified contradiction dataset and blinded/manual labels are needed to measure contradiction precision, recall, and F1.
- An evaluation file containing 86 examples exists in the project history, but evidence-to-revision alignment must be audited before using it for benchmark claims.

## Research-safe conclusion

The prototype demonstrates a transparent way to retrieve the latest *stored* revision in a document family and compare it with an earlier version. Current tests support revision-selection behavior and known text-difference examples. More work is required before claiming reliable contradiction detection.
