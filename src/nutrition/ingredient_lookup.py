"""Ingredient matching with USDA database."""

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "usda_nutrients.db"

DEFAULT_TOP_K = 3
MIN_SCORE = 0.3

# Priority list: preferred matches for common ingredients (flexible matching)
INGREDIENT_PRIORITY = {
    'egg': ['egg whole', 'eggs, whole', 'egg, whole', 'eggs'],
    'eggs': ['egg whole', 'eggs, whole', 'egg, whole', 'eggs'],
    'sugar': ['sugars, granulated', 'sugars, brown', 'sugars, powdered'],
    'brown sugar': ['sugars, brown'],
    'milk': ['milk, whole', 'milk, 2%', 'milk, 1%', 'milk, skim'],
    'butter': ['butter, salted', 'butter, unsalted'],
    'flour': ['flour, all-purpose', 'flour, white', 'flour, whole wheat', 'flour, 00'],
    'chocolate': ['chocolate, dark', 'chocolate, semisweet', 'cocoa powder'],
    'cocoa powder': ['cocoa, dry powder, unsweetened', 'cocoa powder'],
    'cream': ['cream, heavy', 'cream, whipping', 'cream, half and half'],
    'cheese': ['cheese, cheddar', 'cheese, mozzarella', 'cheese, parmesan'],
    'oil': ['olive oil', 'oil, olive', 'oil, vegetable', 'oil, canola'],
    'salt': ['salt, table', 'salt, sea'],
    'honey': ['honey, raw', 'honey, clover'],
    # Spices and flavorings
    'cinnamon': ['Spices, cinnamon, ground'],
    'nutmeg': ['Spices, nutmeg, ground'],
    'clove': ['Spices, cloves, ground'],
    'pepper': ['Spices, pepper, black'],
    'ginger': ['Spices, ginger, ground'],
    'coffee': ['Beverages, coffee, brewed, espresso', 'Beverages, coffee, brewed, breakfast blend', 'Coffee'],
    'vanilla': ['Vanilla extract'],
    'vanilla extract': ['vanilla extract'],
    'oregano': ['Spices, oregano, dried'],
    'thyme': ['Spices, thyme, dried'],
    'rosemary': ['Spices, rosemary, dried'],
    'sage': ['Spices, sage, ground'],
    'basil': ['Basil, fresh', 'Spices, basil, dried'],
    # Vegetables
    'garlic': ['garlic, raw'],
    'onion': ['onions, raw'],
    'carrot': ['carrots, raw'],
    'celery': ['celery, raw'],
    'tomato': ['tomato, red', 'tomatoes, raw'],
    # Proteins
    'pasta': ['pasta, dry', 'pasta, enriched'],
    'chicken': ['chicken breast', 'chicken, breast'],
    'chicken breast': ['chicken breast'],
    'salmon': ['salmon, atlantic', 'salmon, raw'],
    'lemon': ['lemon, raw'],
    'rice': ['rice, white', 'rice, brown'],
    'potato': ['potato, raw', 'potatoes, raw'],
    'beef': ['beef, ground', 'beef, raw'],
    'onions': ['onions, raw'],
    'peas': ['peas, green'],
    'soy sauce': ['soy sauce'],
}

# Blacklist: patterns to exclude from fallback results
EXCLUDE_PATTERNS = {
    'egg': ['eggnog', 'meringue', 'custard', 'mayonnaise', 'quiche', 'yolk', 'white'],
    'eggs': ['eggnog', 'meringue', 'custard', 'mayonnaise', 'quiche', 'yolk', 'white'],
    'milk': ['buttermilk', 'milk chocolate', 'evaporated', 'condensed', 'butter'],
    'sugar': ['syrup', 'molasses', 'sorbitol', 'xylitol', 'artificial', 'brand', 'store', 'cereal', 'oatmeal'],
    'brown sugar': ['syrup', 'molasses', 'sorbitol', 'xylitol', 'artificial', 'brand', 'store', 'cereal', 'oatmeal'],
    'butter': ['butterbur', 'butterfly', 'nut', 'seed'],
    'chocolate': ['ice cream', 'candy', 'spread', 'pudding', 'cereal'],
    'cocoa powder': ['mix', 'beverage', 'drink', 'cereal'],
    'salmon': ['salmonberry', 'salmonberries'],
    'lemon': ['lemon peel', 'lemonade'],
    'rice': ['cracker', 'puff', 'chip'],
    'potato': ['flour', 'starch', 'chip', 'flake'],
    'beef': ['tallow', 'extract', 'broth cube'],
    'chicken': ['spread', 'noodle', 'soup', 'pate'],
    'water': ['melon', 'watercress'],
    'yeast': ['extract', 'spread'],
    'vanilla': ['extract', 'flavor', 'ice cream'],
    'vanilla extract': ['flavor', 'ice cream'],
    'graham': ['chocolate', 'coated'],
    'coffee': ['soy', 'silk', 'latte', 'cappuccino', 'iced', 'substitute', 'chicory', 'coffeecake', 'cake', 'candy', 'bean', 'liqueur', 'cream'],
    'cinnamon': ['bun', 'cake', 'pie', 'roll', 'bagel', 'toast', 'cereal', 'oatmeal'],
    'nutmeg': ['ice cream', 'pie', 'cake', 'bun', 'custard'],
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize(text: str) -> str:
    return text.lower().strip()


def _matches_exclude(description: str, exclude_list: list[str]) -> bool:
    """Check if description matches any exclude pattern."""
    desc_lower = description.lower()
    return any(pat in desc_lower for pat in exclude_list)


class IngredientMatcher:
    """Match ingredients to USDA foods."""
    
    def __init__(self, top_k: int = DEFAULT_TOP_K):
        self.top_k = top_k
        self._cache = {}
    
    def search_by_name(self, query: str, limit: int = 50):
        """Search foods by name with priority: exact > starts with > contains."""
        conn = get_connection()
        cursor = conn.cursor()
        
        q = normalize(query)
        
        cursor.execute("""
            SELECT fdc_id, description, data_type,
                   CASE 
                       WHEN LOWER(description) = ? THEN 0
                       WHEN LOWER(description) LIKE ? THEN 1
                       WHEN LOWER(description) LIKE ? THEN 2
                       ELSE 3
                   END as priority
            FROM foods
            WHERE LOWER(description) LIKE ?
            ORDER BY priority, LENGTH(description)
            LIMIT ?
        """, (q, f"{q}%", f"% {q}%", f"%{q}%", limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def search_priority(self, ingredient: str) -> list[dict]:
        """Try priority list matches first."""
        ing_lower = ingredient.lower()
        
        if ing_lower not in INGREDIENT_PRIORITY:
            return []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        preferred = INGREDIENT_PRIORITY[ing_lower]
        
        # Build query with OR for each preferred term
        conditions = []
        params = []
        for term in preferred:
            conditions.append("LOWER(description) LIKE ?")
            params.append(f"%{term}%")
        
        query = f"""
            SELECT fdc_id, description, data_type
            FROM foods
            WHERE {' OR '.join(conditions)}
            ORDER BY 
                CASE WHEN LOWER(description) LIKE '%beverages, coffee%' THEN 0
                     WHEN LOWER(description) LIKE '%coffee, brewed%' THEN 1
                     ELSE 2
                END,
                LENGTH(description)
            LIMIT 10
        """
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Filter out brand-specific results and blacklist patterns
        filtered = [r for r in results if 'brand' not in r['description'].lower()]
        
        # Apply ingredient-specific blacklist if exists
        if ing_lower in EXCLUDE_PATTERNS:
            exclude_list = EXCLUDE_PATTERNS[ing_lower]
            filtered = [r for r in filtered if not _matches_exclude(r['description'], exclude_list)]
        
        return filtered[:self.top_k] if filtered else results[:self.top_k]
    
    def search_fuzzy(self, query: str, limit: int = 100) -> list[dict]:
        """Fallback fuzzy search with blacklist filtering."""
        conn = get_connection()
        cursor = conn.cursor()
        
        exclude_list = EXCLUDE_PATTERNS.get(query.lower(), [])
        
        cursor.execute("""
            SELECT fdc_id, description, data_type
            FROM foods
            WHERE LOWER(description) LIKE ?
            LIMIT ?
        """, (f"%{normalize(query[:5])}%", limit))
        
        candidates = cursor.fetchall()
        conn.close()
        
        scored = []
        for row in candidates:
            desc = row['description']
            if exclude_list and _matches_exclude(desc, exclude_list):
                continue
            
            similarity = self._similarity(query, desc)
            if similarity >= 0.35:
                scored.append((similarity, dict(row)))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:self.top_k]]
    
    def _similarity(self, a: str, b: str) -> float:
        a_norm = normalize(a)
        b_norm = normalize(b)
        
        if a_norm in b_norm:
            return 0.9
        if b_norm in a_norm:
            return 0.8
        
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a_norm, b_norm).ratio()
    
    def match(self, ingredient: str) -> list[dict]:
        if ingredient in self._cache:
            return self._cache[ingredient]
        
        # 1. Try priority list first
        results = self.search_priority(ingredient)
        
        # 2. Fallback to search by name
        if not results:
            results = self.search_by_name(ingredient)
        
        # 3. Final fallback to fuzzy
        if not results:
            results = self.search_fuzzy(ingredient)
        
        self._cache[ingredient] = results[:self.top_k]
        return self._cache[ingredient]
    
    def match_ingredients(self, ingredients: list[str]) -> dict[str, list[dict]]:
        results = {}
        for ing in ingredients:
            matches = self.match(ing)
            if matches:
                results[ing] = matches
        return results
    
    def clear_cache(self):
        self._cache.clear()


def get_food_nutrients(fdc_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT n.name, n.unit_name, fn.amount
        FROM food_nutrients fn
        JOIN nutrients n ON fn.nutrient_id = n.id
        WHERE fn.fdc_id = ?
    """, (fdc_id,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


if __name__ == "__main__":
    matcher = IngredientMatcher()
    
    test_ingredients = ["butter", "flour", "sugar", "egg", "milk", "chocolate"]
    
    print("Testing ingredient matching...")
    for ing in test_ingredients:
        matches = matcher.match(ing)
        print(f"\n{ing}:")
        for m in matches[:3]:
            print(f"  - {m['description']} (fdc_id={m['fdc_id']})")