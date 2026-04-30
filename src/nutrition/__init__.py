"""Nutrition module for USDA food data."""

try:
    from src.nutrition.db import get_connection
    from src.nutrition.ingredient_lookup import IngredientMatcher, get_food_nutrients
    from src.nutrition.nutrition_calculator import NutritionCalculator, calculate_recipe_nutrients
except ModuleNotFoundError:
    from nutrition.db import get_connection
    from nutrition.ingredient_lookup import IngredientMatcher, get_food_nutrients
    from nutrition.nutrition_calculator import NutritionCalculator, calculate_recipe_nutrients

__all__ = [
    'get_connection',
    'IngredientMatcher',
    'get_food_nutrients',
    'NutritionCalculator',
    'calculate_recipe_nutrients',
]