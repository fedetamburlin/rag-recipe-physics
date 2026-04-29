# RAG Recipe Physics - Architecture

## Project Overview

Python RAG pipeline for recipe generation with multilingual query support and nutritional analysis.

## System Architecture

```
User Query (multilingual)
         ↓
    QueryAnalyzer
    ├── Language Detection (regex + LLM)
    ├── Translation to English (LLM)
    └── Extract: servings, weight, diets, forbidden ingredients
         ↓
    RAGRetriever
    ├── Bi-encoder retrieval (sentence-transformers)
    ├── Cross-encoder reranking
    └── Taxonomy classification (keyword-based)
         ↓
    Ollama Generation (qwen2.5:3b)
         ↓
    Recipe with % ingredients
         ↓
    NutritionCalculator (USDA database)
         ↓
    Nutritional Facts (per 100g)
```

## Components

### 1. Query Parser (`src/parser/query_analyzer.py`)
- **Input**: Multilingual user query (it, fr, es, en)
- **Output**: Parsed query with:
  - Normalized English query
  - Target servings/weight
  - Forbidden ingredients (from diet tags)
  - Diet preferences (vegan, gluten-free, etc.)
  - Max preparation time
- **Test**: 8 multilingual test cases passing

### 2. RAG Retriever (`src/rag/retriever.py`)
- **Retrieval**:
  - Bi-encoder: `sentence-transformers/all-MiniLM-L6-v2`
  - Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - Dataset: `nuhuibrahim/recifine` (500 recipes cached)
  - First stage: top 30 → Final: top 3
- **Generation**:
  - Model: `qwen2.5:3b` via Ollama
  - Output format: `INGREDIENTS: name%, name%, ... TITLE: Recipe`
  - Salt clipped to max 1%
- **Nutrition**:
  - Parses % from generated recipe
  - Scales nutrients by ingredient percentage
  - Uses USDA FoodData Central database

### 3. Nutrition Database (`src/nutrition/`)
- **Database**: SQLite (`data/usda_nutrients.db`)
- **Data**: 
  - 85,819 foods
  - 477 nutrients
  - 803,410 food-nutrient links
- **Components**:
  - `db.py`: Database initialization and schema
  - `ingredient_lookup.py`: Fuzzy matching ingredients to USDA foods
  - `nutrition_calculator.py`: Aggregates nutrients with percentage weighting

### 4. Configuration (`config/pipeline.yaml`)
```yaml
retrieval:
  first_stage_k: 30
  final_k: 3
  embedder_model: "sentence-transformers/all-MiniLM-L6-v2"
  reranker_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"

llm:
  model: "qwen2.5:3b"
  temperature: 0.1

rag:
  dataset_size: 500
  cache_dir: "cache/rag"
```

## Run Commands

```bash
cd src

# Interactive mode
python3 main.py

# Single query with nutrition
python3 main.py --query "vegan chocolate cake without sugar"

# Run tests (8 multilingual queries)
python3 main.py --test

# Retrieval only (skip LLM generation)
python3 main.py --query "gluten-free bread" --skip-generation
```

## Output Example

```
Query: vegan chocolate cake without sugar
[Parsed] Language: en → EN, Diets: [vegan], Forbidden: [sugar, dairy, ...]

[Retrieval] Taxonomy: other
  Top 3:
    [0] Easy German Chocolate Cake               score=1.787

[Generation]
INGREDIENTS: almond flour 30%, cocoa powder 25%, coconut oil 15%, ...
TITLE: Vegan Chocolate Cake

[Nutrition per 100g]
  Energy: 245 KCAL
  Protein: 3.7 G
  Carbohydrates: 48.5 G
  Fat: 16.7 G
  Fiber: 1.0 G
  Sodium: 523 MG
```

## Dependencies

- **Ollama**: qwen2.5:3b running on localhost:11434
- **Python packages**: sentence-transformers, cross-encoders, datasets, ollama, numpy, pyyaml

## Files Structure

```
rag-recipe-physics/
├── config/pipeline.yaml           # Configuration
├── src/
│   ├── main.py                    # Entry point
│   ├── parser/query_analyzer.py   # Query parsing
│   ├── rag/retriever.py           # RAG + generation + nutrition
│   └── nutrition/                 # USDA nutrition module
│       ├── db.py
│       ├── ingredient_lookup.py
│       └── nutrition_calculator.py
├── scripts/ingest_usda.py         # Load USDA data into SQLite
├── data/usda_nutrients.db        # USDA SQLite database
├── cache/rag/                    # Cached embeddings
└── AGENTS.md                     # Agent instructions
```

## Key Features

1. **Multilingual support**: Italian, French, Spanish, English queries
2. **Diet filtering**: Vegan, gluten-free, low-carb, etc.
3. **Nutritional calculation**: Real USDA data with percentage scaling
4. **Caching**: Embeddings cached for fast retrieval

## Known Limitations

- LLM not always following strict percentage format
- Ingredient matching depends on USDA database coverage
- Nutrition values are parametric estimates