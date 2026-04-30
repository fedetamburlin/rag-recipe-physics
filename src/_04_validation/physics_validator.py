"""Physics-based validation per recipe category.

Validates generated recipes against empirically-derived ranges
for hydration, composition, and cooking physics.

Sources:
- Baker's percentage (Wikipedia): hydration ranges for dough/batter
- FDA Safe Minimum Internal Temperatures
- General baking science references
"""

from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

# Validation ranges per category.
# NOTE: salt_pct and yeast_pct are TRUE percentages of total ingredients
# (0.01 = 1%), NOT baker's percentages. The LLM generates proportions
# as percentages of the whole recipe.
VALIDATION_RULES = {
    "dough_structured": {
        "hydration_bakers": {"min": 30, "max": 85, "note": "Stiff bagels 50% to ciabatta 80%"},
        "protein_g": {"min": 4, "max": 15, "note": "Bread needs gluten, cookies lower"},
        "fat_g": {"min": 0, "max": 35, "note": "Lean bread <5%, brioche/croissant up to 35%"},
        "sugar_g": {"min": 0, "max": 25, "note": "Bread <10%, sweet pastry higher"},
        "salt_pct": {"min": 1.0, "max": 2.5, "note": "Standard 1.5-2.2%"},
        "yeast_pct": {"min": 0.5, "max": 3.0, "note": "Fresh yeast, commercial up to 2%"},
        "internal_temp_C": {"min": 88, "max": 99, "note": "Bread done at 88-96°C internal"},
    },
    "batter_baked": {
        "hydration_bakers": {"min": 60, "max": 250, "note": "Cakes 60-100%, pancakes ~190%"},
        "protein_g": {"min": 3, "max": 10, "note": "Cakes lower protein than bread"},
        "fat_g": {"min": 5, "max": 30, "note": "Butter cakes 15-25%"},
        "sugar_g": {"min": 5, "max": 40, "note": "Sponge cakes higher, savory lower"},
        "salt_pct": {"min": 0.5, "max": 2.0, "note": "Generally <2%"},
        "internal_temp_C": {"min": 88, "max": 99, "note": "Cake done when springy, ~96°C"},
    },
    "solid_roast": {
        "hydration_bakers": {"min": 0, "max": 30, "note": "No flour, water from meat/veg itself"},
        "protein_g": {"min": 10, "max": 35, "note": "Meat/fish dominant"},
        "fat_g": {"min": 2, "max": 30, "note": "Lean fish 2-8%, fatty meat 15-25%"},
        "sugar_g": {"min": 0, "max": 10, "note": "Glaze/marinade only"},
        "salt_pct": {"min": 0.5, "max": 2.0, "note": "Seasoning"},
        "internal_temp_C": {"min": 55, "max": 74, "note": "Fish 63°C, beef 63°C, poultry 74°C"},
    },
    "custard_set": {
        "hydration_bakers": {"min": 20, "max": 100, "note": "High liquid from dairy"},
        "protein_g": {"min": 5, "max": 15, "note": "Eggs + cheese"},
        "fat_g": {"min": 5, "max": 25, "note": "Cream cheese, heavy cream"},
        "sugar_g": {"min": 5, "max": 30, "note": "Dessert custards higher"},
        "salt_pct": {"min": 0.2, "max": 1.5, "note": "Quiche slightly more"},
        "internal_temp_C": {"min": 71, "max": 85, "note": "Coagulation starts 65°C, max 85°C to avoid curdling"},
    },
}

# FDA Safe Minimum Internal Temperatures (°C)
FDA_INTERNAL_TEMPS = {
    "beef": 63,      # 145°F
    "pork": 63,      # 145°F
    "lamb": 63,      # 145°F
    "ground_meat": 71,  # 160°F
    "poultry": 74,   # 165°F
    "fish": 63,      # 145°F
    "eggs": 71,      # 160°F
    "leftovers": 74, # 165°F
}


def _extract_ingredient_pct(ingredients: List[Tuple[str, float]]) -> Dict[str, float]:
    """Aggregate percentages for key ingredient groups."""
    ing_dict: Dict[str, float] = {}
    for name, pct in ingredients:
        key = name.lower()
        ing_dict[key] = ing_dict.get(key, 0.0) + pct
    return ing_dict


def validate_recipe(
    ingredients: List[Tuple[str, float]],
    nutrition: dict,
    category: str,
    title: str = "",
) -> Dict:
    """Validate recipe against category-specific physics ranges.

    Args:
        ingredients: List of (name, percentage_decimal)
        nutrition: Dict with USDA nutrients per 100g
        category: One of dough_structured, batter_baked, solid_roast, custard_set
        title: Recipe title (unused, reserved for future heuristics)

    Returns:
        Dict with validation results
    """
    if category not in VALIDATION_RULES:
        return {"status": "unknown_category", "category": category}

    rules = VALIDATION_RULES[category]
    checks = []
    warnings = []
    errors = []

    ing = _extract_ingredient_pct(ingredients)

    # Aggregate groups
    flour = sum(v for k, v in ing.items() if "flour" in k or "farina" in k)
    water = sum(v for k, v in ing.items() if any(x in k for x in ["water", "acqua", "milk", "latte", "egg", "butter"]))
    salt = sum(v for k, v in ing.items() if "salt" in k or "sale" in k)
    yeast = sum(v for k, v in ing.items() if "yeast" in k or "lievito" in k)

    sugar = nutrition.get("SUGAR", {}).get("amount", 0) or 0
    protein = nutrition.get("PROTEIN", {}).get("amount", 0) or 0
    fat = nutrition.get("FAT", {}).get("amount", 0) or 0

    # 1. Hydration (baker's %)
    hydration = (water / flour * 100) if flour > 0 else 0.0
    _check_range(hydration, rules.get("hydration_bakers"), "hydration", "%", checks, warnings, errors)

    # 2. Protein
    _check_range(protein, rules.get("protein_g"), "protein", "g", checks, warnings, errors)

    # 3. Fat
    _check_range(fat, rules.get("fat_g"), "fat", "g", checks, warnings, errors)

    # 4. Sugar
    _check_range(sugar, rules.get("sugar_g"), "sugar", "g", checks, warnings, errors)

    # 5. Salt (true % of total ingredients)
    _check_range(salt * 100, rules.get("salt_pct"), "salt", "%", checks, warnings, errors)

    # 6. Yeast (true %, dough only)
    if yeast > 0:
        _check_range(yeast * 100, rules.get("yeast_pct"), "yeast", "%", checks, warnings, errors)

    # 7. Internal temperature guidance (informational)
    temp_rule = rules.get("internal_temp_C")
    if temp_rule:
        checks.append(f"target internal temp: {temp_rule['min']}-{temp_rule['max']}°C ({temp_rule['note']})")

    # Determine overall status
    if errors:
        status = "invalid"
    elif warnings:
        status = "warning"
    else:
        status = "valid"

    return {
        "status": status,
        "category": category,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "metrics": {
            "hydration_bakers": round(hydration, 1),
            "protein_g": round(protein, 1),
            "fat_g": round(fat, 1),
            "sugar_g": round(sugar, 1),
            "salt_pct": round(salt * 100, 2),
            "yeast_pct": round(yeast * 100, 2),
        }
    }


def _check_range(
    value: float,
    rule: dict,
    name: str,
    unit: str,
    checks: List[str],
    warnings: List[str],
    errors: List[str],
) -> None:
    """Check a numeric value against a min/max rule."""
    if rule is None:
        return

    msg = rule["note"]
    if value < rule["min"]:
        errors.append(f"{name} {value:.1f}{unit} < {rule['min']}{unit} ({msg})")
    elif value > rule["max"]:
        errors.append(f"{name} {value:.1f}{unit} > {rule['max']}{unit} ({msg})")
    else:
        checks.append(f"{name} {value:.1f}{unit} OK")


def get_fda_temp(food_type: str) -> int:
    """Get FDA recommended internal temperature in Celsius."""
    return FDA_INTERNAL_TEMPS.get(food_type, 74)  # Default to poultry-safe
