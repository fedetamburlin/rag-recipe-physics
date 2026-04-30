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

# Validation ranges per category
VALIDATION_RULES = {
    "dough_structured": {
        "hydration_bakers": {"min": 30, "max": 85, "note": "Stiff bagels 50% to ciabatta 80%"},
        "protein_g": {"min": 4, "max": 15, "note": "Bread needs gluten, cookies lower"},
        "fat_g": {"min": 0, "max": 35, "note": "Lean bread <5%, brioche/croissant up to 35%"},
        "sugar_g": {"min": 0, "max": 25, "note": "Bread <10%, sweet pastry higher"},
        "salt_bakers": {"min": 1.0, "max": 2.5, "note": "Standard 1.5-2.2%"},
        "yeast_bakers": {"min": 0.5, "max": 3.0, "note": "Fresh yeast, commercial up to 2%"},
        "internal_temp_C": {"min": 88, "max": 99, "note": "Bread done at 88-96°C internal"},
    },
    "batter_baked": {
        "hydration_bakers": {"min": 60, "max": 250, "note": "Cakes 60-100%, pancakes ~190%"},
        "protein_g": {"min": 3, "max": 10, "note": "Cakes lower protein than bread"},
        "fat_g": {"min": 5, "max": 30, "note": "Butter cakes 15-25%"},
        "sugar_g": {"min": 5, "max": 40, "note": "Sponge cakes higher, savory lower"},
        "salt_bakers": {"min": 0.5, "max": 2.0, "note": "Generally <2%"},
        "internal_temp_C": {"min": 88, "max": 99, "note": "Cake done when springy, ~96°C"},
    },
    "solid_roast": {
        "hydration_bakers": {"min": 0, "max": 30, "note": "No flour, water from meat/veg itself"},
        "protein_g": {"min": 10, "max": 35, "note": "Meat/fish dominant"},
        "fat_g": {"min": 2, "max": 30, "note": "Lean fish 2-8%, fatty meat 15-25%"},
        "sugar_g": {"min": 0, "max": 10, "note": "Glaze/marinade only"},
        "salt_bakers": {"min": 0.5, "max": 2.0, "note": "Seasoning"},
        "internal_temp_C": {"min": 55, "max": 74, "note": "Fish 63°C, beef 63°C, poultry 74°C"},
    },
    "custard_set": {
        "hydration_bakers": {"min": 20, "max": 100, "note": "High liquid from dairy"},
        "protein_g": {"min": 5, "max": 15, "note": "Eggs + cheese"},
        "fat_g": {"min": 5, "max": 25, "note": "Cream cheese, heavy cream"},
        "sugar_g": {"min": 5, "max": 30, "note": "Dessert custards higher"},
        "salt_bakers": {"min": 0.2, "max": 1.5, "note": "Quiche slightly more"},
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
        title: Recipe title

    Returns:
        Dict with validation results
    """
    if category not in VALIDATION_RULES:
        return {"status": "unknown_category", "category": category}

    rules = VALIDATION_RULES[category]
    checks = []
    warnings = []
    errors = []

    # Extract features from ingredients
    ing_dict = {name.lower(): pct for name, pct in ingredients}
    flour = sum(v for k, v in ing_dict.items() if "flour" in k or "farina" in k)
    water = sum(v for k, v in ing_dict.items() if any(x in k for x in ["water", "acqua", "milk", "latte"]))
    salt = sum(v for k, v in ing_dict.items() if "salt" in k or "sale" in k)
    yeast = sum(v for k, v in ing_dict.items() if "yeast" in k or "lievito" in k)
    sugar = nutrition.get("SUGAR", {}).get("amount", 0) or 0

    # 1. Hydration (baker's %)
    if flour > 0:
        hydration = (water / flour) * 100
    else:
        hydration = 0

    h_rule = rules.get("hydration_bakers")
    if h_rule:
        if hydration < h_rule["min"]:
            errors.append(f"hydration {hydration:.1f}% < {h_rule['min']}% ({h_rule['note']})")
        elif hydration > h_rule["max"]:
            errors.append(f"hydration {hydration:.1f}% > {h_rule['max']}% ({h_rule['note']})")
        else:
            checks.append(f"hydration {hydration:.1f}% OK")

    # 2. Protein
    protein = nutrition.get("PROTEIN", {}).get("amount", 0) or 0
    p_rule = rules.get("protein_g")
    if p_rule:
        if protein < p_rule["min"]:
            warnings.append(f"protein {protein:.1f}g < {p_rule['min']}g ({p_rule['note']})")
        elif protein > p_rule["max"]:
            warnings.append(f"protein {protein:.1f}g > {p_rule['max']}g ({p_rule['note']})")
        else:
            checks.append(f"protein {protein:.1f}g OK")

    # 3. Fat
    fat = nutrition.get("FAT", {}).get("amount", 0) or 0
    f_rule = rules.get("fat_g")
    if f_rule:
        if fat < f_rule["min"]:
            warnings.append(f"fat {fat:.1f}g < {f_rule['min']}g ({f_rule['note']})")
        elif fat > f_rule["max"]:
            warnings.append(f"fat {fat:.1f}g > {f_rule['max']}g ({f_rule['note']})")
        else:
            checks.append(f"fat {fat:.1f}g OK")

    # 4. Sugar
    s_rule = rules.get("sugar_g")
    if s_rule:
        if sugar < s_rule["min"]:
            warnings.append(f"sugar {sugar:.1f}g < {s_rule['min']}g ({s_rule['note']})")
        elif sugar > s_rule["max"]:
            warnings.append(f"sugar {sugar:.1f}g > {s_rule['max']}g ({s_rule['note']})")
        else:
            checks.append(f"sugar {sugar:.1f}g OK")

    # Pre-calculate baker's percentages
    if flour > 0:
        salt_bakers = (salt / flour) * 100
        yeast_bakers = (yeast / flour) * 100
    else:
        salt_bakers = 0
        yeast_bakers = 0

    # 5. Salt (baker's %)
    salt_rule = rules.get("salt_bakers")
    if salt_rule:
        if salt_bakers < salt_rule["min"]:
            warnings.append(f"salt {salt_bakers:.1f}% < {salt_rule['min']}% ({salt_rule['note']})")
        elif salt_bakers > salt_rule["max"]:
            errors.append(f"salt {salt_bakers:.1f}% > {salt_rule['max']}% ({salt_rule['note']})")
        else:
            checks.append(f"salt {salt_bakers:.1f}% OK")

    # 6. Yeast (baker's %, dough only)
    yeast_rule = rules.get("yeast_bakers")
    if yeast_rule and flour > 0 and yeast_bakers > 0:
        if yeast_bakers < yeast_rule["min"]:
            warnings.append(f"yeast {yeast_bakers:.1f}% < {yeast_rule['min']}% ({yeast_rule['note']})")
        elif yeast_bakers > yeast_rule["max"]:
            warnings.append(f"yeast {yeast_bakers:.1f}% > {yeast_rule['max']}% ({yeast_rule['note']})")
        else:
            checks.append(f"yeast {yeast_bakers:.1f}% OK")

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
            "salt_bakers": round(salt_bakers, 2),
            "yeast_bakers": round(yeast_bakers, 2) if flour > 0 else 0,
        }
    }


def get_fda_temp(food_type: str) -> int:
    """Get FDA recommended internal temperature in Celsius."""
    return FDA_INTERNAL_TEMPS.get(food_type, 74)  # Default to poultry-safe
