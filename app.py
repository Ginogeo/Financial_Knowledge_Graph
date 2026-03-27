import streamlit as st
import sys
import os
import re
import json

# Bulletproof pathing so Streamlit can find your src folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.hybrid_search import hybrid_search
from src.parser import process_document
from src.build_vector import build_vector_db
from src.build_graph import load_graph
from src.nvidia_llm import (
    query_llm_full_document,
    query_llm_with_rag, 
    format_context_for_llm,
    get_available_models
)
from src.document_store import (
    make_document_id,
    get_document_paths,
    upsert_document,
    list_documents,
    get_latest_ready_document_id,
)


def _safe_filename(name: str) -> str:
    return "".join(ch for ch in name if ch.isalnum() or ch in (" ", ".", "-", "_")) or "uploaded.pdf"


def _compute_document_char_count(parsed_json_path: str) -> int:
    if not os.path.exists(parsed_json_path):
        return 0
    try:
        with open(parsed_json_path, "r", encoding="utf-8") as f:
            sections = json.load(f)
        return sum(len(item.get("text", "")) for item in sections)
    except Exception:
        return 0

# Page configuration
st.set_page_config(layout="wide", page_title="Financial RAG Comparison")

# Keep model-generated tables aligned inside response cards.
st.markdown(
    """
    <style>
    .llm-response {
        background-color: #1a1a1a;
        padding: 20px;
        border-radius: 10px;
        overflow-x: auto;
    }

    .llm-response.full {
        border-left: 4px solid #ff8800;
    }

    .llm-response.rag {
        border-left: 4px solid #44ff44;
    }

    .llm-response table {
        border-collapse: collapse;
        width: max-content;
        min-width: 100%;
    }

    .llm-response th,
    .llm-response td {
        vertical-align: top;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Title and description
st.title("🔬 Financial Document RAG Comparison")
st.markdown("""
This demo compares **two approaches** to answering financial questions:
- **Full Document Dump**: LLM receives entire document (naive approach, 597k chars, ~149k tokens)
- **Optimized RAG Pipeline**: LLM receives only relevant sections via Knowledge Graph + Vector Search
""")

selected_document_id = None
selected_document_name = "Legacy Document"

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
    st.markdown("### 📁 Document Management")

    uploaded_file = st.file_uploader("Upload Document", type=["pdf", "html", "htm"])
    custom_doc_name = st.text_input("Document name (optional)", placeholder="Defaults to file name")

    if st.button("Process Uploaded Document", use_container_width=True):
        if not uploaded_file:
            st.error("Please upload a PDF file first.")
        else:
            filename = _safe_filename(uploaded_file.name)
            doc_name = (custom_doc_name or os.path.splitext(filename)[0]).strip()
            document_id = make_document_id(filename)
            paths = get_document_paths(document_id, filename)

            os.makedirs(paths["raw_dir"], exist_ok=True)
            os.makedirs(paths["processed_dir"], exist_ok=True)

            upsert_document(
                document_id=document_id,
                name=doc_name,
                filename=filename,
                status="PROCESSING",
            )

            try:
                with open(paths["raw_pdf_path"], "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with st.spinner("Parsing, vectorizing, and building graph..."):
                    ext = os.path.splitext(filename)[1].lower()
                    parser_method = "html" if ext in (".html", ".htm") else "pdfplumber"
                    process_document(
                        pdf_path=paths["raw_pdf_path"],
                        output_path=paths["parsed_json_path"],
                        method=parser_method,
                        use_tables=True,
                    )
                    vector_stats = build_vector_db(paths["parsed_json_path"], document_id=document_id)
                    load_graph(paths["parsed_json_path"], document_id=document_id, document_name=doc_name)

                char_count = _compute_document_char_count(paths["parsed_json_path"])
                stats = {
                    "char_count": char_count,
                    "chunk_count": vector_stats.get("chunk_count", 0),
                    "section_count": vector_stats.get("section_count", 0),
                }
                upsert_document(
                    document_id=document_id,
                    name=doc_name,
                    filename=filename,
                    status="READY",
                    stats=stats,
                )
                st.session_state["active_document_id"] = document_id
                st.success(f"Document ready: {doc_name}")
            except Exception as e:
                upsert_document(
                    document_id=document_id,
                    name=doc_name,
                    filename=filename,
                    status="ERROR",
                    error=str(e),
                )
                st.error(f"Failed to process document: {e}")

    documents = list_documents()
    ready_documents = [doc for doc in documents if doc.get("status") == "READY"]

    if "active_document_id" not in st.session_state:
        st.session_state["active_document_id"] = get_latest_ready_document_id()

    if ready_documents:
        options = [doc["id"] for doc in ready_documents]
        option_labels = {doc["id"]: doc.get("name", doc["id"]) for doc in ready_documents}

        current_doc = st.session_state.get("active_document_id")
        if current_doc not in options:
            current_doc = options[0]
            st.session_state["active_document_id"] = current_doc

        selected_document_id = st.selectbox(
            "Active document",
            options=options,
            index=options.index(current_doc),
            format_func=lambda doc_id: option_labels.get(doc_id, doc_id),
        )
        st.session_state["active_document_id"] = selected_document_id
        selected_document_name = option_labels.get(selected_document_id, selected_document_id)

        selected_meta = next((doc for doc in ready_documents if doc["id"] == selected_document_id), {})
        stats = selected_meta.get("stats", {})
        if stats:
            st.caption(
                f"Sections: {stats.get('section_count', 0)} | Chunks: {stats.get('chunk_count', 0)}"
            )
    else:
        st.info("Upload and process a PDF to start querying.")
    
    st.divider()
    

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
    if not selected_document_id:
        st.error("No ready document selected. Upload and process a PDF first.")
        st.stop()
    
    # Step 1: Retrieve context using hybrid search
    with st.spinner("🔍 Step 1/3: Searching knowledge graph..."):
        primary_text, matched_id, graph_context = hybrid_search(query, document_id=selected_document_id)
    
    # Format context for LLM
    formatted_context = format_context_for_llm(
        primary_text,
        graph_context,
        matched_id,
        document_id=selected_document_id,
    )
    
    # Create two columns for side-by-side comparison
    col1, col2 = st.columns(2)
    
    # LEFT COLUMN: Full Document Dump (Naive Approach)
    with col1:
        st.markdown("### 📄 Full Document Dump")
        st.caption(f"Naive approach for selected document: {selected_document_name}")
        st.info(f"🤖 Model: **{selected_model}**")
        
        with st.spinner("⏳ Processing full document..."):
            full_doc_response = query_llm_full_document(
                question=query,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens,
                document_id=selected_document_id,
            )
        
        # Show token/cost warning
        st.warning("⚠️ **Issues**: High token cost (~149k tokens), slow processing, entire 597k chars in context")
        
        st.markdown(
            f"""<div class='llm-response full'>
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
            f"""<div class='llm-response rag'>
            {rag_response}
            """,
            unsafe_allow_html=True
        )
        
        st.success("🎯 This approach retrieves relevant sections + company context via knowledge graph")
    
    # Show retrieved context (collapsible)
    st.divider()
    
    # Add efficiency comparison metrics
    selected_doc_meta = next((doc for doc in documents if doc.get("id") == selected_document_id), {})
    full_doc_size = selected_doc_meta.get("stats", {}).get("char_count", 597681) or 597681
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
            # Render as cleaned plain text so broken HTML/table fragments from chunks
            # cannot distort layout inside the tab.
            primary_display = primary_text.replace("<hr>", "\n" + "-" * 60 + "\n")
            primary_display = primary_display.replace("<br>", "\n")
            primary_display = re.sub(r"<[^>]+>", " ", primary_display)
            primary_display = re.sub(r"[ \t]+", " ", primary_display)
            primary_display = re.sub(r"\n{3,}", "\n\n", primary_display).strip()

            st.text_area(
                "Primary Match Content",
                primary_display,
                height=420,
                key="primary_match_content",
                label_visibility="collapsed"
            )
        
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