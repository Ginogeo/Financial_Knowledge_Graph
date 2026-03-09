import os
import sys
import re
import json
import chromadb
from chromadb.utils import embedding_functions

# Add src directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import EMBEDDING_MODEL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(BASE_DIR, "data", "processed", "parsed_data1.json")
db_path = os.path.join(BASE_DIR, "chroma_db")

# --- Chunking config ---
CHUNK_SIZE = 1000       # Target chars per chunk
CHUNK_OVERLAP = 200     # Overlap between consecutive chunks (prevents lost context at boundaries)


def clean_text(text: str) -> str:
    """Remove common 10-K noise: bare page numbers, repeated headers, tiny fragments."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append('')  # preserve blank lines for paragraph splitting
            continue
        if re.match(r'^\d{1,3}$', stripped):  # bare page numbers
            continue
        if re.match(r'^(THE COCA.COLA COMPANY|Table of Contents)\s*$', stripped, re.IGNORECASE):
            continue
        if len(stripped) < 3:  # tiny fragments
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def semantic_chunk(text: str, section_id: str) -> list[str]:
    """
    Split text into topically coherent chunks using paragraph boundaries.

    1. Split on blank-line boundaries (paragraphs / tables).
    2. Merge small consecutive paragraphs up to CHUNK_SIZE.
    3. Keep CHUNK_OVERLAP chars of context between consecutive chunks.
    4. Prepend section ID so the embedding model has topical grounding.
    """
    # Split on paragraph boundaries (one or more blank lines) or table markers
    blocks = re.split(r'\n\s*\n|\[/TABLE\]\n?', text)
    # Re-attach [/TABLE] markers to the preceding block
    merged_blocks = []
    for block in blocks:
        block = block.strip()
        if block:
            merged_blocks.append(block)

    chunks: list[str] = []
    current_chunk = ""

    for block in merged_blocks:
        # If adding this block would exceed the limit & we already have content, flush
        if current_chunk and (len(current_chunk) + len(block) + 2) > CHUNK_SIZE:
            chunks.append(current_chunk.strip())
            # Carry over the tail of the previous chunk as overlap
            if len(current_chunk) > CHUNK_OVERLAP:
                current_chunk = current_chunk[-CHUNK_OVERLAP:] + "\n\n" + block
            else:
                current_chunk = block
        else:
            current_chunk = (current_chunk + "\n\n" + block) if current_chunk else block

        # Safety: if a single block is huge (e.g. a giant table), flush immediately
        if len(current_chunk) > CHUNK_SIZE * 2:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-CHUNK_OVERLAP:] if len(current_chunk) > CHUNK_OVERLAP else ""

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Prepend section ID to each chunk for embedding context
    labeled = [f"[{section_id}] {chunk}" for chunk in chunks]
    return labeled


def build_vector_db(data_path):
    print(f"Loading parsed data from: {data_path}")
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=db_path)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    
    try:
        client.delete_collection(name="financial_docs")
        print("Cleared old vector collection.")
    except Exception:
        pass 
        
    collection = client.create_collection(
        name="financial_docs", 
        embedding_function=sentence_transformer_ef
    )
    
    documents = []
    metadatas = []
    ids = []
    
    print("Semantic chunking with overlap and noise removal... (This might take a minute)")
    
    for i, item in enumerate(data):
        text_content = item['text'].strip()
        if len(text_content) <= 10:
            continue

        # Step 1: Clean noisy text (page numbers, repeated headers)
        cleaned = clean_text(text_content)

        # Step 2: Semantic chunking with overlap + section label
        chunks = semantic_chunk(cleaned, item['id'])

        for chunk_index, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"neo4j_id": item['id']})
            ids.append(f"node_{i}_chunk_{chunk_index}")
                
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"Success! Added {len(documents)} semantic chunks to Vector DB.")
    print(f"  Config: chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
    print(f"  Sections processed: {len(data)}")
    print(f"  Avg chunks/section: {len(documents) / max(len(data), 1):.1f}")

if __name__ == "__main__":
    build_vector_db(json_path)