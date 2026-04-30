# RAG Recipe Physics

## Project Type

Python RAG pipeline for recipe generation with multilingual query support.

## Run Commands

**Always run from `src/` directory** (paths like `cache/rag/` are relative to src/):

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
- RAG: dataset (`nuhuibrahim/recifine`), dataset_size: 20000, cache_dir: `cache/rag`

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

Embeddings and metadata cached in `src/cache/rag/recipes_*`. Delete cache to force re-download and re-encode (20k recipes takes ~6 min). Cache key includes dataset_size.

## Nutrition Database (Separate Module)

### Database Setup
```bash
python scripts/ingest_usda.py
```

### Usage
```python
from src.nutrition import IngredientMatcher, calculate_recipe_nutrients

# Match ingredients to USDA foods (with priority list + blacklist)
matcher = IngredientMatcher()
matched = matcher.match_ingredients(['butter', 'flour', 'sugar'])

# Calculate nutrition totals (percentages in 0-1 range, not 0-100)
result = calculate_recipe_nutrients(['butter', 'flour', 'sugar'], matched)
# Returns: {'ENERGY': {'amount': X, 'unit': 'KCAL'}, ...}
```

### Known Issues (Debugged)
- **Ingredient matching**: Some ingredients (cinnamon, coffee) return wrong foods. Priority list in `ingredient_lookup.py` maps to exact USDA descriptions.
- **Nutrition calculation**: Percentages must be decimal (0-1) not integer (0-100). The RAGRetriever scaling bug was fixed but verify if parsing changes.

### Database Location
- SQLite: `data/usda_nutrients.db` (19k foods, 44 nutrient codes)