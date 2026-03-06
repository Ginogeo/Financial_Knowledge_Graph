import os
import sys
import json
import chromadb
from chromadb.utils import embedding_functions

# Add src directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import EMBEDDING_MODEL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(BASE_DIR, "data", "processed", "parsed_data1.json")
db_path = os.path.join(BASE_DIR, "chroma_db")

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
    
    print("Sub-chunking text and generating embeddings... (This might take a minute)")
    
    for i, item in enumerate(data):
        text_content = item['text'].strip()
        if len(text_content) > 10:
            # THE FIX: Break massive sections into smaller ~1000 character chunks
            paragraphs = text_content.split('\n')
            current_chunk = ""
            chunk_index = 0
            
            for para in paragraphs:
                current_chunk += para + "\n"
                # Cut the chunk if it gets too long, OR if we just finished a table
                if len(current_chunk) > 1000 or "[/TABLE]" in para:
                    documents.append(current_chunk.strip())
                    # THE BRIDGE: Attach the parent Neo4j ID to this specific bite
                    metadatas.append({"neo4j_id": item['id']})
                    ids.append(f"node_{i}_chunk_{chunk_index}")
                    current_chunk = ""
                    chunk_index += 1
            
            # Catch any leftover text at the end of the section
            if current_chunk.strip():
                documents.append(current_chunk.strip())
                metadatas.append({"neo4j_id": item['id']})
                ids.append(f"node_{i}_chunk_{chunk_index}")
                
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"Success! Added {len(documents)} sub-chunks to Vector DB.")

if __name__ == "__main__":
    build_vector_db(json_path)