"""Offline regression tests for ChronoRAG's data and core retrieval logic.

Run from the project folder:
    python test_chronorag.py

This loads utility functions directly from app.py so tests do not require a
browser or a running Streamlit server. It still requires the packages in
requirements.txt.
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
REQUIRED = ["doc_id", "title", "version", "effective_date", "source", "text"]
FUNCTIONS = {
    "normalize_documents", "retrieve_documents", "has_relevant_match", "find_candidate_group",
    "choose_latest_version", "clean_wikitext", "sentence_chunks",
    "compare_versions", "append_live_revision_if_new", "split_into_sections", "topic_terms_from_question",
    "section_passages_for_topic", "compare_topic_sections",
}


def load_core_functions():
    app_path = ROOT / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS]
    loaded_names = {node.name for node in nodes}
    missing = FUNCTIONS - loaded_names
    if missing:
        raise AssertionError(f"Could not load core app functions: {sorted(missing)}")
    namespace = {
        "Any": Any, "Path": Path, "pd": pd, "re": re, "difflib": difflib,
        "TfidfVectorizer": TfidfVectorizer,
        "cosine_similarity": cosine_similarity,
        "REQUIRED_COLUMNS": REQUIRED,
    }
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace


def check(condition: bool, message: str, results: list[str]) -> None:
    if not condition:
        raise AssertionError(message)
    results.append("PASS: " + message)


def run() -> int:
    funcs = load_core_functions()
    results: list[str] = []
    data_path = ROOT / "data" / "real_documents.csv"
    real_raw = pd.read_csv(data_path, dtype=str).fillna("")

    # File/schema/data integrity.
    check(list(real_raw.columns) == REQUIRED, "real dataset has all 6 required columns", results)
    real = funcs["normalize_documents"](real_raw)
    check(len(real) == 38 and real.doc_id.nunique() == 19, "real dataset has 38 valid revisions across 19 families", results)
    check(real.groupby("doc_id").size().eq(2).all(), "every real-data family has exactly two stored revisions", results)
    check(not real.duplicated().any(), "real dataset has no exact duplicate rows", results)
    check(not real.duplicated(["doc_id", "version"]).any(), "real dataset has no duplicate family/version keys", results)
    check(real.effective_date.notna().all() and real.text.str.strip().ne("").all(), "all real revisions have valid timestamps and non-empty text", results)

    # Live-refresh merge tests use a real article family as the base fixture.
    latest = real[real.title.eq("COVID-19 pandemic in Africa")].sort_values("effective_date").iloc[-1]
    existing_revision = {
        "version": str(latest.version),
        "effective_date": str(latest.effective_date),
        "text": str(latest.text),
    }
    unchanged_docs, was_added = funcs["append_live_revision_if_new"](
        real, str(latest.doc_id), existing_revision
    )
    check(not was_added and len(unchanged_docs) == len(real),
          "live refresh does not duplicate an already stored revision ID", results)

    new_revision = {
        "version": "TEST-ONLY-NEW-REVISION",
        "effective_date": "2030-01-01T00:00:00Z",
        "text": str(latest.text) + " Test-only content for merge validation.",
    }
    extended_docs, was_added = funcs["append_live_revision_if_new"](
        real, str(latest.doc_id), new_revision
    )
    check(was_added and len(extended_docs) == len(real) + 1
          and extended_docs.iloc[-1]["source"] == "wikipedia_live_api",
          "live refresh appends an unseen revision while preserving previous history", results)
    # Each title-based standard query should identify the intended family.
    baseline_latest_count = 0
    baseline_correct_family_count = 0
    all_families_latest_count = 0
    for doc_id, group in real.groupby("doc_id", sort=True):
        group = group.sort_values("effective_date")
        title = str(group.iloc[-1].title)
        query = f"What changed between versions of the {title} article?"
        best, selected_group = funcs["find_candidate_group"](query, real)
        latest = funcs["choose_latest_version"](selected_group)
        check(best.doc_id == doc_id, f"title query identifies correct family: {title}", results)
        baseline_correct_family_count += int(best.doc_id == doc_id)
        baseline_latest_count += int(best.doc_id == doc_id and str(best.version) == str(group.iloc[-1].version))
        all_families_latest_count += int(str(latest.version) == str(group.iloc[-1].version))
        check(str(latest.version) == str(group.iloc[-1].version), f"ChronoRAG latest selection is chronological: {title}", results)

    check(baseline_correct_family_count == 19, "baseline title-based query selects the correct family in 19/19 standardized tests", results)
    check(baseline_latest_count == 7, "baseline selects the latest target-family revision in 7/19 standardized tests", results)
    check(all_families_latest_count == 19, "ChronoRAG selects the latest timestamp in 19/19 families", results)

    # Known text changes should be detected in the appropriate direction.
    covid = real[real.title.eq("COVID-19 pandemic in Africa")].sort_values("effective_date")
    removed, added = funcs["compare_versions"](covid.iloc[0].text, covid.iloc[-1].text)
    check(any("more than 100 people" in x for x in removed), "Botswana earlier limit (>100 people) appears in removed text", results)
    check(any("more than 50 people" in x for x in added), "Botswana later limit (>50 people) appears in added text", results)

    chuchu = real[real.title.eq("ChuChu TV")].sort_values("effective_date")
    removed, added = funcs["compare_versions"](chuchu.iloc[0].text, chuchu.iloc[-1].text)
    check(any("42nd most subscribed" in x for x in removed), "ChuChu TV earlier ranking (42nd) appears in removed text", results)
    check(any("43rd most subscribed" in x for x in added), "ChuChu TV later ranking (43rd) appears in added text", results)

    # Algeria is a negative example in these particular stored revisions.
    q = "What changed between versions of the COVID-19 pandemic in Africa article regarding Algeria?"
    topic_terms = funcs["topic_terms_from_question"](q, "COVID-19 pandemic in Africa")
    removed, added, _ = funcs["compare_topic_sections"](covid.iloc[0].text, covid.iloc[-1].text, topic_terms)
    check(topic_terms == ["algeria"], "Algeria question identifies the requested topic", results)
    check(not removed and not added, "no Algeria-specific text difference is found in these two stored revisions", results)

    # Guard against malformed CSV schema.
    try:
        funcs["normalize_documents"](pd.DataFrame({"title": ["bad input"]}))
    except ValueError as exc:
        check("Missing required columns" in str(exc), "malformed CSV input returns a clear missing-columns error", results)
    else:
        raise AssertionError("Malformed CSV input was unexpectedly accepted")

    # Additional regression tests: edge cases and data cleaning.
    same_removed, same_added = funcs["compare_versions"](covid.iloc[0].text, covid.iloc[0].text)
    check(not same_removed and not same_added, "comparing a revision with itself reports no text differences", results)

    readable = funcs["clean_wikitext"]("This is [[a link|linked text]].<ref>citation</ref> ''bold''.")
    check("linked text" in readable and "citation" not in readable and "bold" in readable, "wikitext cleanup keeps link labels and removes refs/formatting", results)

    sections = funcs["split_into_sections"]("Intro text\n=== Botswana ===\nGatherings over 100.\n=== Benin ===\nFirst case reported.")
    check(any(h == "Botswana" and "100" in body for h, body in sections), "section parser extracts Botswana heading and body", results)
    check(any(h == "Benin" and "First case" in body for h, body in sections), "section parser keeps adjacent country sections separate", results)

    bot_q = "What changed between versions of the COVID-19 pandemic in Africa article regarding Botswana?"
    bot_terms = funcs["topic_terms_from_question"](bot_q, "COVID-19 pandemic in Africa")
    b_removed, b_added, _ = funcs["compare_topic_sections"](covid.iloc[0].text, covid.iloc[-1].text, bot_terms)
    check(bot_terms == ["botswana"], "Botswana question extracts the correct topic term", results)
    check(any("more than 100 people" in x for x in b_removed) and any("more than 50 people" in x for x in b_added), "topic-aware comparison detects Botswana change in correct direction", results)

    no_match = funcs["retrieve_documents"]("zxqvbn kjhgfds qqqqwwwee", real, top_k=5)
    has_match = funcs["retrieve_documents"]("What changed between versions of ChuChu TV?", real, top_k=5)
    check(not funcs["has_relevant_match"](no_match), "all-zero TF-IDF query is recognized as having no lexical match", results)
    check(funcs["has_relevant_match"](has_match), "relevant title query passes the lexical-match guard", results)
    check("No lexical match was found in this collection" in (ROOT / "app.py").read_text(encoding="utf-8"), "app warns instead of returning a random document for zero-overlap queries", results)

    invalid = pd.DataFrame({c: [""] for c in REQUIRED})
    try:
        funcs["normalize_documents"](invalid)
    except ValueError as exc:
        check("No usable document versions" in str(exc), "dataset with no usable revisions is rejected clearly", results)
    else:
        raise AssertionError("Dataset with no usable revisions was unexpectedly accepted")

    report = ROOT / "CHRONORAG_TEST_REPORT.txt"
    header = [
        "ChronoRAG Automated Test Report",
        "================================",
        f"Real dataset: {len(real)} rows, {real.doc_id.nunique()} document families",
        f"Baseline latest-target revision: {baseline_latest_count}/19",
        f"Baseline correct document family: {baseline_correct_family_count}/19",
        f"ChronoRAG latest stored revision: {all_families_latest_count}/19",
        "Caution: latest-revision selection is not contradiction-detection accuracy.",
        "",
        *results,
        "",
        f"TOTAL: {len(results)} checks passed; 0 failures.",
    ]
    report.write_text("\n".join(header) + "\n", encoding="utf-8")
    print("\n".join(header[:8]))
    print(f"\nTOTAL: {len(results)} checks passed; 0 failures.")
    print(f"Report saved to: {report}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"TEST FAILURE: {exc}", file=sys.stderr)
        raise
