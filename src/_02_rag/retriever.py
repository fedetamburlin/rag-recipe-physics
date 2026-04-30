import re
import json
import time
import ast
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List
import numpy as np
import yaml
import logging

logger = logging.getLogger(__name__)

try:
    import ollama
except ImportError:
    raise ImportError("ollama package required: pip install ollama")

try:
    from nutrition.ingredient_lookup import IngredientMatcher
    from nutrition.nutrition_calculator import NutritionCalculator
except ModuleNotFoundError:
    try:
        from src.nutrition.ingredient_lookup import IngredientMatcher
        from src.nutrition.nutrition_calculator import NutritionCalculator
    except ModuleNotFoundError:
        IngredientMatcher = None
        NutritionCalculator = None


# Rough volume-to-weight conversions (grams)
UNIT_WEIGHTS = {
    "cup": 240, "c": 240, "c.": 240,
    "tbsp": 15, "tablespoon": 15, "tbs": 15,
    "tsp": 5, "teaspoon": 5,
    "oz": 28, "ounce": 28,
    "lb": 454, "pound": 454,
    "g": 1, "gm": 1, "gram": 1,
    "kg": 1000, "kilogram": 1000,
    "ml": 1, "l": 1000, "liter": 1000,
    "stick": 113,  # butter stick
}

# Density rough estimates for common ingredients (g per cup or unit)
INGREDIENT_DENSITY = {
    "flour": 120, "sugar": 200, "brown sugar": 200, "powdered sugar": 120,
    "butter": 227, "oil": 218, "lard": 205, "shortening": 205,
    "water": 240, "milk": 244, "buttermilk": 242, "cream": 240,
    "egg": 50, "eggs": 50, "egg white": 30, "egg yolk": 18,
    "honey": 340, "syrup": 340, "molasses": 340,
    "cocoa": 85, "chocolate": 170,
    "oats": 90, "cornmeal": 145,
    "cheese": 100,  # grated/shredded
    "chicken": 150, "beef": 150, "pork": 150, "fish": 150,
    "yeast": 140,  # active dry per packet ~7g but per cup ~140g
}


def _parse_ingredient_line(line: str) -> tuple:
    """Parse a single ingredient line into (name, approx_grams)."""
    line = line.strip().lower()
    if not line:
        return None, 0

    # Extract number
    num_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:\d/\d+)?', line)
    if not num_match:
        return None, 0
    num = float(num_match.group(1))

    # Handle fractions like 1/2, 3/4
    frac_match = re.search(r'(\d)/(\d)', line)
    if frac_match:
        num += float(frac_match.group(1)) / float(frac_match.group(2))

    # Extract unit
    unit = None
    for u in UNIT_WEIGHTS:
        pattern = r'\b' + re.escape(u) + r'\.?\b'
        if re.search(pattern, line):
            unit = u
            break

    # Default: if no unit found, assume the number is count (eggs, lemons, etc.)
    if unit:
        base_weight = num * UNIT_WEIGHTS[unit]
    else:
        base_weight = num * 50  # Default ~50g per item

    # Apply density based on ingredient name
    density = 1.0
    for ing_key, ing_density in INGREDIENT_DENSITY.items():
        if ing_key in line:
            # If unit was a volume measure, scale by density relative to water
            if unit in ("cup", "c", "c.", "tbsp", "tsp", "ml"):
                density = ing_density / 240  # Normalize per cup
            else:
                density = ing_density / 150  # Rough average
            break

    weight = base_weight * density

    # Extract name (everything after the measurement)
    name = re.sub(r'^[^a-z]*', '', line).strip()
    # Clean up common prefixes
    name = re.sub(r'^(?:\d+\s+)?(?:\d/\d+\s+)?(?:c\.?|cup|tbsp|tsp|oz|lb|g|ml|stick|package|pkg|can)\s*', '', name)
    name = re.sub(r',.*$', '', name).strip()

    return name, weight


def _categorize_ingredient(name: str) -> str:
    """Map ingredient name to macro category."""
    name = name.lower()
    categories = {
        "flour": ["flour", "farina", "semola", "cornmeal", "meal"],
        "sugar": ["sugar", "honey", "syrup", "molasses", "sweetener"],
        "fat": ["butter", "oil", "lard", "shortening", "margarine", "ghee"],
        "liquid": ["water", "milk", "cream", "buttermilk", "beer", "wine", "juice", "coffee", "liqueur"],
        "protein": ["egg", "chicken", "beef", "pork", "lamb", "turkey", "fish", "salmon", "cod", "tuna",
                   "cheese", "bacon", "ham", "sausage", "yogurt"],
        "leavening": ["yeast", "baking powder", "baking soda", "bicarbonate"],
        "chocolate": ["cocoa", "chocolate"],
        "salt": ["salt", "sale"],
        "starch": ["cornstarch", "arrowroot", "starch"],
    }
    for cat, keywords in categories.items():
        if any(k in name for k in keywords):
            return cat
    return "other"


def extract_proportions_from_recipes(retrieved) -> str:
    """Extract rough ingredient proportions from retrieved recipes for few-shot prompting."""
    all_categories = {}
    total_weight = 0

    for r in retrieved[:2]:  # Only top 2
        items = [i.strip() for i in r.ingredients.split(",") if i.strip()]
        for item in items:
            name, weight = _parse_ingredient_line(item)
            if name and weight > 0:
                cat = _categorize_ingredient(name)
                all_categories[cat] = all_categories.get(cat, 0) + weight
                total_weight += weight

    if total_weight == 0:
        return "No proportion data available."

    # Build proportion string
    proportions = []
    for cat in ["flour", "protein", "sugar", "fat", "liquid", "chocolate", "leavening", "salt", "other"]:
        if cat in all_categories:
            pct = (all_categories[cat] / total_weight) * 100
            if pct > 2:  # Only show categories > 2%
                proportions.append(f"{cat} ~{pct:.0f}%")

    return ", ".join(proportions)


@dataclass
class RetrievedRecipe:
    rank: int
    bi_score: float
    cross_score: float
    title: str
    ingredients: str
    instructions: str


class RAGRetriever:
    """RAG pipeline with retrieval + generation."""
    
    def __init__(self, config_path: str = "config/pipeline.yaml", debug: bool = False):
        self.config = {}
        if Path(config_path).exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        
        ret_cfg = self.config.get('retrieval', {})
        llm_cfg = self.config.get('llm', {})
        
        self.first_stage_k = ret_cfg.get('first_stage_k', 30)
        self.final_k = ret_cfg.get('final_k', 3)
        
        self.embedder_model = ret_cfg.get('embedder_model', 'sentence-transformers/all-MiniLM-L6-v2')
        self.reranker_model = ret_cfg.get('reranker_model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        self.llm_model = llm_cfg.get('generation_model', 'qwen2.5:3b')
        self.temperature = llm_cfg.get('temperature', 0.1)
        self.num_ctx = llm_cfg.get('num_ctx', 8192)
        self.num_predict = llm_cfg.get('num_predict', 1024)
        
        self.dataset_size = self.config.get('rag', {}).get('dataset_size', 500)
        self.cache_dir = Path(self.config.get('rag', {}).get('cache_dir', 'cache/rag'))
        
        self.debug = debug
        self._embedder = None
        self._reranker = None
        self._embeddings = None
        self._documents = None
        self._metadata = None
    
    def _init_models(self):
        if self._embedder is not None:
            return
        
        from sentence_transformers import SentenceTransformer, CrossEncoder
        
        logger.info(f"Loading embedder: {self.embedder_model}")
        self._embedder = SentenceTransformer(self.embedder_model)
        
        logger.info(f"Loading reranker: {self.reranker_model}")
        self._reranker = CrossEncoder(self.reranker_model)
    
    def _load_cache(self) -> bool:
        key = f"recipes_{self.dataset_size}"
        emb_path = self.cache_dir / f"{key}_embeddings.npy"
        meta_path = self.cache_dir / f"{key}_metadata.json"
        doc_path = self.cache_dir / f"{key}_documents.json"
        
        if not all(p.exists() for p in [emb_path, meta_path, doc_path]):
            return False
        
        logger.info(f"Loading cache from {self.cache_dir}")
        self._embeddings = np.load(emb_path)
        with open(meta_path) as f:
            self._metadata = json.load(f)
        with open(doc_path) as f:
            self._documents = json.load(f)
        return True
    
    def _save_cache(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        key = f"recipes_{self.dataset_size}"
        
        np.save(self.cache_dir / f"{key}_embeddings.npy", self._embeddings)
        with open(self.cache_dir / f"{key}_metadata.json", 'w') as f:
            json.dump(self._metadata, f, ensure_ascii=False)
        with open(self.cache_dir / f"{key}_documents.json", 'w') as f:
            json.dump(self._documents, f, ensure_ascii=False)
        
        logger.info(f"Cache saved to {self.cache_dir}")
    
    @staticmethod
    def _is_oven_recipe(title: str, instructions: str) -> bool:
        """Filter dataset to keep only oven-bakeable recipes."""
        text = (title + " " + instructions).lower()
        exclude = [
            "no-bake", "no bake", "slow cooker", "crockpot", "stove top",
            "refrigerate", "no cook", "salad", "soup", "dip", "frosting",
            "no cooking", "freezer", "cold", "raw"
        ]
        if any(w in text for w in exclude):
            return False
        include = [
            "bake", "baking", "baked", "oven", "roast", "roasted",
            "bread", "cake", "pie", "tart", "cookie", "pastry",
            "275°", "300°", "325°", "350°", "375°", "400°", "425°", "450°",
            "degrees", "°f"
        ]
        return any(w in text for w in include)

    def _ingest_dataset(self):
        from datasets import load_dataset
        
        dataset_name = self.config.get('rag', {}).get('dataset_name', 'nuhuibrahim/recifine')
        
        logger.info(f"Loading dataset: {dataset_name}")
        dataset = load_dataset(dataset_name, split=f"train[:{self.dataset_size}]")
        
        logger.info(f"Processing {len(dataset)} recipes...")
        
        documents = []
        metadata = []
        skipped = 0
        
        for i, row in enumerate(dataset):
            title = row.get('title', f'Recipe {i}').strip() or f'Recipe {i}'
            
            try:
                dir_list = ast.literal_eval(row.get('directions', '[]'))
                instructions = ' '.join(dir_list[:5])
            except:
                instructions = str(row.get('directions', ''))[:200]
            
            if not self._is_oven_recipe(title, instructions):
                skipped += 1
                continue
            
            ingredients = row.get('ingredients', row.get('NER', ''))
            if isinstance(ingredients, str):
                items = re.findall(r'"([^"]*)"', ingredients)
                ingredients = ', '.join([i.strip() for i in items if i.strip()]) or ingredients[:200]
            
            doc = f"Title: {title}. Ingredients: {ingredients}. Method: {instructions[:200]}"
            documents.append(doc)
            
            metadata.append({
                'title': title,
                'ingredients': ingredients[:500],
                'instructions': instructions[:500],
            })
        
        logger.info(f"Kept {len(documents)} oven recipes (skipped {skipped})")
        
        logger.info(f"Encoding {len(documents)} documents...")
        t0 = time.time()
        self._embeddings = self._embedder.encode(
            documents, batch_size=64, show_progress_bar=True,
            convert_to_numpy=True, normalize_embeddings=True
        )
        logger.info(f"Encoding done in {time.time()-t0:.1f}s")
        
        self._documents = documents
        self._metadata = metadata
        
        self._save_cache()
    
    def _compute_taxonomy(self, retrieved: list[RetrievedRecipe]) -> str:
        keywords = {
            'leavened': ['bread', 'yeast', 'pizza', 'focaccia', 'brioche', 'dough', 'risen', 'ferment'],
            'whipped': ['meringue', 'sponge', 'ladyfinger', 'foam', 'whisked', 'aerated'],
            'doughs': ['shortcrust', 'tart', 'pastry', 'crust', 'pie'],
            'preserves': ['jam', 'marmalade', 'preserve', 'jelly', 'confiture', 'canning'],
            'creams': ['cream', 'custard', 'pudding', 'mousse', 'flan', 'ganache'],
            'meats': ['beef', 'chicken', 'pork', 'lamb', 'meat', 'roast', 'steak', 'breast', 'thigh'],
            'seafood': ['fish', 'salmon', 'tuna', 'cod', 'seafood', 'shrimp', 'tilapia'],
        }
        
        categories = []
        for r in retrieved:
            text = (r.title + ' ' + r.instructions).lower()
            for cat, words in keywords.items():
                if any(w in text for w in words):
                    categories.append(cat)
                    break
            else:
                categories.append('other')
        
        return max(set(categories), key=categories.count) if categories else 'other'
    
    def retrieve(self, query: str, forbidden: list[str] = None) -> list[RetrievedRecipe]:
        if self._embeddings is None:
            self._init_models()
            if not self._load_cache():
                self._ingest_dataset()
        
        forbidden = forbidden or []
        
        q_emb = self._embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        sims = np.dot(q_emb, self._embeddings.T).flatten()
        
        if forbidden:
            f_embs = self._embedder.encode(forbidden, convert_to_numpy=True, normalize_embeddings=True)
            penalty = np.max(np.dot(f_embs, self._embeddings.T), axis=0) * 0.7 + \
                      np.mean(np.dot(f_embs, self._embeddings.T), axis=0) * 0.3
            sims -= 0.5 * penalty
        
        top_idx = np.argsort(sims)[::-1][:self.first_stage_k]
        candidates = [self._documents[i] for i in top_idx]
        
        cross_scores = self._reranker.predict([[query, doc] for doc in candidates])
        cross_scores = (cross_scores - cross_scores.mean()) / (cross_scores.std() + 1e-8)
        
        best_local = np.argsort(cross_scores)[::-1][:self.final_k]
        
        results = []
        for rank, idx in enumerate(best_local):
            orig_idx = top_idx[idx]
            meta = self._metadata[orig_idx]
            
            results.append(RetrievedRecipe(
                rank=rank,
                bi_score=float(sims[orig_idx]),
                cross_score=float(cross_scores[idx]),
                title=meta['title'],
                ingredients=meta['ingredients'],
                instructions=meta['instructions'],
            ))
        
        return results
    
    def generate(self, query: str, retrieved: list[RetrievedRecipe], 
                 forbidden: list[str] = None, taxonomy: str = None) -> str:
        
        forbidden = forbidden or []
        
        # Use top 2 retrieved recipes with full context
        top_retrieved = retrieved[:2]
        avg_ing = sum(len(r.ingredients.split(',')) for r in top_retrieved) // len(top_retrieved)
        
        # Extract rough proportions from retrieved for few-shot
        proportions_text = extract_proportions_from_recipes(top_retrieved)
        
        context = "\n\n".join(
            f"Reference Recipe {i+1}: {r.title}\n"
            f"  Ingredients: {r.ingredients[:300]}\n"
            f"  Method: {r.instructions[:200]}"
            for i, r in enumerate(top_retrieved)
        )
        
        # Determine query category for few-shot examples
        q_lower = query.lower()
        
        # Build few-shot examples based on query type
        few_shot = ""
        if any(k in q_lower for k in ["bread", "baguette", "ciabatta", "focaccia"]):
            few_shot = (
                "Example (Bread):\n"
                "INGREDIENTS: flour 55%, water 35%, yeast 2%, salt 1.5%, oil 3.5%, sugar 3%\n"
                "TITLE: Simple White Bread\n\n"
            )
        elif any(k in q_lower for k in ["cake", "brownie", "muffin", "cupcake"]):
            few_shot = (
                "Example (Chocolate Cake):\n"
                "INGREDIENTS: flour 25%, sugar 25%, butter 15%, eggs 15%, milk 10%, cocoa 10%\n"
                "TITLE: Rich Chocolate Cake\n\n"
            )
        elif any(k in q_lower for k in ["roast", "chicken", "beef", "pork", "salmon", "fish"]):
            few_shot = (
                "Example (Roast Chicken):\n"
                "INGREDIENTS: chicken 70%, garlic 8%, lemon 8%, olive oil 7%, rosemary 4%, salt 1.5%, pepper 1.5%\n"
                "TITLE: Herb-Roasted Chicken\n\n"
            )
        elif any(k in q_lower for k in ["quiche", "souffle", "cheesecake", "custard"]):
            few_shot = (
                "Example (Quiche):\n"
                "INGREDIENTS: flour 30%, eggs 15%, milk 20%, cheese 15%, ham 10%, spinach 8%, salt 2%\n"
                "TITLE: Classic Ham and Cheese Quiche\n\n"
            )
        elif any(k in q_lower for k in ["cookie", "biscuit", "shortbread", "macaron"]):
            few_shot = (
                "Example (Chocolate Chip Cookies):\n"
                "INGREDIENTS: flour 30%, sugar 25%, butter 25%, eggs 10%, chocolate chips 8%, vanilla 1%, salt 1%\n"
                "TITLE: Classic Chocolate Chip Cookies\n\n"
            )

        system_prompt = (
            "You are a recipe assistant. Generate a realistic recipe inspired by the reference recipes provided.\n\n"
            f"{few_shot}"
            "CRITICAL RULES:\n"
            "1. Use ingredients SIMILAR to the reference recipes below.\n"
            "2. The main ingredient MUST match what the user asks for.\n"
            "3. Use ingredient PROPORTIONS similar to the example above.\n"
            "4. Output ONLY this exact format with PERCENTAGES:\n"
            "   INGREDIENTS: name XX%, name XX%, ...\n"
            "   TITLE: Recipe Name\n"
            "5. EVERY ingredient MUST have a percentage.\n"
            "6. Percentages MUST sum to 100%.\n"
            "7. Salt MUST be 1% or less.\n"
            "8. Use 4-8 ingredients.\n"
            "9. Do NOT invent ingredients unrelated to the reference recipes."
        )
        
        # Add proportion guide based on query keywords
        proportion_hint = ""
        if any(k in q_lower for k in ["bread", "baguette", "ciabatta", "focaccia"]):
            proportion_hint = "\nPROPORTION GUIDE: flour ~55%, water ~35%, yeast ~2%, salt ~1.5%, oil ~3%, sugar ~3.5%"
        elif any(k in q_lower for k in ["cake", "brownie", "muffin", "cupcake"]):
            proportion_hint = "\nPROPORTION GUIDE: flour ~25%, sugar ~25%, butter ~15%, eggs ~15%, milk ~10%, cocoa/chocolate ~10%"
        elif any(k in q_lower for k in ["roast", "chicken", "beef", "pork", "salmon", "fish"]):
            proportion_hint = "\nPROPORTION GUIDE: meat/fish ~70%, oil/butter ~8%, garlic/onion ~10%, lemon/herbs ~10%, salt ~1%, pepper ~1%"
        elif any(k in q_lower for k in ["quiche", "souffle", "cheesecake", "custard"]):
            proportion_hint = "\nPROPORTION GUIDE: flour/crust ~30%, eggs ~15%, milk/cream ~20%, cheese ~15%, filling ~15%, salt ~0.5%"
        elif any(k in q_lower for k in ["cookie", "biscuit", "shortbread", "macaron"]):
            proportion_hint = "\nPROPORTION GUIDE: flour ~30%, sugar ~25%, butter ~25%, eggs ~10%, vanilla ~5%, salt ~1%, chocolate/nuts ~4%"

        user_prompt = (
            f"Reference Recipes:\n\n{context}\n\n"
            f"REQUIREMENT: Create a recipe for '{query}'. "
            f"The main ingredients must be typical of '{query}'. "
            f"Use about {avg_ing} ingredients.{proportion_hint}"
        )
        
        if forbidden:
            user_prompt += f"\nFORBIDDEN INGREDIENTS: {', '.join(forbidden)}."
        
        if taxonomy:
            user_prompt += f"\nCategory: {taxonomy}"
        
        if self.debug:
            print(f"\n[DEBUG] System: {system_prompt[:200]}...")
            print(f"[DEBUG] User: {user_prompt[:500]}...")
        
        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": self.temperature,
                    "num_ctx": self.num_ctx,
                    "num_predict": self.num_predict,
                }
            )
            
            full = response["message"]["content"]
            print(full)
            
            return full
        except Exception as e:
            print(f"[Generation Error: {e}]")
            return f"Error: {e}"
    
    def parse_ingredients(self, generated_text: str) -> list[tuple[str, float]]:
        """Extract (name, percentage_decimal) list from generated recipe text."""
        import re

        text = generated_text.replace('\n', ' ').replace('**', '')
        text = re.sub(r'TITLE:.*', '', text, flags=re.I)

        UNIT_CONVERSION = {'tbsp': 8, 'tablespoon': 8, 'cup': 20, 'tsp': 3, 'teaspoon': 3}

        matches1 = re.findall(r'([a-zA-Z\s\-]+?)\s+(\d+)%', text)
        matches2 = re.findall(r'(\d+)%\s+([a-zA-Z\s\-]+?)(?:\s|$|,|\.)', text)
        matches_tbsp = re.findall(r'(\d+)\s*(?:tbsp|tablespoon)s?\s+([a-zA-Z\s\-]+?)(?:\s|$|,|\.)', text, re.I)
        matches_cup = re.findall(r'(\d+)\s*(?:cups?)\s+([a-zA-Z\s\-]+?)(?:\s|$|,|\.)', text, re.I)
        matches_tsp = re.findall(r'(\d+)\s*(?:tsp|teaspoon)s?\s+([a-zA-Z\s\-]+?)(?:\s|$|,|\.)', text, re.I)

        all_matches = []
        for name, pct in matches1:
            all_matches.append((name.strip(), int(pct)))
        for pct, name in matches2:
            all_matches.append((name.strip(), int(pct)))
        for num, name in matches_tbsp:
            all_matches.append((name.strip(), int(num) * UNIT_CONVERSION['tbsp']))
        for num, name in matches_cup:
            all_matches.append((name.strip(), int(num) * UNIT_CONVERSION['cup']))
        for num, name in matches_tsp:
            all_matches.append((name.strip(), int(num) * UNIT_CONVERSION['tsp']))

        normalized = []
        for name, pct in all_matches:
            if 'salt' in name.lower() and pct > 1:
                pct = 1
            if pct > 0 and len(name) > 2:
                normalized.append((name.lower(), pct))

        normalized = [(n, p / 100.0) for n, p in normalized]

        total = sum(p for _, p in normalized)
        if total > 0 and abs(total - 1.0) > 0.01:
            scale = 1.0 / total
            normalized = [(n, p * scale) for n, p in normalized]
            total_pct = total * 100
            if total_pct < 50 or total_pct > 150:
                print(f"[Warning: Ingredients total {int(total_pct)}%, scaled to 100%]")

        return normalized

    def calculate_recipe_nutrition(self, generated_text: str) -> dict:
        """Parse ingredients from generated recipe and calculate nutrition scaled by percentage."""
        if IngredientMatcher is None or NutritionCalculator is None:
            logger.warning("Nutrition modules not available")
            return {}

        ingredient_data = self.parse_ingredients(generated_text)
        if not ingredient_data:
            return {}

        calc = NutritionCalculator()
        matcher = IngredientMatcher()
        scaled_nutrition: dict = {}

        for ing_name, percentage in ingredient_data:
            matches = matcher.match(ing_name)
            if not matches:
                continue

            # Pick best match: prefer foods with WATER data (critical for hydration)
            nutrients = None
            for m in matches:
                test = calc.get_food_nutrients(m['fdc_id'])
                if test.get('WATER', {}).get('amount') is not None:
                    nutrients = test
                    break
            if nutrients is None:
                nutrients = calc.get_food_nutrients(matches[0]['fdc_id'])

            for nut_name, data in nutrients.items():
                if data['amount'] is None:
                    continue
                scaled_value = data['amount'] * percentage
                if nut_name not in scaled_nutrition:
                    scaled_nutrition[nut_name] = {'unit': data['unit'], 'amount': 0.0}
                scaled_nutrition[nut_name]['amount'] += scaled_value

        return calc.get_summary(scaled_nutrition)