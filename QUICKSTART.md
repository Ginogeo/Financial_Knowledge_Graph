# 🚀 Quick Start - NVIDIA RAG Comparison

## Step 1: Get Your NVIDIA API Key (2 minutes)

1. Go to: **https://build.nvidia.com/**
2. Click **"Sign In"** (or create free account)
3. Select any model (e.g., **"Llama 3.1 405B"**)
4. Click **"Get API Key"** button
5. Copy your key (starts with `nvapi-`)

## Step 2: Add API Key to Config

Open `src/config.py` and paste your key:

```python
NVIDIA_API_KEY = "nvapi-YOUR_KEY_HERE"  # Paste your actual key
```

## Step 3: Run the App

```bash
streamlit run app.py
```

## Step 4: See the Difference!

Ask a question like:
- "What are the main revenue sources?"
- "What were the total assets in 2024?"

You'll see **two approaches side-by-side**:
- 📄 **Full Document Dump**: Sends entire 597k char document (naive, expensive, ~149k tokens)
- 🎯 **Optimized RAG**: Retrieves only relevant sections via vector + graph (smart, efficient, ~10-20k chars)

### The Result:
- **~95% token reduction** with RAG pipeline (597k → ~15k chars)
- **Same or better accuracy** with precise targeting
- **Faster responses** with pre-indexed retrieval
- **Lower costs** with efficient context

---

### Need Help?

See detailed setup: [NVIDIA_SETUP.md](NVIDIA_SETUP.md)

### Can't Get API Key?

The app still works without it! The RAG pipeline (vector search + graph) will still run - you just won't see the LLM comparison feature.
