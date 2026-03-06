"""
NVIDIA LLM API Integration Module
Supports comparison between direct LLM queries and RAG-enhanced queries.
"""

import os
import sys
import json
from openai import OpenAI

# Add src directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NVIDIA_API_KEY

# NVIDIA API Configuration
# NVIDIA uses OpenAI-compatible API format
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# Default model - you can change this to any NVIDIA model
DEFAULT_MODEL = "meta/llama-3.1-405b-instruct"  # or "nvidia/llama-3.1-nemotron-70b-instruct"


def load_full_document(max_chars: int = 597681) -> str:
    """
    Load the entire parsed document as one big text blob.
    This represents the naive approach: dumping everything into the LLM context.
    
    Full document stats:
    - 597,681 characters
    - 111,118 words
    - ~149,420 tokens (at 4 chars/token)
    
    Args:
        max_chars: Maximum characters to include (default: full document)
    
    Returns:
        Full document text concatenated together
    """
    try:
        # Get the path to parsed_data1.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "data", "processed", "parsed_data1.json")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            sections = json.load(f)
        
        # Concatenate all sections
        full_text = ""
        for section in sections:
            section_id = section.get('id', 'UNKNOWN')
            section_text = section.get('text', '')
            full_text += f"\n\n{'='*60}\n{section_id}\n{'='*60}\n{section_text}"
        
        # Truncate if too long (to avoid exceeding model context limits)
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n\n[... Document truncated due to length ...]"
        
        return full_text
    
    except Exception as e:
        return f"Error loading document: {str(e)}"


def query_llm_full_document(question: str, model: str = DEFAULT_MODEL, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    """
    Query the LLM with the ENTIRE document dumped into context.
    This represents the naive approach without retrieval optimization.
    
    Args:
        question: The user's question
        model: NVIDIA model to use
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum response length
    
    Returns:
        The LLM's response based on full document
    """
    try:
        # Load the entire document
        full_doc = load_full_document(max_chars=597681)  # Full doc: ~149k tokens (597,681 chars, 111,118 words)
        
        prompt = f"""You are a financial analyst assistant. Answer the question based on the financial document provided below.

FULL FINANCIAL DOCUMENT:
{full_doc}

QUESTION:
{question}

ANSWER:"""

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful financial analyst. Answer questions based on the provided document."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        return f"❌ Error querying NVIDIA API: {str(e)}\n\nPlease check your API key in src/config.py"


def query_llm_direct(question: str, model: str = DEFAULT_MODEL, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    """
    Query the LLM directly WITHOUT any context (no RAG).
    This shows what the model knows from its training data alone.
    
    Args:
        question: The user's question
        model: NVIDIA model to use
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum response length
    
    Returns:
        The LLM's response as a string
    """
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful financial analyst assistant. Answer questions based on your general knowledge. If you don't know specific details about a company, be honest about it."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        return f"❌ Error querying NVIDIA API: {str(e)}\n\nPlease check your API key in src/config.py"


def query_llm_with_rag(question: str, context: str, model: str = DEFAULT_MODEL, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    """
    Query the LLM WITH context from the RAG pipeline (hybrid search + graph traversal).
    This provides the model with relevant document excerpts to answer from.
    
    Args:
        question: The user's question
        context: Retrieved context from vector DB + knowledge graph
        model: NVIDIA model to use
        temperature: Controls randomness
        max_tokens: Maximum response length
    
    Returns:
        The LLM's response grounded in the provided context
    """
    try:
        # Construct a prompt that includes the retrieved context
        rag_prompt = f"""You are a financial analyst assistant. Answer the question based ONLY on the context provided below. If the context doesn't contain enough information to answer the question, say so.

CONTEXT FROM FINANCIAL DOCUMENTS:
{context}

QUESTION:
{question}

ANSWER (based on the context above):"""

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful financial analyst. Answer questions based strictly on the provided context. Cite specific sections when possible."
                },
                {
                    "role": "user",
                    "content": rag_prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        return f"❌ Error querying NVIDIA API: {str(e)}\n\nPlease check your API key in src/config.py"


def format_context_for_llm(primary_text: str, graph_context: list, matched_id: str) -> str:
    """
    Format the retrieved context (from hybrid search) into a clean string for the LLM.
    
    Args:
        primary_text: The main text chunk from vector search
        graph_context: List of related sections from graph traversal
        matched_id: ID of the matched section
    
    Returns:
        Formatted context string
    """
    # Clean up HTML tags from primary_text
    import re
    clean_primary = re.sub(r'<[^>]+>', '', primary_text)
    clean_primary = re.sub(r'\*\*Match \d+.*?\*\*', '', clean_primary)
    clean_primary = clean_primary.replace('<hr>', '\n---\n').strip()
    
    formatted = f"PRIMARY SECTION ({matched_id}):\n{clean_primary}\n\n"
    
    # Add related sections from graph
    if graph_context:
        formatted += "RELATED SECTIONS (from knowledge graph):\n\n"
        for idx, ctx in enumerate(graph_context, 1):
            # Include more context for better LLM understanding (first 2000 chars)
            text_preview = ctx['text'][:2000] if len(ctx['text']) > 2000 else ctx['text']
            if len(ctx['text']) > 2000:
                text_preview += "\n[... section continues ...]"
            formatted += f"{idx}. Section {ctx['id']}:\n{text_preview}\n\n"
    
    return formatted


def get_available_models():
    """
    Get list of available NVIDIA models.
    You can update this list based on NVIDIA's catalog.
    """
    return [
        "meta/llama-3.1-405b-instruct",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "mistralai/mistral-large-2-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1",
    ]


if __name__ == "__main__":
    # Test the integration
    print("Testing NVIDIA LLM API Integration...")
    print("=" * 80)
    
    test_question = "What are the main revenue sources?"
    
    print(f"\n1. Testing Full Document Query (Naive Approach):")
    print(f"Question: {test_question}")
    print("Loading entire document...")
    full_response = query_llm_full_document(test_question)
    print(f"Response:\n{full_response}\n")
    
    print("=" * 80)
    
    test_context = """
PRIMARY SECTION (ITEM 7):
Management's Discussion and Analysis of Financial Condition and Results of Operations

Our revenues for fiscal 2024 were primarily derived from three business segments:
1. Cloud Services and License Support: $52.96 billion (45% of total revenue)
2. Cloud License and On-Premise License: $9.38 billion (20% of total revenue)
3. Hardware: $3.32 billion (8% of total revenue)
4. Services: $5.12 billion (27% of total revenue)

Total revenues: $52.96 billion, representing a 6% increase from fiscal 2023.

RELATED SECTIONS (from knowledge graph):

1. Section NOTE 15:
Revenue by Geographic Region shows that 55% comes from Americas, 25% from EMEA, 
and 20% from Asia Pacific. Cloud services growth was 23% year-over-year.
    """
    
    print(f"\n2. Testing RAG-Optimized Query:")
    print(f"Question: {test_question}")
    print(f"Context provided: {len(test_context)} chars (vs 597,681 for full doc)")
    rag_response = query_llm_with_rag(test_question, test_context)
    print(f"Response:\n{rag_response}\n")
    
    print("=" * 80)
    print(f"\n✅ Efficiency: RAG uses {(len(test_context)/597681)*100:.1f}% of full doc size")
    print(f"💰 Token Savings: ~{(597681-len(test_context))//4:,} tokens saved per query")
