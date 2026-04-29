# RAG Recipe Physics

## Project Type

Python RAG pipeline for recipe generation with multilingual query support.

## Run Commands

```bash
cd src

# Interactive mode
python main.py

# Single query
python main.py --query "vegan chocolate cake without sugar"

# Run built-in test cases (8 multilingual queries)
python main.py --test

# Retrieval only (skip LLM generation)
python main.py --query "gluten-free bread" --skip-generation
```

## Prerequisites

- **Ollama** must be running on `localhost:11434` with model `qwen2.5:3b`
- **Python packages**: sentence-transformers, cross-encoders, datasets, ollama

## Configuration

All settings in `config/pipeline.yaml`:
- Retrieval: embedder (`all-MiniLM-L6-v2`), reranker (`ms-marco-MiniLM-L-6-v2`), k values
- LLM: model (`qwen2.5:3b`), temperature, context size
- RAG: dataset (`nuhuibrahim/recifine`), cache dir (`cache/rag`)

## Architecture

```
Query → QueryAnalyzer (parser/query_analyzer.py)
        ├─ Language detection (regex + LLM)
        ├─ Translation to English (LLM)
        └─ Extract: servings, weight, diets, forbidden ingredients

     → RAGRetriever (rag/retriever.py)
        ├─ Bi-encoder retrieval (sentence-transformers)
        ├─ Cross-encoder reranking
        └─ Taxonomy classification (keyword-based)

     → Ollama generation (qwen2.5:3b)
```

## Cache

Embeddings and metadata cached in `cache/rag/recipes_*`. Delete cache to re-download dataset.