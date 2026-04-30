# AGENTS.md

## Run Commands

**Always run from `src/` directory:**

```bash
cd src

# Interactive
python main.py

# Single query
python main.py --query "vegan chocolate cake without sugar"

# Retrieval only
python main.py --query "gluten-free bread" --skip-generation

# Debug mode (verbose logging)
python main.py --query "..." --debug
```

## Prerequisites

- **Ollama** running on `localhost:11434` with model `qwen2.5:3b`
- **Python**: sentence-transformers, cross-encoders, datasets, ollama, numpy, pyyaml

## Config

`config/pipeline.yaml` controls everything:
- Retrieval: `first_stage_k: 30`, `final_k: 3`, embedder (`all-MiniLM-L6-v2`), reranker (`ms-marco-MiniLM-L-6-v2`)
- LLM: `qwen2.5:3b`, temperature, `num_ctx: 8192`
- RAG: `dataset_size: 50000`, cache in `cache/rag/`

## Architecture

```
Query → QueryAnalyzer (_01_parser/query_analyzer.py)
          ├─ Language detection (regex + LLM)
          ├─ Translate to English
          └─ Extract: servings, weight, diets, forbidden

     → RAGRetriever (_02_rag/retriever.py)
          ├─ Bi-encoder retrieval
          ├─ Cross-encoder reranking
          ├─ Taxonomy classification
          └─ Nutrition calculation

      → Ollama generation
           └─ Parse + scale ingredients by percentage

      → Feature Extraction (_03_feature_extraction/feature_extractor.py)
           └─ 10 physicochemical features → future oven prediction

      → Validation (_04_validation/validator.py)
           └─ Check calories/macros against empirical ranges
```

**Goal**: extract structured feature vectors from LLM recipe output to train a model predicting oven parameters (temperature, time, preheat, mode, humidity). No heuristics. No text-to-text prediction. Only USDA nutrients + physics mixing rules.

## Directory Structure (src/)

```
src/
├── _01_parser/              # Step 1: query parsing
├── _02_rag/                 # Step 2: retrieval + generation + nutrition
│                              └── _is_oven_recipe() filters dataset for oven-only
├── _03_feature_extraction/  # Step 3: physicochemical feature extraction + classifier
│                              └── classifier.py: 4 families (dough, batter, roast, custard)
├── _04_validation/          # Step 4: empirical validation
├── nutrition/               # Shared library (USDA DB, no number)
└── main.py
```

## Cache

Delete `cache/rag/recipes_*` to force re-download + re-encode (~6 min for 50k recipes, ~23k oven recipes kept after filtering).

## Nutrition Module

```python
from src.nutrition import IngredientMatcher, calculate_recipe_nutrients

matcher = IngredientMatcher()
matched = matcher.match_ingredients(['butter', 'flour', 'sugar'])
result = calculate_recipe_nutrients(['butter', 'flour', 'sugar'], matched)
# Percentages as decimal (0-1), NOT integers (0-100)
```

DB: `data/usda_nutrients.db` (19k foods, 44 nutrients)

## Feature Extraction (WIP)

`src/_03_feature_extraction/feature_extractor.py` extracts 10 physicochemical features from LLM-generated recipes:

```python
from src._03_feature_extraction.feature_extractor import RecipeFeatureExtractor

extractor = RecipeFeatureExtractor()
features = extractor.extract(ingredients, nutrition, taxonomy)
# Returns: water_g, protein_g, fat_g, carbs_g, sodium_mg, energy_kcal,
#          hydration_bakers, density_kg_m3, thermal_diffusivity, taxonomy_encoded
```

**Purpose**: structured feature vector feeds future oven parameter prediction model (temperature, time, preheat, mode, humidity). No heuristics. No text-to-text prediction. Only USDA nutrients + physics mixing rules.

**Training data**: not yet collected. Pipeline reserved for future GBDT/NN training.

**Formulas**: see `src/_03_feature_extraction/FEATURES.md` for exact calculations.

## Gotchas

- Some ingredients (cinnamon, coffee) return wrong USDA foods - priority list in `ingredient_lookup.py` workaround
- Config path in main.py defaults to `../config/pipeline.yaml` (relative to src/)
- `--test` flag is broken - calls undefined `run_tests()` function (will error)

## Validation Module

`src/_04_validation/` validates generated recipes against physics/empirical data:
- `validator.py`: RecipeValidator class maps taxonomy → category → checks calories/macros
- Data: `calories_reference.json`, `macro_ranges.json`, `categories.json`, `moisture_loss.json`

```python
from src._04_validation.validator import RecipeValidator
validator = RecipeValidator()
result = validator.validate_calories("bread", energy_kcal=265)
```