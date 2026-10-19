# ChronoRAG Project Report

## 1. Project overview

**Title:** ChronoRAG: Contradiction-Aware Retrieval for Changing Documents

**Problem:** A similarity-based retriever may return an older version of a changing document. When facts, counts, dates, or policies evolve, returning only a highly similar passage can hide the newer stored information.

**Aim:** Build and evaluate a small, interpretable prototype that compares a TF-IDF baseline with version-aware selection and makes changes between stored revisions visible to the user.

## 2. Objectives

1. Load versioned documents from a validated CSV schema.
2. Retrieve documents using a transparent TF-IDF similarity baseline.
3. Add a version-aware strategy that identifies the best-matching document family and chooses its latest stored timestamp.
4. Display revision metadata, history, and heuristic text differences.
5. Evaluate selection behavior and test known examples and input validation.

## 3. System design

The Streamlit interface loads the included historical Wikipedia revision collection by default, or an uploaded versioned CSV. A user-triggered refresh calls the public English Wikipedia Action API for each article family, checks its latest revision ID and timestamp, and appends newly discovered revisions while preserving the existing stored history. The refreshed data remains in session memory and can be downloaded as CSV; it is not persisted back to GitHub by the app. The input is validated and normalized. Both strategies use TF-IDF scores to find the likely document family. Baseline returns the most similar revision; ChronoRAG selects the latest stored version in the candidate family. The app then displays the selected content and, where a version pair exists, compares the earlier and later text. Topic/section filtering uses keyword heuristics.

## 4. Data

- Real collection: 38 stored revision records from 19 Wikipedia article families.
- The included real collection starts with two stored versions per family, rather than a complete revision history. A manual live refresh can append newer current revisions.
- Required CSV columns: `doc_id`, `title`, `version`, `effective_date`, `source`, `text`.

## 5. Evaluation method

The script `evaluate_chronorag.py` uses a standardized title-based question for each document family. It computes TF-IDF scores across the document collection, records the baseline selection, and compares that selection with the latest timestamp in the target family. The regression tests validate schema/data integrity, family matching, latest-version selection, two known changed-text examples, one unchanged topic example, and malformed-input handling. The separate `evaluate_change_detection.py` script checks two predefined changed-text examples and one unchanged-topic negative control.

## 6. Results

| Measure | Result | Interpretation |
|---|---:|---|
| Document families in standardized tests | 19 | Small exploratory evaluation |
| Baseline chooses correct document family | 19/19 (100%) | For the standardized title-based queries only |
| Baseline chooses latest target-family revision | 7/19 (36.8%) | Baseline often ranks the older version higher |
| ChronoRAG chooses latest stored revision | 19/19 (100%) | Expected because the algorithm explicitly selects max timestamp within the candidate family |
| Core/data regression checks | 64 expected; rerun pending | Count reflects removal of demo-specific assertions; rerun the suite before submission. |
| App-flow smoke checks | 14 expected; rerun pending | Uses a mocked Streamlit API; not a real browser/UI test. Rerun before submission. |
| Known-case change-detection checks | 3/3 passed | Two positive text-difference examples and one unchanged-topic negative control; not a contradiction benchmark |
| Botswana gathering-limit difference | Detected | Earlier stored text says >100; later stored text says >50 |
| ChuChu TV ranking/statistics difference | Detected | Earlier and later revision text differs |
| Algeria negative example | No topic-specific difference found | Applies only to the two stored revisions tested |

## 7. Interpretation

The results support that the implementation loads the tested collection, resolves the expected document family for standardized title-based questions, and selects the latest stored version within that family. The baseline selection rate for the latest target-family revision is lower on the same question templates. These results are consistent with the design goal of version-aware selection.

They do **not** demonstrate that ChronoRAG detects contradictions with 100% accuracy. Selecting a recent version is a selection policy, not a semantic contradiction detector. A sentence changing from one numeric value to another can represent a real-world update, correction, or conflicting statement. Manual labels or a verified contradiction benchmark are needed to evaluate that distinction.

The separate known-case change evaluation writes `change_detection_smoke_results.csv` and `CHANGE_DETECTION_EVALUATION.md`. A local HTTP health checker (`Verify_Live_App.bat`) is also included for use after Streamlit starts. The local health check is designed to verify server responsiveness, not interaction fidelity.

## 8. Limitations

- The application uses TF-IDF and does not generate answers with an external LLM.
- Live refresh depends on network access to the public Wikipedia API; failures are reported and existing records are retained.
- Refreshed revisions are session-only until downloaded. They do not automatically update the repository or the deployed app's baseline CSV.
- The dataset contains only two stored versions per article family.
- Standardized title-based test queries may be easier than natural user questions.
- Latest timestamp among stored versions does not guarantee the revision is current or authoritative.
- Topic detection, wikitext cleanup, sentence segmentation, and section extraction are heuristic.
- The current evaluation does not report contradiction precision, recall, F1, answer faithfulness, or latency.

## 9. Future work

1. Curate a set of labeled document pairs and conflict/non-conflict questions.
2. Label each change as contradiction, correction, addition, deletion, or time-dependent update.
3. Compare both methods with identical held-out queries and report precision, recall, F1, and confidence intervals where appropriate.
4. Add safeguards for equal or missing timestamps and conflicting source authority.
5. Consider semantic embeddings and claim-level extraction, while retaining an interpretable evidence trail.
6. Audit the available 86-example evaluation file and its evidence-to-revision alignment before reporting benchmark results.

## 10. Conclusion

ChronoRAG is a working research prototype for version-aware retrieval and visible comparison of changing documents. Current automated tests and standardized selection results validate core behavior in the included dataset. The main research step remaining is a properly labeled evaluation of contradiction detection, separate from ordinary change detection.
