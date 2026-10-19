from __future__ import annotations

from pathlib import Path
from typing import Any
import difflib
import re

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).parent
REAL_DATA_PATH = ROOT / "data" / "real_documents.csv"

REQUIRED_COLUMNS = ["doc_id", "title", "version", "effective_date", "source", "text"]

st.set_page_config(
    page_title="ChronoRAG | Changing-Document Assistant",
    page_icon="🕒",
    layout="wide",
)


@st.cache_data
def load_csv(path_string: str) -> pd.DataFrame:
    return pd.read_csv(path_string, dtype=str).fillna("")


def normalize_documents(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    out = df[REQUIRED_COLUMNS].copy().fillna("")
    for column in ["doc_id", "title", "version", "source", "text"]:
        out[column] = out[column].astype(str).str.strip()

    out["effective_date"] = pd.to_datetime(
        out["effective_date"], errors="coerce", utc=True
    )
    out = out.dropna(subset=["effective_date"])
    out = out[(out["doc_id"] != "") & (out["text"] != "")]
    if out.empty:
        raise ValueError("No usable document versions were found.")
    return out.reset_index(drop=True)


def load_documents() -> pd.DataFrame:
    """Load only the included historical Wikipedia revision collection."""
    if not REAL_DATA_PATH.exists():
        raise FileNotFoundError(f"Real revision dataset not found: {REAL_DATA_PATH}")
    return normalize_documents(load_csv(str(REAL_DATA_PATH)))


def retrieve_documents(query: str, docs: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """Transparent TF-IDF retrieval baseline."""
    corpus = docs["title"].fillna("") + " " + docs["text"].fillna("")
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), sublinear_tf=True
    )
    matrix = vectorizer.fit_transform(corpus.tolist() + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    results = docs.copy()
    results["similarity"] = scores
    results = results.sort_values(
        ["similarity", "effective_date"], ascending=[False, False]
    )
    return results.head(min(top_k, len(results))).reset_index(drop=True)


def find_candidate_group(query: str, docs: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    ranked = retrieve_documents(query, docs, top_k=len(docs))
    best_match = ranked.iloc[0]
    group = ranked[ranked["doc_id"] == best_match["doc_id"]].copy()
    group = group.sort_values("effective_date", ascending=False)
    return best_match, group


def choose_latest_version(group: pd.DataFrame) -> pd.Series:
    return group.sort_values("effective_date", ascending=False).iloc[0]


def format_date(value: Any) -> str:
    try:
        return pd.Timestamp(value).strftime("%d %b %Y %H:%M UTC")
    except Exception:
        return str(value)


def display_history(group: pd.DataFrame) -> pd.DataFrame:
    history = group[["title", "version", "effective_date", "source"]].copy()
    history["effective_date"] = history["effective_date"].map(format_date)
    return history


def clean_wikitext(text: str) -> str:
    """Make a readable approximation of Wikipedia wikitext."""
    text = str(text or "")
    text = re.sub(r"<ref\b[^>]*>.*?</ref>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<ref\b[^>]*/\s*>", " ", text, flags=re.I)
    text = re.sub(r"\[\[(?:File|Image):.*?\]\]", " ", text, flags=re.I | re.S)

    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\{\{[^{}]*\}\}", " ", text)

    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"^\s*=+\s*|\s*=+\s*$", " ", text, flags=re.M)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentence_chunks(text: str) -> list[str]:
    readable = clean_wikitext(text)
    chunks = re.split(r"(?<=[.!?])\s+", readable)
    return [chunk.strip() for chunk in chunks if len(chunk.strip()) > 20]


def compare_versions(
    older_text: str, newer_text: str, limit: int = 8
) -> tuple[list[str], list[str]]:
    """Return a small, readable list of sentence-level additions/removals."""
    old_chunks = sentence_chunks(older_text)
    new_chunks = sentence_chunks(newer_text)
    matcher = difflib.SequenceMatcher(a=old_chunks, b=new_chunks, autojunk=False)
    removed: list[str] = []
    added: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            removed.extend(old_chunks[i1:i2])
        if tag in ("insert", "replace"):
            added.extend(new_chunks[j1:j2])
    return list(dict.fromkeys(removed))[:limit], list(dict.fromkeys(added))[:limit]


def split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split heading-marked text into sections, preserving each section heading."""
    text = str(text or "")
    # Wikipedia headings use == Heading == or === Subheading ===.
    matches = list(re.finditer(r"(?m)^\s*(={2,6})\s*(.*?)\s*\1\s*$", text))
    if not matches:
        return [("Document", clean_wikitext(text))]

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        intro = clean_wikitext(text[:matches[0].start()])
        if intro:
            sections.append(("Introduction", intro))

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = re.sub(r"\s+", " ", match.group(2)).strip() or "Untitled section"
        body = clean_wikitext(text[start:end])
        sections.append((heading, body))
    return sections


def topic_terms_from_question(question: str, title: str) -> list[str]:
    """Extract a simple topic hint from phrases such as 'regarding Algeria'."""
    q = question.lower()
    stop = {
        "what", "changed", "between", "versions", "version", "the", "article",
        "information", "about", "regarding", "in", "on", "of", "for", "and",
        "does", "say", "latest", "stored", "please", "pandemic", "africa",
    }
    patterns = [
        r"\bregarding\s+(.+?)(?:[?.!,]|$)",
        r"\bspecifically\s+about\s+(.+?)(?:[?.!,]|$)",
        r"\babout\s+(.+?)(?:\s+article)?(?:[?.!,]|$)",
    ]
    candidate = ""
    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            candidate = match.group(1).strip()
            break

    terms = [
        token for token in re.findall(r"[a-z0-9-]+", candidate)
        if token not in stop and len(token) > 1
    ]
    title_terms = [
        token for token in re.findall(r"[a-z0-9-]+", title.lower())
        if token not in stop and len(token) > 1
    ]
    if terms and terms != title_terms and not all(term in title.lower() for term in terms):
        return terms
    return []


def section_passages_for_topic(text: str, topic_terms: list[str]) -> list[tuple[str, str]]:
    """Find heading sections or sentence passages relevant to topic terms."""
    sections = split_into_sections(text)
    matches = []
    for heading, body in sections:
        heading_and_body = f"{heading} {body}".lower()
        if any(term in heading_and_body for term in topic_terms):
            matches.append((heading, body))

    if matches:
        return matches

    # Many imported Wikipedia extracts have flattened headings. Fall back to
    # sentences that mention the topic and their immediate neighbours.
    sentences = sentence_chunks(text)
    relevant = []
    for i, sentence in enumerate(sentences):
        if any(term in sentence.lower() for term in topic_terms):
            start = max(0, i - 1)
            end = min(len(sentences), i + 2)
            relevant.append(("Topic-matching passage", " ".join(sentences[start:end])))
    # De-duplicate repeated passages.
    unique = []
    seen = set()
    for item in relevant:
        if item[1] not in seen:
            unique.append(item)
            seen.add(item[1])
    return unique


def compare_topic_sections(
    older_text: str,
    newer_text: str,
    topic_terms: list[str],
    limit: int = 8,
) -> tuple[list[str], list[str], str]:
    """Compare only section/passages that match the requested topic."""
    if not topic_terms:
        removed, added = compare_versions(older_text, newer_text, limit)
        return removed, added, "No narrow topic was detected; comparing the full document."

    old_sections = section_passages_for_topic(older_text, topic_terms)
    new_sections = section_passages_for_topic(newer_text, topic_terms)
    if not old_sections and not new_sections:
        return [], [], "No section or passage mentioning the requested topic was found in either version."

    old_text = "\n".join(f"{heading}. {body}" for heading, body in old_sections)
    new_text = "\n".join(f"{heading}. {body}" for heading, body in new_sections)
    removed, added = compare_versions(old_text, new_text, limit)
    note = (
        "Compared topic-matching sections/passages for: " + ", ".join(topic_terms)
        + ". Section extraction is heuristic and may miss indirect references."
    )
    return removed, added, note


st.title("🕒 ChronoRAG")
st.subheader("Contradiction-aware retrieval for changing documents")
st.write(
    "A research prototype comparing similarity-based retrieval with version-aware "
    "retrieval over changing documents. It currently uses TF-IDF and does not "
    "generate answers with an external LLM."
)

with st.sidebar:
    st.header("Document collection")
    st.caption("Default dataset: historical Wikipedia revisions (38 stored revisions across 19 article families).")
    uploaded_file = st.file_uploader("Or upload a versioned CSV", type=["csv"])
    mode = st.radio(
        "Retrieval strategy",
        ["Baseline RAG retrieval", "ChronoRAG version-aware retrieval"],
        index=1,
        help="Baseline returns the highest-similarity revision. ChronoRAG identifies its document family and selects the latest stored revision.",
    )
    show_all = st.checkbox("Show all document versions", value=False)

try:
    if uploaded_file is not None:
        documents = normalize_documents(pd.read_csv(uploaded_file, dtype=str).fillna(""))
        st.success(f"Loaded {len(documents)} uploaded document versions.")
    else:
        documents = load_documents()
        st.warning(
            "Using the included real-data collection: 38 stored revision records across 19 Wikipedia article families. "
            "Only two stored versions per page are included; this is not a complete revision history."
        )
except Exception as exc:
    st.error(f"Could not load documents: {exc}")
    st.stop()

st.markdown("### Ask a question")
sample_questions = [
    "What changed between versions of Westlife?",
    "What does the page say about sales?",
    "What information changed in the COVID-19 pandemic in Africa article?",
    "What changed between versions of the COVID-19 pandemic in Africa article regarding Algeria?",
    "What is the latest stored version of ChuChu TV?",
]

selected_sample = st.selectbox("Example question", ["Choose an example…"] + sample_questions)
question = st.text_input(
    "Your question",
    value="" if selected_sample == "Choose an example…" else selected_sample,
    placeholder="Enter a question about the document collection",
)

if question.strip():
    ranked = retrieve_documents(question.strip(), documents, top_k=min(6, len(documents)))
    best_match, version_group = find_candidate_group(question.strip(), documents)

    if mode == "Baseline RAG retrieval":
        answer = best_match
        st.markdown("### Baseline retrieval result")
        st.info("The baseline selects the highest-similarity revision. It does not explicitly resolve conflicting versions.")
    else:
        answer = choose_latest_version(version_group)
        st.markdown("### ChronoRAG result")
        if len(version_group) > 1:
            if version_group["text"].nunique() > 1:
                st.warning(
                    f"Found {len(version_group)} stored versions for **{answer['title']}**. "
                    "ChronoRAG selects the latest stored timestamp. This does not, by itself, prove that a contradiction exists."
                )
            else:
                st.success("Multiple versions found, but their stored text is identical.")
        else:
            st.info("Only one version was found for the selected document family.")

    st.markdown(f"**{answer['title']} — Revision {answer['version']}**")
    readable_answer = clean_wikitext(str(answer["text"]))
    preview_limit = 1400
    st.write(readable_answer[:preview_limit] + ("…" if len(readable_answer) > preview_limit else ""))
    if len(readable_answer) > preview_limit:
        with st.expander("Show full cleaned revision text"):
            st.write(readable_answer)

    st.caption(
        f"Document: {answer['doc_id']} · Revision timestamp: {format_date(answer['effective_date'])} · "
        f"Source: {answer['source']} · Similarity score: {float(answer.get('similarity', 0)):.3f}"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Stored version history")
        st.dataframe(display_history(version_group), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("#### Top retrieved revisions")
        view = ranked[["title", "version", "effective_date", "similarity", "source"]].copy()
        view["effective_date"] = view["effective_date"].map(format_date)
        view["similarity"] = view["similarity"].map(lambda score: f"{score:.3f}")
        st.dataframe(view, use_container_width=True, hide_index=True)

    if len(version_group) > 1:
        st.markdown("#### Compare stored versions")
        ordered = version_group.sort_values("effective_date", ascending=True)
        older = ordered.iloc[0]
        newer = ordered.iloc[-1]
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Earlier revision: {older['version']}**")
            st.caption(format_date(older["effective_date"]))
            older_readable = clean_wikitext(str(older["text"]))
            st.write(older_readable[:900] + ("…" if len(older_readable) > 900 else ""))
            if len(older_readable) > 900:
                with st.expander("Show full earlier revision"):
                    st.write(older_readable)
        with right:
            st.markdown(f"**Later revision: {newer['version']}**")
            st.caption(format_date(newer["effective_date"]))
            newer_readable = clean_wikitext(str(newer["text"]))
            st.write(newer_readable[:900] + ("…" if len(newer_readable) > 900 else ""))
            if len(newer_readable) > 900:
                with st.expander("Show full later revision"):
                    st.write(newer_readable)

        st.markdown("#### Detected text changes")
        topic_terms = topic_terms_from_question(question.strip(), str(answer["title"]))
        removed, added, comparison_note = compare_topic_sections(
            str(older["text"]), str(newer["text"]), topic_terms
        )
        st.caption(comparison_note)
        if not removed and not added:
            st.info(
                "No changes were detected in the selected comparison passages. "
                "This does not prove that no relevant change exists; section extraction and sentence comparison are heuristic."
            )
        else:
            st.caption("These are text differences, not automatically verified contradictions. Only the first few differences are shown.")
            change_left, change_right = st.columns(2)
            with change_left:
                st.markdown("**Removed or modified in the later version**")
                if removed:
                    for item in removed:
                        st.markdown(f"- ~~{item}~~")
                else:
                    st.write("No removed sentences detected in the selected passages.")
            with change_right:
                st.markdown("**Added or modified in the later version**")
                if added:
                    for item in added:
                        st.markdown(f"- {item}")
                else:
                    st.write("No added sentences detected in the selected passages.")

    if show_all:
        st.markdown("#### All loaded revisions")
        all_versions = documents[["title", "version", "effective_date", "source", "doc_id"]].copy()
        all_versions["effective_date"] = all_versions["effective_date"].map(format_date)
        st.dataframe(all_versions, use_container_width=True, hide_index=True)
else:
    st.write("Choose an example question or enter your own question to compare retrieval strategies.")

with st.expander("Research notes and limitations"):
    st.markdown(
        """
- This is a retrieval prototype, not a full generative RAG system.
- TF-IDF similarity is a baseline, not a semantic understanding model.
- The real collection has 38 stored revision records from 19 pages.
- The newest timestamp among the stored revisions is not necessarily the current version of the Wikipedia page.
- The VitaminC evaluation dataset has 86 examples, but evidence-to-revision alignment still requires verification. Do not report benchmark metrics as validated until that audit is complete.
- Wikipedia markup cleanup and section extraction are approximate.
- The app includes topic-aware section/passage comparison, but keyword matching can miss indirect references.
- Detected text changes do not prove contradictions.
- For a fair experiment, use the same queries and evaluation protocol for baseline retrieval and ChronoRAG, and document any limitations.
        """
    )
