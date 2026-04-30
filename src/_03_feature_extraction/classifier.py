"""Recipe classifier for oven-bakeable recipes.

Maps parsed recipe ingredients + title to 4 physical families.
Used for validation constraints and as features for oven prediction NN.

Categories
==========

dough_structured
  Flour-dominant, solid structure. Yeast or no yeast.
  Examples: bread, pizza, croissant, pie crust, shortcrust, cookie
  Validation: hydration < 100% baker's, fat/flour 0.3-1.0

batter_baked
  Liquid/semi-liquid batter baked in pan.
  Examples: cake, brownie, lasagne, casserole, crumble
  Validation: enough liquid for internal cooking, pan depth

solid_roast
  Solid piece, surface Maillard cooking.
  Examples: roast chicken, baked salmon, roasted vegetables, steak
  Validation: internal temp target (meat 65°C, fish 55°C)

custard_set
  Heat-coagulated, often in bain-marie.
  Examples: cheesecake, crème caramel, pudding al forno, quiche
  Validation: egg+dairy > 40%, coagulation ~85°C, no boiling

No-bake recipes are EXCLUDED upstream by _is_oven_recipe in retriever.py.

Usage
=====
    from _03_feature_extraction.classifier import classify_recipe
    result = classify_recipe(ingredients, title)
    # result = {"category": "dough_structured", "is_oven_recipe": True}
"""

from typing import List, Tuple, Dict


def classify_recipe(
    ingredients: List[Tuple[str, float]],
    title: str = "",
) -> Dict[str, str]:
    """Classify oven recipe into 4 physical families.
    
    Args:
        ingredients: List of (name, percentage_decimal) tuples
        title: Recipe title (optional, for keyword boost)
    
    Returns:
        Dict with keys: category, is_oven_recipe (always True here)
    """
    # TODO: implement classification logic
    # See module docstring for category definitions and examples
    raise NotImplementedError("classify_recipe not yet implemented")
