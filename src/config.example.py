"""
Configuration file template for database connections.

INSTRUCTIONS:
1. Copy this file to 'config.py' in the same directory
2. Update the values with your actual credentials
3. Never commit config.py to git (it's in .gitignore)
"""

# Neo4j Database Configuration
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password_here"  # UPDATE THIS

# Embedding Model Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# NVIDIA LLM API Configuration (for RAG comparison)
# Get your free API key at: https://build.nvidia.com/
NVIDIA_API_KEY = "nvapi-YOUR_API_KEY_HERE"  # UPDATE THIS
