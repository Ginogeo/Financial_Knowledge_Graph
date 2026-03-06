# NVIDIA API Integration - Setup Guide

## 🎯 Overview
This project now includes a RAG (Retrieval-Augmented Generation) comparison feature that uses NVIDIA's LLM APIs to demonstrate the value of your Knowledge Graph pipeline.

## 📋 Quick Start

### 1. Get Your NVIDIA API Key

1. Visit: https://build.nvidia.com/
2. Sign in or create a free account
3. Navigate to any model (e.g., "meta/llama-3.1-405b-instruct")
4. Click "Get API Key" 
5. Copy your API key (starts with `nvapi-`)

### 2. Configure Your API Key

Open `src/config.py` and update the NVIDIA API key:

```python
# NVIDIA LLM API Configuration
NVIDIA_API_KEY = "nvapi-YOUR_ACTUAL_KEY_HERE"  # Paste your key here
```

### 3. Install Dependencies

```bash
# Activate your virtual environment first
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install the new dependency
pip install openai>=1.0.0

# Or install all requirements
pip install -r requirements.txt
```

### 4. Test the Integration

Test that your API key works:

```bash
cd src
python nvidia_llm.py
```

You should see two test responses:
- One without context (direct LLM query)
- One with context (RAG-enhanced query)

### 5. Launch the Comparison UI

```bash
streamlit run app.py
```

## 🖥️ Using the UI

The new comparison interface shows **side-by-side results**:

### Left Side: **Without RAG**
- LLM uses only its training data
- May be generic or outdated
- No specific document citations

### Right Side: **With RAG**
- LLM uses your Knowledge Graph + Vector Search
- Grounded in actual document content
- Specific section references

### Example Questions to Try:
- "What are the main revenue sources?"
- "Explain the company's debt structure"
- "What were the total assets in 2024?"
- "What are the key risks mentioned?"

## ⚙️ Configuration Options

### Sidebar Settings:

1. **Model Selection**: Choose from available NVIDIA models
   - `meta/llama-3.1-405b-instruct` (most capable, slower)
   - `meta/llama-3.1-70b-instruct` (balanced)
   - `meta/llama-3.1-8b-instruct` (fastest)
   - `nvidia/llama-3.1-nemotron-70b-instruct` (NVIDIA optimized)
   - `mistralai/mistral-large-2-instruct`

2. **Temperature** (0.0 - 1.0):
   - Lower (0.0-0.3): More factual, deterministic
   - Higher (0.7-1.0): More creative, varied

3. **Max Tokens** (256 - 2048):
   - Controls response length
   - Higher = longer responses

## 📊 How It Works

```
User Question
     │
     ├─── [Without RAG] ──────> Direct LLM Query
     │                          (General knowledge only)
     │
     ├─── [With RAG] ──────────> 1. Vector Search (find relevant chunks)
                                  2. Graph Traversal (discover connections)
                                  3. Format Context
                                  4. LLM Query with Context
                                  (Document-grounded response)
```

## 🔧 Troubleshooting

### "API Key Error"
- Make sure you updated `src/config.py` with your actual NVIDIA API key
- Ensure the key starts with `nvapi-`
- Check that you have API credits at https://build.nvidia.com/

### "Vector database not initialized"
- Run `python src/build_vector.py` first
- Ensure `chroma_db/` folder exists

### "Import Error: No module named 'openai'"
- Run: `pip install openai>=1.0.0`

### Model Not Available
- Some models have regional availability
- Try a different model from the dropdown
- Check https://build.nvidia.com/ for active models

## 🎓 Understanding the Comparison

### What You'll See:

1. **Without RAG Limitations**:
   - Generic responses based on training data
   - May hallucinate specific numbers
   - Cannot reference your specific document
   - Limited to knowledge cutoff date

2. **With RAG Advantages**:
   - Accurate, document-specific answers
   - Can cite exact sections (ITEM 7, NOTE 15, etc.)
   - Uses current financial data from your PDF
   - Combines vector search + graph traversal

## 🚀 Next Steps

### Enhance Your Pipeline:
1. **Add more documents**: Parse additional 10-Ks or financial reports
2. **Tune retrieval**: Adjust `n_results` in `hybrid_search.py`
3. **Try different models**: Test various NVIDIA models for your use case
4. **Add caching**: Cache responses to reduce API costs

### Advanced Features:
- Add conversation history (multi-turn chat)
- Implement streaming responses
- Add source citations in the UI
- Export comparison results to PDF

## 📚 Additional Resources

- NVIDIA Build Documentation: https://docs.build.nvidia.com/
- Model Catalog: https://build.nvidia.com/explore/discover
- OpenAI Python Client: https://github.com/openai/openai-python
- Streamlit Documentation: https://docs.streamlit.io/

## 💡 Tips

1. **Start with lower temperature (0.2)** for factual financial queries
2. **Use the graph connections tab** to see what context was retrieved
3. **Compare multiple models** to find the best for your use case
4. **Ask specific questions** rather than general ones for better RAG performance

## 🔐 Security Note

⚠️ **Never commit your API keys to version control!**

Add to `.gitignore`:
```
src/config.py
.env
```

Consider using environment variables for production:
```python
import os
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY', 'default-key-here')
```

---

**Questions or Issues?** 
- Check the troubleshooting section above
- Review the NVIDIA Build documentation
- Test with `python src/nvidia_llm.py` to isolate issues
