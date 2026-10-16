"""Small, reproducible change-detection check for known ChronoRAG examples.

This is a smoke evaluation of three hand-checked cases, not a broad benchmark and
not a contradiction classifier. It tests whether the current text-comparison
logic surfaces known changed text and leaves one known unchanged topic alone.

Run:
    python evaluate_change_detection.py

Outputs:
    change_detection_smoke_results.csv
    CHANGE_DETECTION_EVALUATION.md
"""
from __future__ import annotations
import ast
import difflib
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent
REQUIRED_COLUMNS = ["doc_id", "title", "version", "effective_date", "source", "text"]
FUNCTIONS = {
    "normalize_documents", "clean_wikitext", "sentence_chunks", "compare_versions",
    "split_into_sections", "topic_terms_from_question", "section_passages_for_topic",
    "compare_topic_sections",
}


def load_core_functions():
    app_path = ROOT / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS]
    missing = FUNCTIONS - {node.name for node in nodes}
    if missing:
        raise RuntimeError(f"Missing comparison functions in app.py: {sorted(missing)}")
    namespace = {
        "Any": Any, "Path": Path, "pd": pd, "re": re, "difflib": difflib,
        "TfidfVectorizer": TfidfVectorizer, "cosine_similarity": cosine_similarity,
        "REQUIRED_COLUMNS": REQUIRED_COLUMNS,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(app_path), "exec"), namespace)
    return namespace


def run() -> int:
    f = load_core_functions()
    raw = pd.read_csv(ROOT / "data" / "real_documents.csv", dtype=str).fillna("")
    docs = f["normalize_documents"](raw)
    rows: list[dict[str, Any]] = []

    covid = docs[docs["title"].eq("COVID-19 pandemic in Africa")].sort_values("effective_date")
    if len(covid) != 2:
        raise RuntimeError(f"Expected two COVID-19 article revisions; found {len(covid)}")
    chu = docs[docs["title"].eq("ChuChu TV")].sort_values("effective_date")
    if len(chu) != 2:
        raise RuntimeError(f"Expected two ChuChu TV revisions; found {len(chu)}")

    cases = [
        {
            "case_id": "CD-01",
            "document": "COVID-19 pandemic in Africa",
            "topic": "Botswana",
            "query": "What changed between versions of the COVID-19 pandemic in Africa article regarding Botswana?",
            "expected": "changed",
            "old_text": covid.iloc[0]["text"],
            "new_text": covid.iloc[1]["text"],
            "topic_aware": True,
            "required_removed": "more than 100 people",
            "required_added": "more than 50 people",
            "interpretation": "A time-sensitive policy statement changed; this is not by itself proof of a logical contradiction.",
        },
        {
            "case_id": "CD-02",
            "document": "COVID-19 pandemic in Africa",
            "topic": "Algeria",
            "query": "What changed between versions of the COVID-19 pandemic in Africa article regarding Algeria?",
            "expected": "unchanged_topic",
            "old_text": covid.iloc[0]["text"],
            "new_text": covid.iloc[1]["text"],
            "topic_aware": True,
            "required_removed": "",
            "required_added": "",
            "interpretation": "Negative control: no Algeria-specific text change was found in these two stored revisions.",
        },
        {
            "case_id": "CD-03",
            "document": "ChuChu TV",
            "topic": "full document",
            "query": "What changed between versions of the ChuChu TV article?",
            "expected": "changed",
            "old_text": chu.iloc[0]["text"],
            "new_text": chu.iloc[1]["text"],
            "topic_aware": False,
            "required_removed": "42nd most subscribed",
            "required_added": "43rd most subscribed",
            "interpretation": "Reported ranking/statistics changed between stored revisions; the difference is not automatically a contradiction.",
        },
    ]

    for case in cases:
        if case["topic_aware"]:
            terms = f["topic_terms_from_question"](case["query"], case["document"])
            removed, added, note = f["compare_topic_sections"](case["old_text"], case["new_text"], terms)
        else:
            terms = []
            removed, added = f["compare_versions"](case["old_text"], case["new_text"])
            note = "No narrow topic was requested; the full document pair was compared."

        removed_text = "\n".join(removed)
        added_text = "\n".join(added)
        if case["expected"] == "unchanged_topic":
            passed = not removed and not added
            observed = "unchanged_topic" if passed else "changed"
        else:
            passed = bool(case["required_removed"] in removed_text and case["required_added"] in added_text)
            observed = "changed_as_expected" if passed else "expected_change_not_detected"

        rows.append({
            "case_id": case["case_id"],
            "document": case["document"],
            "topic": case["topic"],
            "query": case["query"],
            "expected_outcome": case["expected"],
            "observed_outcome": observed,
            "passed": passed,
            "required_removed_phrase": case["required_removed"],
            "required_added_phrase": case["required_added"],
            "removed_text": " || ".join(removed),
            "added_text": " || ".join(added),
            "method_note": note,
            "interpretation": case["interpretation"],
        })

    result = pd.DataFrame(rows)
    out_csv = ROOT / "change_detection_smoke_results.csv"
    out_md = ROOT / "CHANGE_DETECTION_EVALUATION.md"
    result.to_csv(out_csv, index=False, encoding="utf-8-sig")
    passed_count = int(result["passed"].sum())
    total = len(result)
    md = [
        "# ChronoRAG Change-Detection Smoke Evaluation",
        "",
        f"**Result: {passed_count}/{total} predefined checks passed.**",
        "",
        "This is a small, manually specified smoke evaluation, not a representative benchmark. It contains two known changed-text examples and one unchanged-topic negative control.",
        "",
        "| Case | Document/topic | Expected | Observed | Pass |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        md.append(f"| {row['case_id']} | {row['document']} / {row['topic']} | {row['expected_outcome']} | {row['observed_outcome']} | {'Yes' if row['passed'] else 'No'} |")
    md += [
        "",
        "## Interpretation and limitations",
        "",
        "- The Botswana example verifies that the earlier `more than 100 people` text is removed and later `more than 50 people` text is added.",
        "- The ChuChu TV example verifies that the earlier 42nd-place ranking and later 43rd-place ranking appear in the corresponding change outputs.",
        "- The Algeria example is a negative control for these two stored revisions only; it does not establish that the section never changes in other revisions.",
        "- A textual change is not automatically a contradiction. Changes may be corrections, new facts, time-dependent updates, additions, or deletions.",
        "- These three cases are too small to support general precision, recall, F1, or contradiction-detection accuracy claims.",
        "- Full contradiction evaluation requires a larger independently labelled dataset with clear claim-level labels and adjudication.",
        "",
        f"Machine-readable results: `{out_csv.name}`.",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("ChronoRAG Change-Detection Smoke Evaluation")
    print("==========================================")
    for row in rows:
        print(f"{'PASS' if row['passed'] else 'FAIL'}: {row['case_id']} - {row['document']} / {row['topic']}: {row['observed_outcome']}")
    print(f"\nTOTAL: {passed_count}/{total} checks passed.")
    print(f"CSV saved to: {out_csv}")
    print(f"Report saved to: {out_md}")
    return 0 if passed_count == total else 1


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"CHANGE-DETECTION EVALUATION FAILED: {exc}", file=sys.stderr)
        raise
