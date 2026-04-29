"""Nutrition calculator for recipe ingredients."""

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "usda_nutrients.db"

NUTRIENT_MAP = {
    'Energy': ['Energy (Atwater General Factors)', 'Energy (Atwater Specific Factors)', 'Energy'],
    'Protein': ['Protein', 'Protein (N x 6.25)'],
    'Carbohydrates': ['Carbohydrate, by difference', 'Carbohydrate, total'],
    'Fat': ['Total lipid (fat)', 'Total fat (NLEA)'],
    'Fiber': ['Fiber, total dietary', 'Fiber, crude (DO NOT USE - Archived)'],
    'Sugar': ['Sugars, total', 'Sugars, total (NLEA)'],
    'Sodium': ['Sodium, Na'],
    'Cholesterol': ['Cholesterol'],
    'Saturated Fat': ['Fatty acids, total saturated'],
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class NutritionCalculator:
    """Calculate total nutrition for a recipe."""
    
    def __init__(self):
        self._nutrient_id_map = self._load_nutrient_map()
    
    def _load_nutrient_map(self) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM nutrients")
        rows = cursor.fetchall()
        conn.close()
        
        name_to_id = {}
        for row in rows:
            name_to_id[row['name'].lower()] = row['id']
            name_to_id[row['name']] = row['id']
        
        return name_to_id
    
    def get_nutrient_id(self, nutrient_name: str) -> Optional[int]:
        name_lower = nutrient_name.lower()
        
        if name_lower in self._nutrient_id_map:
            return self._nutrient_id_map[name_lower]
        
        for key, aliases in NUTRIENT_MAP.items():
            if nutrient_name in aliases:
                for alias in aliases:
                    if alias.lower() in self._nutrient_id_map:
                        return self._nutrient_id_map[alias.lower()]
        
        return None
    
    def get_food_nutrients(self, fdc_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT n.name, n.unit_name, fn.amount
            FROM food_nutrients fn
            JOIN nutrients n ON fn.nutrient_id = n.id
            WHERE fn.fdc_id = ?
        """, (fdc_id,))
        
        results = {row['name']: {'unit': row['unit_name'], 'amount': row['amount']} 
                   for row in cursor.fetchall()}
        conn.close()
        return results
    
    def calculate_from_fdc_ids(self, fdc_ids: list[int]) -> dict:
        aggregated = {}
        
        for fdc_id in fdc_ids:
            nutrients = self.get_food_nutrients(fdc_id)
            
            for name, data in nutrients.items():
                if name not in aggregated:
                    aggregated[name] = {'unit': data['unit'], 'amount': 0}
                
                if data['amount'] is not None:
                    aggregated[name]['amount'] += data['amount']
        
        return aggregated
    
    def calculate_from_matched(self, matched_foods: dict) -> dict:
        fdc_ids = []
        
        for ing, matches in matched_foods.items():
            if matches:
                fdc_ids.append(matches[0]['fdc_id'])
        
        return self.calculate_from_fdc_ids(fdc_ids)
    
    def get_summary(self, nutrition_data: dict) -> dict:
        summary = {}
        
        for category, aliases in NUTRIENT_MAP.items():
            for alias in aliases:
                if alias in nutrition_data:
                    data = nutrition_data[alias]
                    if data['amount'] is not None:
                        summary[category] = {
                            'amount': round(data['amount'], 1),
                            'unit': data['unit']
                        }
                        break
        
        return summary


def calculate_recipe_nutrients(ingredients: list[str], matched_foods: dict) -> dict:
    """Main entry point for calculating recipe nutrition."""
    from src.nutrition.ingredient_lookup import IngredientMatcher
    
    matcher = IngredientMatcher()
    
    if not matched_foods:
        matched_foods = matcher.match_ingredients(ingredients)
    
    calculator = NutritionCalculator()
    nutrition = calculator.calculate_from_matched(matched_foods)
    
    return calculator.get_summary(nutrition)


if __name__ == "__main__":
    test_ingredients = ["butter", "flour", "sugar", "egg", "milk"]
    
    print("Testing nutrition calculation...")
    print(f"Ingredients: {test_ingredients}\n")
    
    from src.nutrition.ingredient_lookup import IngredientMatcher
    matcher = IngredientMatcher()
    matched = matcher.match_ingredients(test_ingredients)
    
    print("Matched foods:")
    for ing, foods in matched.items():
        if foods:
            print(f"  {ing}: {foods[0]['description']}")
    
    print("\nNutrition summary:")
    result = calculate_recipe_nutrients(test_ingredients, matched)
    for k, v in result.items():
        print(f"  {k}: {v['amount']} {v['unit']}")