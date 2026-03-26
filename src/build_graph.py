import os
import sys
import json
from typing import Optional
from neo4j import GraphDatabase

# Add src directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 1. Dynamically find your project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(BASE_DIR, "data", "processed", "parsed_data1.json")

# 2. Neo4j Connection Details (imported from config.py)
URI = NEO4J_URI
AUTH = (NEO4J_USER, NEO4J_PASSWORD)

def load_graph(data_path, document_id: Optional[str] = None, document_name: Optional[str] = None):
    print(f"Loading data from: {data_path}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    doc_name = document_name or "SEC 10-K Filing"
    
    with driver.session() as session:
        if document_id:
            print(f"Clearing graph data for document_id={document_id}...")
            session.run("MATCH (s:Section {document_id: $doc_id}) DETACH DELETE s", doc_id=document_id)
            session.run("MATCH (d:Document {id: $doc_id}) DETACH DELETE d", doc_id=document_id)

            print("Creating scoped Document and Section nodes...")
            session.run(
                "MERGE (d:Document {id: $doc_id}) SET d.name = $doc_name",
                doc_id=document_id,
                doc_name=doc_name,
            )

            for item in data:
                session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    MERGE (s:Section {id: $id, document_id: $doc_id})
                    MERGE (d)-[:HAS_SECTION]->(s)
                    """,
                    id=item['id'],
                    doc_id=document_id,
                )

                for ref in item.get('references', []):
                    session.run(
                        """
                        MATCH (s:Section {id: $source_id, document_id: $doc_id})
                        MERGE (target:Section {id: $target_id, document_id: $doc_id})
                        MERGE (s)-[:REFERS_TO]->(target)
                        """,
                        source_id=item['id'],
                        target_id=ref,
                        doc_id=document_id,
                    )
        else:
            print("Clearing old graph data...")
            session.run("MATCH (n) DETACH DELETE n")

            print("Creating Document and Section Nodes...")
            session.run("MERGE (d:Document {name: 'SEC 10-K Filing'})")

            for item in data:
                # Create Section Node
                session.run("""
                    MATCH (d:Document {name: 'SEC 10-K Filing'})
                    MERGE (s:Section {id: $id})
                    MERGE (d)-[:HAS_SECTION]->(s)
                """, id=item['id'])

                # Create REFERS_TO relationships
                for ref in item.get('references', []):
                    session.run("""
                        MATCH (s:Section {id: $source_id})
                        MERGE (target:Section {id: $target_id})
                        MERGE (s)-[:REFERS_TO]->(target)
                    """, source_id=item['id'], target_id=ref)
                
    driver.close()
    print("Graph construction complete!")

if __name__ == "__main__":
    load_graph(json_path)