"""Reproducible evaluation for the ChronoRAG versioned CSV.

Usage:
  python evaluate_chronorag.py data/real_documents.csv
  python evaluate_chronorag.py data/real_documents.csv --output evaluation_results.csv

This evaluates revision selection with the same TF-IDF settings as app.py.
It does NOT measure contradiction-detection accuracy or answer correctness.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import difflib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REQUIRED = ["doc_id", "title", "version", "effective_date", "source", "text"]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="Path to real_documents.csv")
    parser.add_argument("--output", default="chronorag_evaluation_results.csv")
    args = parser.parse_args()
    path = Path(args.csv_path)
    docs = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in REQUIRED if c not in docs.columns]
    if missing:
        raise SystemExit("CSV is missing required columns: " + ", ".join(missing))
    docs = docs[REQUIRED].copy()
    docs["effective_date"] = pd.to_datetime(docs["effective_date"], errors="coerce", utc=True)
    docs = docs.dropna(subset=["effective_date"])
    docs = docs[(docs.doc_id.str.strip() != "") & (docs.text.str.strip() != "")].copy()
    if docs.empty:
        raise SystemExit("No usable document revisions found.")

    corpus = docs["title"] + " " + docs["text"]
    rows = []
    for doc_id, group in docs.groupby("doc_id", sort=True):
        group = group.sort_values("effective_date")
        title = str(group.iloc[-1]["title"])
        query = f"What changed between versions of the {title} article?"
        # Reproduce app.py retrieval settings on the complete collection.
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        matrix = vectorizer.fit_transform(corpus.tolist() + [query])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
        ranked = docs.copy()
        ranked["similarity"] = scores
        ranked = ranked.sort_values(["similarity", "effective_date"], ascending=[False, False])
        baseline = ranked.iloc[0]
        latest = group.sort_values("effective_date", ascending=False).iloc[0]
        earlier = group.sort_values("effective_date").iloc[0]
        matcher = difflib.SequenceMatcher(None, str(earlier.text), str(latest.text))
        changed = sum(1 for tag, *_ in matcher.get_opcodes() if tag != "equal")
        rows.append({
            "doc_id": doc_id,
            "title": title,
            "query_used": query,
            "stored_revision_count": len(group),
            "earliest_version": earlier.version,
            "earliest_timestamp_utc": earlier.effective_date.isoformat(),
            "latest_version": latest.version,
            "latest_timestamp_utc": latest.effective_date.isoformat(),
            "baseline_selected_doc_id": baseline.doc_id,
            "baseline_selected_version": baseline.version,
            "baseline_similarity": round(float(baseline.similarity), 6),
            "baseline_selected_latest_for_target_family": bool(baseline.doc_id == doc_id and baseline.version == latest.version),
            "chronorag_selected_version": latest.version,
            "chronorag_selected_latest_for_target_family": True,
            "text_diff_operation_count": changed,
            "note": "Text difference count is not a contradiction label; query is a standardized title-based test."
        })
    out = pd.DataFrame(rows).sort_values("title")
    out_path = Path(args.output)
    out.to_csv(out_path, index=False)
    total = len(out)
    baseline_latest = int(out["baseline_selected_latest_for_target_family"].sum())
    print(f"Document families tested: {total}")
    print(f"Baseline selected the latest target-family revision: {baseline_latest}/{total} ({baseline_latest/total:.1%})")
    print(f"ChronoRAG selected the latest stored revision by design: {total}/{total} (100.0%)")
    print("Note: these are revision-selection metrics, not contradiction-detection accuracy.")
    print(f"Results saved to: {out_path.resolve()}")

if __name__ == "__main__":
    main()
