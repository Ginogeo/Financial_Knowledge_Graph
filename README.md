# 💰 Financial Knowledge Graph with Hybrid RAG

A **financial question-answering system** that combines **Knowledge Graphs, vector retrieval, and Large Language Models (LLMs)** to provide context-aware answers from financial documents.

The project uses a **hybrid retrieval approach**, combining the structured relationships captured by a Knowledge Graph with semantic similarity search from a vector database. This allows the system to retrieve both **explicit relationships** and **semantically relevant information** before generating an answer.

---

## 📌 Overview

Financial documents contain large amounts of interconnected information about companies, people, financial events, markets, and relationships.

Traditional keyword-based search can struggle to understand these connections. A user asking:

> *"What companies are associated with this financial event?"*

may need information scattered across multiple sections of a document.

This project addresses that problem by combining:

* **Knowledge Graphs** for structured relationships
* **Vector embeddings** for semantic retrieval
* **LLMs** for natural-language question answering
* **Retrieval-Augmented Generation (RAG)** to ground generated answers in retrieved information

The overall pipeline can be summarized as:

```text
Financial Documents
        ↓
Document Processing
        ↓
Chunking / Slicing
        ↓
Information Extraction
        ↓
 ┌───────────────┬────────────────┐
 ↓               ↓                ↓
Knowledge      Vector           Metadata
Graph          Database         / Documents
 ↓               ↓
 └───────┬───────┘
         ↓
   Hybrid Retrieval
         ↓
      LLM / RAG
         ↓
    Final Answer
```

---

## ✨ Key Features

### 🔹 1. Financial Knowledge Graph

Financial information is represented as interconnected entities and relationships rather than isolated pieces of text.

The graph can capture relationships between entities such as:

* Companies
* People
* Financial entities
* Events
* Concepts
* Other relevant entities extracted from financial documents

This enables relationship-based retrieval and contextual reasoning.

---

### 🔹 2. Vector-Based Semantic Retrieval

Documents are processed into smaller chunks and represented using vector embeddings.

Semantic retrieval allows the system to find information based on **meaning**, rather than relying only on exact keyword matches.

For example:

```text
Query:
"How did the company's acquisition affect its business?"

        ↓

Semantic Retrieval

        ↓

Relevant document sections
```

---

### 🔹 3. Hybrid RAG

The project combines two complementary retrieval strategies:

**Knowledge Graph retrieval**

```text
Entity → Relationship → Entity
```

and

**Vector retrieval**

```text
Query → Embedding → Similar Documents
```

The retrieved information is then provided as context to the language model.

This helps the LLM generate responses based on the available financial knowledge instead of relying solely on its pretrained knowledge.

---

### 🔹 4. Context-Aware Question Answering

Users can interact with the financial knowledge base using natural-language questions.

Instead of requiring users to know database query languages such as Cypher or SQL, the system is designed around natural-language interaction.

Example:

```text
User:
"What companies are connected to this financial event?"

        ↓

Query Processing

        ↓

Hybrid Retrieval

        ↓

Relevant Graph + Document Context

        ↓

LLM

        ↓

Natural Language Answer
```

---

### 🔹 5. Retrieval Testing

The repository includes retrieval testing utilities for evaluating whether relevant information is successfully retrieved for a given query.

Files such as:

* `test_retrieval.py`
* `tester.ipynb`

are used for experimenting with and validating the retrieval pipeline.

---

## 🧠 Architecture

The system follows a Retrieval-Augmented Generation architecture:

```text
                    ┌─────────────────────┐
                    │ Financial Documents │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Document Processing │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Chunking / Slicing  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │ Knowledge Graph │         │ Vector Database │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 └─────────────┬─────────────┘
                               ▼
                     ┌──────────────────┐
                     │ Hybrid Retrieval │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ Retrieved Context│
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │      LLM         │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ Generated Answer │
                     └──────────────────┘
```

---

## 🛠️ Technology Stack

| Component              | Technology                      |
| ---------------------- | ------------------------------- |
| Programming Language   | Python                          |
| Knowledge Graph        | Neo4j                           |
| Vector Retrieval       | ChromaDB                        |
| LLM / Generative AI    | LLM-based RAG                   |
| Retrieval              | Hybrid Graph + Vector Retrieval |
| Data Processing        | Python                          |
| Backend / Interface    | Flask                           |
| Environment Management | `.env`                          |
| Experimentation        | Jupyter Notebook                |

---

## 📂 Project Structure

```text
Financial_Knowledge_Graph/
│
├── data/
│   └──                 # Financial data / processed resources
│
├── src/
│   ├──                # Core project modules
│   └──
│
├── app.py              # Application entry point
│
├── slicer.py           # Document slicing / chunking
│
├── debug_parser.py     # Parser debugging utilities
│
├── test_retrieval.py   # Retrieval testing
│
├── tester.ipynb        # Interactive experimen
```

