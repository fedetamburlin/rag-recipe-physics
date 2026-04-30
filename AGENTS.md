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

- **Ollama** running on `localhost:11434` with:
  - `gemma2:9b` for recipe generation (produces realistic proportions)
  - `qwen2.5:3b` for query parsing (lightweight, fast)
- **Python**: sentence-transformers, cross-encoders, datasets, ollama, numpy, pyyaml

## Config

`config/pipeline.yaml` controls everything:
- Retrieval: `first_stage_k: 30`, `final_k: 3`, embedder (`all-MiniLM-L6-v2`), reranker (`ms-marco-MiniLM-L-6-v2`)
- LLM generation: `gemma2:9b` (was `qwen2.5:3b` — too small for accurate proportions)
- LLM parsing: `qwen2.5:3b`
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
          ├─ Nutrition calculation (USDA DB, scaled by %)
          └─ _is_oven_recipe() filters dataset to ~23k oven recipes

      → Ollama generation (gemma2:9b)
           └─ Few-shot prompt with examples → structured recipe

      → Feature Extraction (_03_feature_extraction/feature_extractor.py)
           └─ 11 physicochemical features → future oven prediction

      → Classification (_03_feature_extraction/classifier.py)
           └─ 4 families: dough_structured, batter_baked, solid_roast, custard_set

      → Validation (_04_validation/physics_validator.py)
           └─ Category-specific physics ranges (hydration, salt, yeast, protein, fat, sugar)
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
├── _04_validation/          # Step 4: physics validation (physics_validator.py)
│                              └── Validates against empirical ranges per category
├── nutrition/               # Shared library (USDA DB, 19k foods, 44 nutrients)
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

**Ingredient matching**: `ingredient_lookup.py` uses priority lists + blacklists to avoid bad matches (e.g. `eggs` → whole eggs not yolk, `brown sugar` → actual sugar not cereal). If the top USDA match lacks `WATER` data, the retriever falls back to the next candidate — critical for accurate hydration calculations.

## Feature Extraction

`src/_03_feature_extraction/feature_extractor.py` extracts 11 physicochemical features from LLM-generated recipes:

```python
from src._03_feature_extraction.feature_extractor import RecipeFeatureExtractor

extractor = RecipeFeatureExtractor()
features = extractor.extract(ingredients, nutrition, taxonomy, category)
# Returns: water_g, protein_g, fat_g, carbs_g, sodium_mg, energy_kcal,
#          hydration_bakers, density_kg_m3, thermal_diffusivity,
#          taxonomy_encoded, category_encoded
```

**Purpose**: structured feature vector feeds future oven parameter prediction model (temperature, time, preheat, mode, humidity). No heuristics. No text-to-text prediction. Only USDA nutrients + physics mixing rules.

**Training data**: not yet collected. Pipeline reserved for future GBDT/NN training.

**Formulas**: see `src/_03_feature_extraction/FEATURES.md` for exact calculations.

## Validation

`src/_04_validation/physics_validator.py` validates generated recipes against physics/empirical data per category:

```python
from src._04_validation.physics_validator import validate_recipe

result = validate_recipe(ingredients, nutrition, category="dough_structured")
# result["status"] in {"valid", "warning", "invalid", "unknown_category"}
```

**Important**: validation checks `salt_pct` and `yeast_pct` as **true percentages of total ingredients** (0.01 = 1%), because the LLM generates proportions as percentages of the whole recipe. These are NOT baker's percentages (which are relative to flour weight).

**Hydration calculation**: baker's hydration counts explicit liquids (water, milk, cream) **plus eggs and butter** as water sources. Eggs are ~75% water and butter ~16% water — excluding them under-reports hydration for batters and enriched doughs.

## Gotchas

- `gemma2:9b` required for generation — `qwen2.5:3b` produces absurd proportions (yeast 38%, flour 0% in cake)
- Some ingredients need priority-list overrides in `nutrition/ingredient_lookup.py`
- Config path in main.py defaults to `../config/pipeline.yaml` (relative to src/)
- `--test` flag is broken — calls undefined `run_tests()` function (will error)
