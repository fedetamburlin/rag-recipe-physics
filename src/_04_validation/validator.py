"""Recipe validation based on physics and empirical data."""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"


class RecipeValidator:
    """Validate generated recipes against expected nutritional ranges."""
    
    def __init__(self):
        with open(DATA_DIR / "calories_reference.json") as f:
            self.calories_data = json.load(f)
        with open(DATA_DIR / "macro_ranges.json") as f:
            self.macro_data = json.load(f)
        with open(DATA_DIR / "categories.json") as f:
            self.categories = json.load(f)
        with open(DATA_DIR / "moisture_loss.json") as f:
            self.moisture_data = json.load(f)
    
    def map_taxonomy(self, taxonomy: str) -> str:
        """Map taxonomy string to validation category."""
        taxonomy_lower = taxonomy.lower()
        
        mapping = {
            "bread": "bread",
            "baguette": "bread",
            "ciabatta": "bread",
            "sourdough": "bread",
            "brioche": "bread",
            "focaccia": "bread",
            "cake": "butter_cake",
            "butter_cake": "butter_cake",
            "chocolate": "butter_cake",
            "cheesecake": "butter_cake",
            "pound": "butter_cake",
            "red velvet": "butter_cake",
            "carrot": "butter_cake",
            "foam_cake": "foam_cake",
            "sponge": "foam_cake",
            "angel": "foam_cake",
            "meringue": "foam_cake",
            "pastry": "pastry_puff",
            "puff": "pastry_puff",
            "croissant": "pastry_puff",
            "millefeuille": "pastry_puff",
            "danish": "pastry_puff",
            "shortcrust": "pastry_shortcrust",
            "pie": "pastry_shortcrust",
            "tart": "pastry_shortcrust",
            "quiche": "pastry_shortcrust",
            "cookie": "cookies",
            "biscuit": "cookies",
            "macaron": "cookies",
            "savory": "savory_pie",
            "pie": "savory_pie",
            "shepherd": "savory_pie",
            "cottage": "savory_pie",
            "empanada": "savory_pie",
            "meat pie": "savory_pie",
            "tart": "pastry_shortcrust",
            "seafood": "seafood_baked",
            "fish": "seafood_baked",
            "salmon": "seafood_baked",
            "pizza": "pizza",
            "calzone": "pizza"
        }
        
        for key, category in mapping.items():
            if key in taxonomy_lower:
                return category
        return "butter_cake"  # default
    
    def validate_calories(self, category: str, energy_kcal: float, taxonomy_hint: str = "") -> dict:
        """Validate calories against expected range for category."""
        kcal_data = self.calories_data["kcal_per_100g"]
        
        if category not in kcal_data:
            return {"status": "unknown", "message": f"Unknown category: {category}"}
        
        cat_data = kcal_data[category]
        
        # Try to find specific subcategory based on taxonomy hint
        subcat = None
        if taxonomy_hint:
            hint_lower = taxonomy_hint.lower()
            for key in cat_data.keys():
                if key.lower() in hint_lower or hint_lower in key.lower():
                    subcat = cat_data[key]
                    break
        
        # Fallback to first available or default
        if not subcat:
            subcat = cat_data.get("typical", cat_data.get(list(cat_data.keys())[0], {}))
        
        if isinstance(subcat, dict):
            min_kcal = subcat.get("min", 0)
            max_kcal = subcat.get("max", 9999)
        else:
            min_kcal, max_kcal = 0, 9999
        
        in_range = min_kcal <= energy_kcal <= max_kcal
        
        return {
            "status": "valid" if in_range else "warning",
            "energy_kcal": energy_kcal,
            "expected_min": min_kcal,
            "expected_max": max_kcal,
            "deviation_percent": ((energy_kcal - (min_kcal + max_kcal)/2) / ((max_kcal - min_kcal)/2)) * 100 if max_kcal > min_kcal else 0
        }
    
    def validate_macros(self, category: str, protein: float, carbs: float, fat: float) -> dict:
        """Validate macro breakdown for category."""
        macro_ranges = self.macro_data["macro_percentages"]
        
        if category not in macro_ranges:
            return {"status": "unknown"}
        
        ranges = macro_ranges[category]
        total = protein + carbs + fat
        
        if total == 0:
            return {"status": "error", "message": "No macros provided"}
        
        protein_pct = (protein / total) * 100
        carbs_pct = (carbs / total) * 100
        fat_pct = (fat / total) * 100
        
        results = {}
        for macro, range_dict in ranges.items():
            if macro == "protein":
                actual = protein_pct
            elif macro == "carbs":
                actual = carbs_pct
            else:
                actual = fat_pct
            
            in_range = range_dict["min"] <= actual <= range_dict["max"]
            results[macro] = {
                "actual": round(actual, 1),
                "expected_min": range_dict["min"],
                "expected_max": range_dict["max"],
                "status": "valid" if in_range else "warning"
            }
        
        return results
    
    def estimate_weight_loss(self, category: str) -> dict:
        """Estimate expected weight loss during baking."""
        weight_loss = self.moisture_data["weight_loss_percent"]
        
        if category in weight_loss:
            return weight_loss[category]
        
        # Default
        return {"min": 10, "max": 15, "note": "default"}
    
    def validate_recipe(self, taxonomy: str, energy_kcal: float, 
                       protein: float = 0, carbs: float = 0, fat: float = 0) -> dict:
        """Full recipe validation."""
        category = self.map_taxonomy(taxonomy)
        
        cal_result = self.validate_calories(category, energy_kcal, taxonomy)
        macro_result = self.validate_macros(category, protein, carbs, fat)
        weight_loss = self.estimate_weight_loss(category)
        
        return {
            "taxonomy": taxonomy,
            "category": category,
            "calories": cal_result,
            "macros": macro_result,
            "expected_weight_loss_percent": weight_loss,
            "overall_status": "valid" if cal_result.get("status") == "valid" else "warning"
        }


def validate_recipe(taxonomy: str, energy_kcal: float, 
                   protein: float = 0, carbs: float = 0, fat: float = 0) -> dict:
    """Convenience function for recipe validation."""
    validator = RecipeValidator()
    return validator.validate_recipe(taxonomy, energy_kcal, protein, carbs, fat)


if __name__ == "__main__":
    # Quick test
    v = RecipeValidator()
    
    test_cases = [
        ("bread", 266, 10, 50, 3),
        ("chocolate cake", 391, 5, 50, 25),
        ("croissant", 440, 8, 45, 30),
        ("shepherd's pie", 200, 15, 25, 10)
    ]
    
    for taxonomy, energy, p, c, f in test_cases:
        result = v.validate_recipe(taxonomy, energy, p, c, f)
        print(f"\n{taxonomy}:")
        print(f"  Calories: {result['calories']}")
        print(f"  Overall: {result['overall_status']}")