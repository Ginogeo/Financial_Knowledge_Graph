import streamlit as st
import sys
import os

# Bulletproof pathing so Streamlit can find your src folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.hybrid_search import hybrid_search
from src.nvidia_llm import (
    query_llm_full_document,
    query_llm_with_rag, 
    format_context_for_llm,
    get_available_models
)

# Page configuration
st.set_page_config(layout="wide", page_title="Financial RAG Comparison")

# Title and description
st.title("🔬 Financial Document RAG Comparison")
st.markdown("""
This demo compares **two approaches** to answering financial questions:
- **Full Document Dump**: LLM receives entire document (naive approach, 597k chars, ~149k tokens)
- **Optimized RAG Pipeline**: LLM receives only relevant sections via Knowledge Graph + Vector Search
""")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Model selection
    available_models = get_available_models()
    selected_model = st.selectbox(
        "Select NVIDIA Model",
        available_models,
        index=0,
        help="Choose which NVIDIA LLM to use"
    )
    
    # Temperature control
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.1,
        help="Higher = more creative, Lower = more deterministic"
    )
    
    # Max tokens
    max_tokens = st.slider(
        "Max Response Tokens",
        min_value=256,
        max_value=2048,
        value=1024,
        step=256,
        help="Maximum length of LLM response"
    )
    
    st.divider()
    st.markdown("### 📊 Why RAG is Better:")
    st.markdown("""
    **Full Document Problems:**
    - � ~149k tokens/query
    - 🐌 Slow processing
    - 🎯 Poor precision
    - 🧠 Context overflow
    
    **RAG Advantages:**
    - ✅ Retrieval: Find relevant chunks
    - ✅ Graph: Discover connections      - ✅ Company Context: PREAMBLE always included    - ✅ Efficient: ~95% token savings
    - ✅ Accurate: Precise context
    
    **Document Stats:**
    - 597,681 characters
    - 111,118 words
    - 44 sections
    """)

# Main query input
query = st.text_input(
    "💬 Ask a question about the financial document:",
    placeholder="e.g., What are the company's main revenue sources?"
)

# Action buttons
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
with col_btn1:
    search_button = st.button("🔍 Compare", type="primary", use_container_width=True)
with col_btn2:
    if st.button("🔄 Clear", use_container_width=True):
        st.rerun()

# Main comparison logic
if search_button and query:
    
    # Step 1: Retrieve context using hybrid search
    with st.spinner("🔍 Step 1/3: Searching knowledge graph..."):
        primary_text, matched_id, graph_context = hybrid_search(query)
    
    # Format context for LLM
    formatted_context = format_context_for_llm(primary_text, graph_context, matched_id)
    
    # Create two columns for side-by-side comparison
    col1, col2 = st.columns(2)
    
    # LEFT COLUMN: Full Document Dump (Naive Approach)
    with col1:
        st.markdown("### 📄 Full Document Dump")
        st.caption("Naive approach: Upload entire document (~597k chars)")
        st.info(f"🤖 Model: **{selected_model}**")
        
        with st.spinner("⏳ Processing full document..."):
            full_doc_response = query_llm_full_document(
                question=query,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        # Show token/cost warning
        st.warning("⚠️ **Issues**: High token cost (~149k tokens), slow processing, entire 597k chars in context")
        
        st.markdown(
            f"""<div style='background-color: #1a1a1a; padding: 20px; border-radius: 10px; border-left: 4px solid #ff8800;'>
            {full_doc_response}
            </div>""",
            unsafe_allow_html=True
        )
        
        st.info("📊 This approach sends 597,681 characters (111,118 words, ~149k tokens) to the LLM every query")
    
    # RIGHT COLUMN: Optimized RAG Pipeline
    with col2:
        st.markdown("### 🎯 Optimized RAG Pipeline")
        st.caption("Smart retrieval: Vector Search + Knowledge Graph + Company Context")
        st.info(f"🤖 Model: **{selected_model}**")
        
        with st.spinner("⏳ Retrieving relevant context..."):
            rag_response = query_llm_with_rag(
                question=query,
                context=formatted_context,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        # Show efficiency metrics
        context_size = len(formatted_context)
        st.success(f"✅ **Efficient**: Only {context_size:,} chars sent (~{context_size//4} tokens) + PREAMBLE")
        
        st.markdown(
            f"""<div style='background-color: #1a1a1a; padding: 20px; border-radius: 10px; border-left: 4px solid #44ff44;'>
            {rag_response}
            </div>""",
            unsafe_allow_html=True
        )
        
        st.success("🎯 This approach retrieves relevant sections + company context via knowledge graph")
    
    # Show retrieved context (collapsible)
    st.divider()
    
    # Add efficiency comparison metrics
    full_doc_size = 597681  # Actual full document size (111,118 words)
    rag_size = len(formatted_context)
    efficiency_gain = ((full_doc_size - rag_size) / full_doc_size) * 100
    num_chunks_retrieved = len(primary_text.split("<hr>")) - 1
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric("Full Doc Size", f"{full_doc_size:,} chars", delta=None, delta_color="off")
    with metric_col2:
        st.metric("RAG Context Size", f"{rag_size:,} chars", delta=f"-{efficiency_gain:.1f}%", delta_color="normal")
    with metric_col3:
        token_savings = (full_doc_size - rag_size) // 4  # Rough token estimate
        st.metric("Token Savings", f"~{token_savings:,}", delta="Efficiency", delta_color="normal")
    with metric_col4:
        st.metric("Chunks Retrieved", num_chunks_retrieved, delta="10 max", delta_color="off")
    
    with st.expander("📄 View Retrieved Context & Comparison Details", expanded=False):
        
        tab1, tab2, tab3, tab4 = st.tabs(["Primary Match", "Graph Connections", "RAG Context for LLM", "Why RAG Wins"])
        
        with tab1:
            st.subheader(f"Vector Match: {matched_id}")
            st.markdown(primary_text, unsafe_allow_html=True)
        
        with tab2:
            if graph_context:
                st.success(f"✅ Found {len(graph_context)} related sections via graph traversal")
                for context in graph_context:
                    with st.expander(f"Linked: {context['id']}", expanded=False):
                        # Show full content with scroll
                        st.markdown(f"**Full Content ({len(context['text']):,} characters)**")
                        st.text_area(
                            "Section Text",
                            context['text'],
                            height=300,
                            key=f"context_{context['id']}",
                            label_visibility="collapsed"
                        )
            else:
                st.info("No cross-references detected for this section.")
        
        with tab3:
            st.markdown("### Full Context Sent to LLM")
            st.success("✅ **PREAMBLE always included** - Company information for proper grounding")
            st.info(f"📊 Total context size: {len(formatted_context):,} characters (~{len(formatted_context)//4:,} tokens)")
            st.code(formatted_context, language="text")
        
        with tab4:
            st.markdown("""
            ### 🎯 Why Optimized RAG is Superior:
            
            #### **Full Document Dump Problems:**
            1. **Token Waste**: Sends 597,681 chars (~149k tokens) every query
            2. **High Cost**: Pay for entire document context each time
            3. **Slow Processing**: LLM must scan everything
            4. **Poor Precision**: Relevant info buried in noise
            5. **Context Limit**: Exceeds most model context windows
            
            #### **RAG Pipeline Advantages:**
            1. **Efficient Retrieval**: Only retrieves relevant sections
            2. **Cost Effective**: Sends only ~{:,} chars ({:.1f}% reduction)
            3. **Fast**: Pre-indexed vector + graph search
            4. **Precise**: Graph traversal finds cross-references
            5. **Context-Aware**: PREAMBLE always included for grounding
            6. **Scalable**: Works with documents of any size
            
            #### **Result:**
            - **{:.1f}x more efficient** in token usage
            - **Same or better accuracy** with precise context
            - **Sub-second retrieval** with vector search
            - **Graph-aware** connections between sections
            - **Company context** always included via PREAMBLE
            """.format(rag_size, efficiency_gain, full_doc_size / max(rag_size, 1)))


# Instructions when no query yet
else:
    st.info("👆 Enter a question above and click 'Compare' to see the difference between full-document dump and optimized RAG retrieval.")
    
    # Show comparison visualization
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("""
        ### 📄 Full Document Dump
        **The Naive Approach:**
        - Uploads entire 597k character document
        - LLM scans everything every time
        - High token costs (~149k tokens/query)
        - Slow and inefficient
        - No precision targeting
        """)
    
    with col_info2:
        st.markdown("""
        ### 🎯 Optimized RAG Pipeline
        **The Smart Approach:**
        - Vector search finds relevant chunks
        - Graph traversal discovers connections
        - PREAMBLE (company info) always included
        - Only sends relevant context (~10-20k chars)
        - Fast retrieval (<1 second)
        - Precise and cost-effective
        """)
    
    st.divider()
    
    # Example queries
    st.markdown("### 💡 Example Questions:")
    examples = [
        "What are the main revenue sources?",
        "What were the total assets in 2024?",
        "Explain the company's debt structure",
        "What are the key risks mentioned?",
        "What is the company's business strategy?"
    ]
    
    cols = st.columns(len(examples))
    for idx, example in enumerate(examples):
        with cols[idx]:
            if st.button(example, key=f"example_{idx}", use_container_width=True):
                st.session_state.example_query = example
                st.rerun()

# Handle example query selection
if 'example_query' in st.session_state:
    st.session_state.pop('example_query')