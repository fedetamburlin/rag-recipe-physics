import re
import json
import time
import ast
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np
import yaml
import logging

logger = logging.getLogger(__name__)

try:
    import ollama
except ImportError:
    raise ImportError("ollama package required: pip install ollama")


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
    
    def _ingest_dataset(self):
        from datasets import load_dataset
        
        dataset_name = self.config.get('rag', {}).get('dataset_name', 'nuhuibrahim/recifine')
        
        logger.info(f"Loading dataset: {dataset_name}")
        dataset = load_dataset(dataset_name, split=f"train[:{self.dataset_size}]")
        
        logger.info(f"Processing {len(dataset)} recipes...")
        
        documents = []
        metadata = []
        
        for i, row in enumerate(dataset):
            title = row.get('title', f'Recipe {i}').strip() or f'Recipe {i}'
            
            try:
                dir_list = ast.literal_eval(row.get('directions', '[]'))
                instructions = ' '.join(dir_list[:5])
            except:
                instructions = str(row.get('directions', ''))[:200]
            
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
        
        avg_ing = sum(len(r.ingredients.split(',')) for r in retrieved) // len(retrieved)
        
        context = "\n".join(
            f"- {r.title}: {r.ingredients[:100]}"
            for r in retrieved
        )
        
        system_prompt = (
            "Generate a recipe. Output ONLY exactly this format with percentages:\n\n"
            "INGREDIENTS: flour 30%, sugar 25%, butter 20%, egg 15%, milk 10%\n"
            "TITLE: Recipe Name\n\n"
            "Replace with your recipe. Use exactly 5 ingredients. Percentages MUST sum to 100%.\n"
            "IMPORTANT: Salt MUST be 1% or less. Other ingredients fill the rest."
        )
        
        user_prompt = f"Context:\n\n{context}\n\n"
        
        if forbidden:
            user_prompt += f"FORBIDDEN INGREDIENTS: {', '.join(forbidden)}.\n"
        
        user_prompt += f"\nTASK: Create a new recipe that satisfies: {query}. Use about {avg_ing} ingredients."
        
        if taxonomy:
            user_prompt += f"\nType: {taxonomy}"
        
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
        ingredient_data = self.parse_ingredients(generated_text)

        if not ingredient_data:
            return {}
        
        try:
            from pathlib import Path
            import importlib.util
            
            project_root = Path(__file__).parent.parent
            nutrition_path = project_root / "nutrition"
            
            spec = importlib.util.spec_from_file_location("ingredient_lookup", 
                          nutrition_path / "ingredient_lookup.py")
            ik = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ik)
            
            spec2 = importlib.util.spec_from_file_location("nutrition_calculator",
                          nutrition_path / "nutrition_calculator.py")
            nc = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(nc)
            
            # Get nutrition calculator
            calc = nc.NutritionCalculator()
            
            # Calculate scaled nutrition for each ingredient
            scaled_nutrition = {}
            
            for ing_name, percentage in ingredient_data:
                matches = ik.IngredientMatcher().match(ing_name)
                if not matches:
                    continue
                
                fdc_id = matches[0]['fdc_id']
                nutrients = calc.get_food_nutrients(fdc_id)
                
                for nut_name, data in nutrients.items():
                    if data['amount'] is None:
                        continue
                    
                    # Scale by percentage (already decimal from normalization)
                    scaled_value = data['amount'] * percentage
                    
                    if nut_name not in scaled_nutrition:
                        scaled_nutrition[nut_name] = {'unit': data['unit'], 'amount': 0}
                    
                    scaled_nutrition[nut_name]['amount'] += scaled_value
            
            # Get summary with mapped nutrients
            return calc.get_summary(scaled_nutrition)
            
        except Exception as e:
            import traceback
            print(f"[Nutrition Error: {e}]")
            traceback.print_exc()
            return {}