"""Nutrition calculator for recipe ingredients."""
try:
    from src.nutrition.db import get_connection
except ModuleNotFoundError:
    from nutrition.db import get_connection


class NutritionCalculator:
    """Calculate total nutrition for a recipe using robust code-based lookup."""

    # Standard nutrients to include in summary output
    SUMMARY_CODES = [
        'ENERGY', 'PROTEIN', 'CARB', 'FAT', 'FIBER', 'SUGAR',
        'CHOLESTEROL', 'NA', 'K', 'CA', 'FE', 'VITC'
    ]

    def __init__(self):
        self._code_cache = self._load_code_cache()

    def _load_code_cache(self) -> dict:
        """Load mapping: code -> nutrient_id"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, id FROM nutrients")
        code_to_id = {row['code']: row['id'] for row in cursor.fetchall()}
        conn.close()
        return code_to_id

    def get_nutrient_id_by_code(self, code: str) -> int:
        """Get nutrient ID from code (e.g., 'ENERGY' -> 1008)"""
        return self._code_cache.get(code)

    def get_food_nutrients(self, fdc_id: int) -> dict:
        """Get all nutrients for a food by fdc_id"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.code, n.unit_name, fn.amount
            FROM food_nutrients fn
            JOIN nutrients n ON fn.nutrient_id = n.id
            WHERE fn.fdc_id = ?
        """, (fdc_id,))

        result = {}
        for row in cursor.fetchall():
            code = row['code']
            if code not in result:
                result[code] = {'unit': row['unit_name'], 'amount': row['amount']}
        conn.close()
        return result

    def calculate_from_fdc_ids(self, fdc_ids: list[int]) -> dict:
        """Aggregate nutrients from multiple foods"""
        aggregated = {}
        for fdc_id in fdc_ids:
            nutrients = self.get_food_nutrients(fdc_id)
            for code, data in nutrients.items():
                if code not in aggregated:
                    aggregated[code] = {'unit': data['unit'], 'amount': 0}
                if data['amount'] is not None:
                    aggregated[code]['amount'] += data['amount']
        return aggregated

    def calculate_from_matched(self, matched_foods: dict) -> dict:
        """Calculate nutrition from matched ingredient foods"""
        fdc_ids = [matches[0]['fdc_id'] for ing, matches in matched_foods.items() if matches]
        return self.calculate_from_fdc_ids(fdc_ids)

    def get_summary(self, nutrition_data: dict) -> dict:
        """Extract standard summary nutrients"""
        summary = {}
        for code in self.SUMMARY_CODES:
            if code in nutrition_data:
                data = nutrition_data[code]
                if data['amount'] is not None:
                    summary[code] = {'amount': round(data['amount'], 1), 'unit': data['unit']}
        return summary


def calculate_recipe_nutrients(ingredients: list[str], matched_foods: dict = None) -> dict:
    """Main entry point: calculate nutrition for a recipe."""
    try:
        from src.nutrition.ingredient_lookup import IngredientMatcher
    except ModuleNotFoundError:
        from nutrition.ingredient_lookup import IngredientMatcher
    matcher = IngredientMatcher()
    if not matched_foods:
        matched_foods = matcher.match_ingredients(ingredients)
    calc = NutritionCalculator()
    return calc.get_summary(calc.calculate_from_matched(matched_foods))


if __name__ == "__main__":
    # Quick test
    ingredients = ["butter", "flour", "sugar"]
    from src.nutrition.ingredient_lookup import IngredientMatcher
    matcher = IngredientMatcher()
    matched = matcher.match_ingredients(ingredients)
    result = calculate_recipe_nutrients(ingredients, matched)
    print("Nutrition:", result)