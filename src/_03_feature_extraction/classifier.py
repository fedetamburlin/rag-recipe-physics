"""Recipe classifier for oven-bakeable recipes.

Maps parsed recipe ingredients + title to 4 physical families.
Rule-based first, LLM fallback if ambiguous.

Categories
==========

dough_structured
  Flour-dominant, solid structure. Yeast or no yeast.
  Examples: bread, pizza, croissant, pie crust, shortcrust, cookie, lasagna
  Validation: hydration < 100% baker's, fat/flour 0.3-1.0

batter_baked
  Liquid/semi-liquid batter baked in pan.
  Examples: cake, brownie, muffin, casserole, crumble, soufflé
  Validation: enough liquid for internal cooking, pan depth

solid_roast
  Solid piece, surface Maillard cooking.
  Examples: roast chicken, baked salmon, roasted vegetables, steak
  Validation: internal temp target (meat 65°C, fish 55°C)

custard_set
  Heat-coagulated, often in bain-marie.
  Examples: cheesecake, crème caramel, pudding al forno, quiche
  Validation: egg+dairy > 40%, coagulation ~85°C, no boiling

Usage
=====
    from _03_feature_extraction.classifier import classify_recipe
    result = classify_recipe(ingredients, title)
    # result = {"category": "dough_structured", "method": "rule", "confidence": 0.9}
"""

import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "dough_structured": 0,
    "batter_baked": 1,
    "solid_roast": 2,
    "custard_set": 3,
}

# Keyword lists for title-based classification
DOUGH_KEYWORDS = [
    "bread", "pizza", "croissant", "puff", "pie crust", "shortcrust",
    "cookie", "biscuit", "pastry", "sfoglia", "frolla", "lasagn", "lasagna",
    "cannellon", "dough", "focaccia", "baguette", "ciabatta", "sourdough"
]

BATTER_KEYWORDS = [
    "cake", "brownie", "muffin", "cupcake", "casserole", "crumble",
    "torta", "gateau", "souffle", "soufflé", "clafoutis", "flan"
]

SOLID_KEYWORDS = [
    "chicken", "beef", "pork", "lamb", "turkey", "duck", "meat",
    "salmon", "fish", "tuna", "cod", "trout", "sea bass", "pesce",
    "potato", "carrot", "pumpkin", "zucchini", "eggplant", "pepper",
    "vegetable", "verdura", "roast", "arrosto"
]


def classify_recipe(
    ingredients: List[Tuple[str, float]],
    title: str = "",
    use_llm: bool = True,
) -> Dict:
    """Classify oven recipe into 4 physical families.

    Rule-based classification with deterministic priority:
    1. custard_set (egg + dairy, little flour)
    2. solid_roast (no flour, solid protein/veg)
    3. dough_structured vs batter_baked (flour dominant, yeast/keywords/fat ratio)
    4. LLM fallback if ambiguous

    Args:
        ingredients: List of (name, percentage_decimal) tuples
        title: Recipe title for keyword boost
        use_llm: If True, call LLM when rules are ambiguous

    Returns:
        Dict with keys: category, method (rule/llm/forced), confidence
    """
    ing_dict = {name.lower(): pct for name, pct in ingredients}
    title_lower = title.lower()

    # Aggregate base ingredients
    flour = sum(v for k, v in ing_dict.items() if "flour" in k or "farina" in k or "semola" in k)
    egg = sum(v for k, v in ing_dict.items() if "egg" in k or "uova" in k)
    dairy = sum(v for k, v in ing_dict.items() if any(x in k for x in [
        "milk", "cream", "cheese", "latte", "crema", "formaggio",
        "ricotta", "mascarpone", "parmesan", "mozzarella"
    ]))
    fat = sum(v for k, v in ing_dict.items() if any(x in k for x in [
        "butter", "oil", "shortening", "lard", "olio", "burro", "margarine"
    ]))
    yeast = any(k in ing_dict for k in ["yeast", "lievito", "brewer's yeast"])
    baking_powder = any(k in ing_dict for k in ["baking powder", "baking soda", "bicarbonate", "bicarbonato"])

    # Solid pieces (meat, fish, vegetables)
    solid = sum(v for k, v in ing_dict.items() if any(x in k for x in SOLID_KEYWORDS))

    # Title-only strong indicators (independent of ingredient ratios)
    if any(k in title_lower for k in ["lasagna", "lasagne", "cannelloni", "pasta al forno"]):
        return {"category": "dough_structured", "method": "rule", "confidence": 0.90}

    # --- 1. CUSTARD: egg + dairy dominant, flour minor ---
    if egg > 0.15 and dairy > 0.15 and flour < 0.20:
        return {"category": "custard_set", "method": "rule", "confidence": 0.92}

    # --- 2. SOLID ROAST: solid piece dominant ---
    # Exclude obvious pies/pastry/custard by title
    excluded_for_solid = any(k in title_lower for k in [
        "pie", "tart", "quiche", "casserole", "cake", "cookie", "bread", "pizza", "lasagn"
    ])

    if not excluded_for_solid:
        # Title strongly indicates roasting
        if any(k in title_lower for k in ["roast", "grilled", "arrosto"]):
            if flour < 0.30:
                return {"category": "solid_roast", "method": "rule", "confidence": 0.88}
        # Ingredient-based
        if flour < 0.05 and solid > 0.30:
            return {"category": "solid_roast", "method": "rule", "confidence": 0.85}

    # --- 3 & 4. DOUGH vs BATTER: flour dominant ---
    if flour > 0.10:
        is_dough_title = any(k in title_lower for k in DOUGH_KEYWORDS)
        is_batter_title = any(k in title_lower for k in BATTER_KEYWORDS)

        # Batter keyword wins (cake, brownie, muffin, etc.)
        if is_batter_title:
            return {"category": "batter_baked", "method": "rule", "confidence": 0.88}

        # Dough keyword wins (bread, pizza, cookie, lasagna, etc.)
        if is_dough_title:
            return {"category": "dough_structured", "method": "rule", "confidence": 0.88}

        # Chemical leavening → batter
        if baking_powder:
            return {"category": "batter_baked", "method": "rule", "confidence": 0.85}

        # Yeast → dough
        if yeast:
            return {"category": "dough_structured", "method": "rule", "confidence": 0.85}

        # High fat ratio → pastry/dough (shortcrust without explicit keyword)
        if flour > 0 and fat / flour > 0.8:
            return {"category": "dough_structured", "method": "rule", "confidence": 0.75}

        # Hydration heuristic for edge cases
        water = sum(v for k, v in ing_dict.items() if any(x in k for x in ["water", "acqua", "milk", "latte"]))
        if flour > 0 and water / flour < 0.6:
            return {"category": "dough_structured", "method": "rule", "confidence": 0.60}
        else:
            return {"category": "batter_baked", "method": "rule", "confidence": 0.60}

    # --- AMBIGUOUS: call LLM if enabled ---
    if use_llm:
        return _classify_with_llm(title, ingredients)

    # Forced fallback (should rarely happen with LLM enabled)
    logger.warning("Ambiguous classification without LLM, forcing batter_baked")
    return {"category": "batter_baked", "method": "forced_fallback", "confidence": 0.30}


def _classify_with_llm(title: str, ingredients: List[Tuple[str, float]]) -> Dict:
    """Use LLM when rules are ambiguous."""
    try:
        import ollama

        ing_str = ", ".join([f"{n} {p*100:.0f}%" for n, p in ingredients[:12]])
        prompt = (
            "You are a food scientist. Classify this oven recipe into exactly one category:\n\n"
            "dough_structured: flour-based solid structure (bread, pizza, croissant, pie, cookie, lasagna, pasta)\n"
            "batter_baked: liquid/semi-liquid batter baked in pan (cake, brownie, muffin, casserole, souffle)\n"
            "solid_roast: solid piece cooked by surface heat (roast chicken, baked fish, roasted vegetables)\n"
            "custard_set: heat-coagulated egg+dairy mixture (cheesecake, creme caramel, quiche)\n\n"
            f"Title: {title}\n"
            f"Ingredients: {ing_str}\n\n"
            "Respond with ONLY the category name, nothing else."
        )

        response = ollama.chat(
            model="qwen2.5:3b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0, "num_predict": 20}
        )
        cat = response["message"]["content"].strip().lower().replace("é", "e").replace("è", "e")

        # Normalize partial matches
        valid = {"dough_structured", "batter_baked", "solid_roast", "custard_set"}
        if cat not in valid:
            for v in valid:
                if v in cat:
                    cat = v
                    break
            else:
                cat = "batter_baked"

        return {"category": cat, "method": "llm", "confidence": 0.75}

    except Exception as e:
        logger.warning(f"LLM classification failed: {e}")
        return {"category": "batter_baked", "method": "llm_error", "confidence": 0.30}


def get_category_names() -> List[str]:
    """Return ordered list of category names."""
    return ["dough_structured", "batter_baked", "solid_roast", "custard_set"]
