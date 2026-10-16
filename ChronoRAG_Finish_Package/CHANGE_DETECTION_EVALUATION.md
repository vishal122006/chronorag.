# ChronoRAG Change-Detection Smoke Evaluation

**Result: 3/3 predefined checks passed.**

This is a small, manually specified smoke evaluation, not a representative benchmark. It contains two known changed-text examples and one unchanged-topic negative control.

| Case | Document/topic | Expected | Observed | Pass |
|---|---|---|---|---|
| CD-01 | COVID-19 pandemic in Africa / Botswana | changed | changed_as_expected | Yes |
| CD-02 | COVID-19 pandemic in Africa / Algeria | unchanged_topic | unchanged_topic | Yes |
| CD-03 | ChuChu TV / full document | changed | changed_as_expected | Yes |

## Interpretation and limitations

- The Botswana example verifies that the earlier `more than 100 people` text is removed and later `more than 50 people` text is added.
- The ChuChu TV example verifies that the earlier 42nd-place ranking and later 43rd-place ranking appear in the corresponding change outputs.
- The Algeria example is a negative control for these two stored revisions only; it does not establish that the section never changes in other revisions.
- A textual change is not automatically a contradiction. Changes may be corrections, new facts, time-dependent updates, additions, or deletions.
- These three cases are too small to support general precision, recall, F1, or contradiction-detection accuracy claims.
- Full contradiction evaluation requires a larger independently labelled dataset with clear claim-level labels and adjudication.

Machine-readable results: `change_detection_smoke_results.csv`.
