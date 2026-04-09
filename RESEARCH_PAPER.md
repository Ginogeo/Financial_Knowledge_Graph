# Financial Knowledge Graph: A Hybrid RAG System for SEC 10-K Document Analysis

## Abstract

This paper presents a **Hybrid Retrieval-Augmented Generation (RAG) pipeline** for querying large financial documents — specifically SEC 10-K annual filings. The system combines a **Neo4j knowledge graph** with a **ChromaDB vector store** and an **NVIDIA-hosted large language model (LLM)** to answer analyst questions with high precision and minimal token overhead. A side-by-side Streamlit interface allows direct comparison between the naïve full-document approach and the optimised RAG pipeline, demonstrating substantial gains in retrieval precision and cost efficiency.

---

## 1. Introduction and Motivation

Annual SEC 10-K filings are dense, multi-section documents that regularly exceed 100,000 words. Feeding an entire filing into an LLM context window is wasteful and often impossible: the Coca-Cola 10-K used in this project totals 597,681 characters (~149,000 tokens), which exceeds the practical context budget of most production-grade models. Existing approaches either truncate the document (losing critical financial data) or send everything at once (incurring prohibitive API costs and degraded answer quality due to "lost-in-the-middle" attention failures).

The proposed system solves this by intelligently selecting only the document sections that are relevant to each query — typically reducing context to fewer than 20,000 characters (~5,000 tokens), a **95% reduction** — while still preserving cross-section dependencies captured in the knowledge graph.

---

## 2. System Architecture

The pipeline consists of four cooperating components:

### 2.1 Document Parser (`src/parser.py`)
The raw PDF is ingested using **pdfplumber** (recommended for SEC filings because of its accurate table detection). The parser identifies structural boundaries — `PREAMBLE`, `ITEM n`, `NOTE n`, and `PART n` headings — via regular expressions and serialises each section as a JSON object containing the section ID, full text, embedded HTML tables, detected cross-references, and word count. The cross-reference extractor scans body text for phrases such as *"see Note 15"* or *"as described in Item 7A"*, producing directed edge data that is later loaded into the graph.

### 2.2 Knowledge Graph (`src/build_graph.py`)
A **Neo4j** graph database stores two node types — `Document` and `Section` — connected by `HAS_SECTION` and `REFERS_TO` relationships. `REFERS_TO` edges are built directly from the cross-references extracted during parsing. This structure makes it possible to follow citation chains at query time: if the vector search surfaces *Item 7*, the graph traversal can immediately retrieve all sections that Item 7 cites (e.g., Notes 1, 5, and 15), ensuring no related financial context is silently omitted.

### 2.3 Vector Store (`src/build_vector.py`)
Each section's text is cleaned (page numbers and repeated headers are stripped) and split into semantically coherent chunks of ≤ 1,000 characters with a 200-character overlap to prevent boundary loss. Every chunk is prefixed with its section ID before being embedded with a **SentenceTransformer** model and indexed in **ChromaDB**. Semantic chunking on paragraph boundaries — rather than fixed character windows — preserves the topical integrity of financial disclosures.

### 2.4 Hybrid Search (`src/hybrid_search.py`)
At query time, the system performs a two-stage retrieval:

1. **Semantic vector search** — the top-10 most similar chunks are fetched from ChromaDB. Chunks from the same section are merged, and the best-matching section ID is forwarded to the graph.
2. **Graph traversal** — Neo4j returns every section linked to the primary hit via `REFERS_TO`, and their full text is fetched from ChromaDB.

The combined context (primary chunks + graph-connected sections) is formatted with the document **PREAMBLE** always prepended, ensuring the LLM receives essential company background regardless of query topic.

---

## 3. LLM Integration and Evaluation (`src/nvidia_llm.py`, `app.py`)

The formatted context and user question are sent to an **NVIDIA-hosted LLM** (default: `meta/llama-3.1-8b-instruct`) via an OpenAI-compatible API endpoint. A Streamlit application presents two answers side-by-side: the naïve full-document answer and the RAG-optimised answer. Efficiency metrics — context size, token savings, and number of retrieved chunks — are displayed in real time after each query.

---

## 4. Key Contributions

| Contribution | Description |
|---|---|
| Graph-augmented retrieval | Cross-reference edges prevent silent omission of related financial disclosures |
| Semantic chunking with overlap | Paragraph-boundary splitting preserves financial statement integrity |
| Always-on PREAMBLE grounding | Company context is always in scope regardless of which section is matched |
| 95% token reduction | Reduces per-query cost from ~149 k to ~5 k tokens while maintaining answer quality |
| Side-by-side benchmarking UI | Direct comparison of naïve vs. optimised approaches on live queries |

---

## 5. Conclusion

This system demonstrates that combining a **structural knowledge graph** with **semantic vector retrieval** is substantially superior to naïve full-document dumping for financial document QA. The graph component is essential for financial filings in particular, where numerical disclosures in one section routinely reference definitions and prior-year comparatives buried in footnotes. The result is a production-ready, cost-efficient RAG pipeline capable of answering complex analyst questions from multi-hundred-page SEC filings within seconds.
