# ChronoRAG Architecture

```mermaid
flowchart TD
    A[User question] --> B[Streamlit interface]
    C[Built-in CSV or uploaded versioned CSV] --> D[Validate schema and normalize timestamps]
    D --> E[Document collection]
    B --> F[TF-IDF vectorization and cosine similarity]
    E --> F
    F --> G[Candidate document family]
    G --> H{Retrieval strategy}
    H --> I[Baseline: highest-similarity revision]
    H --> J[ChronoRAG: latest stored timestamp]
    I --> K[Selected revision]
    J --> K
    K --> L[Show text, source, timestamp, score, and history]
    E --> M[Earlier/later revision pair]
    M --> N[Clean wikitext and split into sentences/sections]
    N --> O[Heuristic text-difference comparison]
    O --> P[Show removed/modified and added/modified text]
    L --> Q[User interprets evidence]
    P --> Q
```

## Component summary

- **Interface:** Streamlit controls for dataset, upload, retrieval strategy, and question.
- **Validation:** Requires `doc_id`, `title`, `version`, `effective_date`, `source`, and `text`; malformed rows are filtered or rejected with a message.
- **Retrieval baseline:** TF-IDF using unigrams/bigrams and cosine similarity.
- **Version-aware rule:** Uses the best matching family and selects its most recent stored timestamp.
- **Comparison:** Cleans basic Wikipedia markup, splits approximate sentences/sections, and reports text that differs.
- **Important boundary:** Comparison reports textual changes only; it does not prove semantic contradiction.
