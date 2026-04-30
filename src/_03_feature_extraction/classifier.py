"""Recipe classifier for oven-bakeable recipes.

Maps parsed recipe ingredients + title to 4 physical families.
Rule-based first (ingredients prioritized over title), LLM fallback if ambiguous.

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

# Keyword lists for title-based tie-breaking
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

    Priority: ingredients first, title keywords as tie-breaker, LLM fallback.
    This makes the classifier robust against misleading titles from LLM output.

    Args:
        ingredients: List of (name, percentage_decimal) tuples
        title: Recipe title for keyword tie-breaking
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

    # --- 1. CUSTARD: egg + dairy dominant, flour minor (ingredients) ---
    if egg > 0.15 and dairy > 0.15 and flour < 0.20:
        return {"category": "custard_set", "method": "rule", "confidence": 0.92}

    # --- 2. SOLID ROAST: title says roast/meat/fish (override LLM errors) ---
    excluded_for_solid = any(k in title_lower for k in [
        "pie", "tart", "quiche", "casserole", "cake", "cookie", "bread", "pizza", "lasagn",
        "wellington", "empanada", "calzone", "pastry"
    ])
    if not excluded_for_solid:
        if any(k in title_lower for k in ["roast", "grilled", "arrosto", "beef", "steak"]):
            if flour < 0.35:
                return {"category": "solid_roast", "method": "rule_title", "confidence": 0.85}
        if any(k in title_lower for k in ["salmon", "cod", "trout", "fish", "pesce"]):
            if flour < 0.35:
                return {"category": "solid_roast", "method": "rule_title", "confidence": 0.85}

    # --- 3. SOLID ROAST: no flour, solid piece dominant (ingredients) ---
    if flour < 0.05 and solid > 0.30:
        return {"category": "solid_roast", "method": "rule", "confidence": 0.88}

    # --- 4. DOUGH: yeast present (ingredients) ---
    if yeast:
        return {"category": "dough_structured", "method": "rule", "confidence": 0.90}

    # --- 5. BATTER: chemical leavening (ingredients) ---
    if baking_powder:
        return {"category": "batter_baked", "method": "rule", "confidence": 0.88}

    # --- 6. FLOUR-DOMINANT (>10%): distinguish dough vs batter ---
    if flour > 0.10:
        is_dough_title = any(k in title_lower for k in DOUGH_KEYWORDS)
        is_batter_title = any(k in title_lower for k in BATTER_KEYWORDS)

        # Batter keyword wins
        if is_batter_title and not is_dough_title:
            return {"category": "batter_baked", "method": "rule_title", "confidence": 0.85}

        # Dough keyword wins
        if is_dough_title and not is_batter_title:
            return {"category": "dough_structured", "method": "rule_title", "confidence": 0.85}

        # High fat ratio → pastry/dough
        if flour > 0 and fat / flour > 0.8:
            return {"category": "dough_structured", "method": "rule", "confidence": 0.80}

        # Hydration heuristic for edge cases
        water = sum(v for k, v in ing_dict.items() if any(x in k for x in ["water", "acqua", "milk", "latte"]))
        if flour > 0 and water / flour < 0.5:
            return {"category": "dough_structured", "method": "rule", "confidence": 0.65}
        if flour > 0 and water / flour > 1.2:
            return {"category": "batter_baked", "method": "rule", "confidence": 0.65}

        # Both or neither title keyword → LLM fallback
        if use_llm:
            return _classify_with_llm(title, ingredients)
        return {"category": "batter_baked", "method": "forced_fallback", "confidence": 0.40}

    # --- 7. LOW FLOUR (<10%): solid or ambiguous ---
    if solid > 0.20:
        return {"category": "solid_roast", "method": "rule", "confidence": 0.65}

    # --- AMBIGUOUS: call LLM if enabled ---
    if use_llm:
        return _classify_with_llm(title, ingredients)

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
