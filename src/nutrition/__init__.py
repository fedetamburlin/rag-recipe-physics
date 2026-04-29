"""Nutrition module for USDA food data."""

from src.nutrition.db import init_db, get_connection, DB_PATH
from src.nutrition.ingredient_lookup import IngredientMatcher, get_food_nutrients
from src.nutrition.nutrition_calculator import NutritionCalculator, calculate_recipe_nutrients

__all__ = [
    'init_db',
    'get_connection', 
    'DB_PATH',
    'IngredientMatcher',
    'get_food_nutrients',
    'NutritionCalculator',
    'calculate_recipe_nutrients',
]