import os
import sys
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, SessionExpired, ServiceUnavailable

# Add src directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, EMBEDDING_MODEL

# 1. Bulletproof Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# 2. Connect Databases
chroma_client = chromadb.PersistentClient(path=DB_PATH)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

URI = NEO4J_URI
AUTH = (NEO4J_USER, NEO4J_PASSWORD)
neo4j_driver = GraphDatabase.driver(URI, auth=AUTH)


def _collection_name(document_id: Optional[str]) -> str:
    return f"financial_docs__{document_id}" if document_id else "financial_docs"

def normalize_id(section_id):
    """Normalize section IDs to match between Neo4j and ChromaDB"""
    # Convert to uppercase and add colon if it's a NOTE
    normalized = section_id.upper()
    if normalized.startswith("NOTE ") and not normalized.endswith(":"):
        normalized = normalized + ":"
    return normalized

def hybrid_search(query, document_id: Optional[str] = None):
    # Get collection fresh each time to handle recreation
    try:
        collection = chroma_client.get_collection(
            name=_collection_name(document_id),
            embedding_function=ef,
        )
    except Exception as e:
        return f"Vector database not initialized. Please run build_vector.py first. Error: {str(e)}", "None", []
    
    # 1. Semantic Search: Fetch Top 10 for better coverage
    # This ensures we capture information spread across multiple chunks
    vector_results = collection.query(query_texts=[query], n_results=10)
    
    if not vector_results['documents'][0]:
        return "No text found.", "None", []

    # Deduplicate chunks from the same section and aggregate them
    section_chunks = {}  # section_id -> list of chunks
    for i, chunk in enumerate(vector_results['documents'][0]):
        node_source = vector_results['metadatas'][0][i]['neo4j_id']
        if node_source not in section_chunks:
            section_chunks[node_source] = []
        section_chunks[node_source].append(chunk)
    
    # Combine chunks by section for better context
    primary_text = ""
    for section_id, chunks in section_chunks.items():
        combined_text = "\n\n".join(chunks)
        primary_text += f"**Section: {section_id}**<br>{combined_text}<br><hr><br>"

    # Use the first (most relevant) section for graph traversal
    matched_neo4j_id = vector_results['metadatas'][0][0]['neo4j_id']
    
    graph_context = []
    
    # 2. Graph Traversal (The Map)
    try:
        with neo4j_driver.session() as session:
            if document_id:
                result = session.run(
                    """
                    MATCH (s:Section {id: $id, document_id: $doc_id})-[:REFERS_TO]->(target:Section {document_id: $doc_id})
                    RETURN target.id AS ref_id
                    """,
                    id=matched_neo4j_id,
                    doc_id=document_id,
                )
            else:
                result = session.run(
                    """
                    MATCH (s:Section {id: $id})-[:REFERS_TO]->(target:Section)
                    RETURN target.id AS ref_id
                    """,
                    id=matched_neo4j_id,
                )

            for record in result:
                ref_id = record["ref_id"]
                # Try both the original ID and normalized versions
                normalized_ref_id = normalize_id(ref_id)

                # Try original ID first
                if document_id:
                    ref_docs = collection.get(
                        where={
                            "$and": [
                                {"neo4j_id": ref_id},
                                {"doc_id": document_id},
                            ]
                        },
                        limit=1000,
                    )
                else:
                    ref_docs = collection.get(where={"neo4j_id": ref_id}, limit=1000)

                # If not found, try normalized ID
                if not ref_docs['documents']:
                    if document_id:
                        ref_docs = collection.get(
                            where={
                                "$and": [
                                    {"neo4j_id": normalized_ref_id},
                                    {"doc_id": document_id},
                                ]
                            },
                            limit=1000,
                        )
                    else:
                        ref_docs = collection.get(where={"neo4j_id": normalized_ref_id}, limit=1000)

                if ref_docs['documents']:
                    # Combine ALL chunks from this section for complete context
                    full_text = "\n\n".join(ref_docs['documents'])  # Get all chunks - complete section content
                    graph_context.append({"id": ref_id, "text": full_text})
                else:
                    graph_context.append({"id": ref_id, "text": "[Graph traversed successfully, but exact text chunk not embedded.]"})
    except (SessionExpired, ServiceUnavailable, Neo4jError) as e:
        # Keep RAG working with vector context even if Aura is temporarily unavailable.
        print(f"⚠️ Neo4j unavailable, continuing with vector-only context: {e}")
                
    return primary_text, matched_neo4j_id, graph_context

if __name__ == "__main__":
    # Quick test to make sure it works before Streamlit
    p_text, p_id, g_context = hybrid_search("What are the notes mentioned in the document?")
    print(f"Primary Match: {p_id}")
    print(f"Found {len(g_context)} connected references via Graph.")