import os
import sys
import json
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

def load_graph(data_path):
    print(f"Loading data from: {data_path}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    with driver.session() as session:
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