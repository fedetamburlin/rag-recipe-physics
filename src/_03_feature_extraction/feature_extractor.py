"""Feature extraction from recipe ingredients and USDA nutrition data.

Extracts 10 core physicochemical features from LLM-generated recipes
for downstream oven parameter prediction (temperature, time, etc.)

No heuristics used — only USDA nutrient data + basic mixing rules.
"""

from typing import List, Tuple, Dict
from pathlib import Path
import json

from _03_feature_extraction.classifier import CATEGORY_MAP

# Simplified thermal properties for mixing rule (per 100g basis)
THERMAL_PROPS = {
    "water":   {"cp": 4186, "k": 0.60, "rho": 1000},
    "fat":     {"cp": 2000, "k": 0.15, "rho": 900},
    "protein": {"cp": 2000, "k": 0.20, "rho": 1300},
    "carbs":   {"cp": 1700, "k": 0.10, "rho": 550},
    "fiber":   {"cp": 1800, "k": 0.10, "rho": 500},
}

# Taxonomy encoding map (matches retriever _compute_taxonomy output)
TAXONOMY_MAP = {
    "leavened": 0,
    "whipped": 1,
    "doughs": 2,
    "preserves": 3,
    "creams": 4,
    "meats": 5,
    "seafood": 6,
    "other": 7,
}

# Target variables for future oven prediction model
OVEN_TARGETS = ["temperature_C", "time_min", "preheat_bool", "mode_encoded", "humidity_pct"]


class RecipeFeatureExtractor:
    """Extract structured physicochemical features from parsed recipe + nutrition."""

    def __init__(self):
        self.feature_names = [
            "water_g",
            "protein_g",
            "fat_g",
            "carbs_g",
            "sodium_mg",
            "energy_kcal",
            "hydration_bakers",
            "density_kg_m3",
            "thermal_diffusivity",
            "taxonomy_encoded",
            "category_encoded",
        ]

    def _analyze_base_ingredients(
        self, ingredients: List[Tuple[str, float]]
    ) -> Dict[str, float]:
        """Extract flour and water percentages for baker's calculations."""
        flour = 0.0
        water = 0.0

        flour_keywords = ["flour", "farina", "semola", "manitoba"]
        water_keywords = ["water", "acqua", "milk", "latte", "yogurt", "buttermilk", "cream", "egg", "butter"]

        for name, pct in ingredients:
            name_lower = name.lower()
            if any(k in name_lower for k in flour_keywords):
                flour += pct
            if any(k in name_lower for k in water_keywords):
                water += pct

        return {"flour_pct": flour, "water_pct": water}

    def _compute_physical_properties(
        self, nutrition: dict
    ) -> Tuple[float, float]:
        """Estimate density and thermal diffusivity from macronutrient composition.

        Uses simplified mixing rules:
            density = sum(wi * rho_i)
            alpha = k / (rho * cp)   [thermal diffusivity in mm2/s]
        """
        w = nutrition.get("WATER", {}).get("amount", 0) or 0
        p = nutrition.get("PROTEIN", {}).get("amount", 0) or 0
        f = nutrition.get("FAT", {}).get("amount", 0) or 0
        c = nutrition.get("CARB", {}).get("amount", 0) or 0

        total = w + p + f + c
        if total == 0:
            return 800.0, 0.1

        w_norm = w / total
        p_norm = p / total
        f_norm = f / total
        c_norm = c / total

        density = (
            w_norm * THERMAL_PROPS["water"]["rho"]
            + p_norm * THERMAL_PROPS["protein"]["rho"]
            + f_norm * THERMAL_PROPS["fat"]["rho"]
            + c_norm * THERMAL_PROPS["carbs"]["rho"]
        )

        cp = (
            w_norm * THERMAL_PROPS["water"]["cp"]
            + p_norm * THERMAL_PROPS["protein"]["cp"]
            + f_norm * THERMAL_PROPS["fat"]["cp"]
            + c_norm * THERMAL_PROPS["carbs"]["cp"]
        )

        k = (
            w_norm * THERMAL_PROPS["water"]["k"]
            + p_norm * THERMAL_PROPS["protein"]["k"]
            + f_norm * THERMAL_PROPS["fat"]["k"]
            + c_norm * THERMAL_PROPS["carbs"]["k"]
        )

        # Convert to mm2/s for readability
        alpha = (k / (density * cp)) * 1e6

        return density, alpha

    def extract(
        self,
        ingredients: List[Tuple[str, float]],
        nutrition: dict,
        taxonomy: str,
        category: str = "batter_baked",
    ) -> dict:
        """Extract 11 physicochemical features from recipe ingredients and nutrition.

        Args:
            ingredients: List of (name, percentage_decimal) tuples.
                         Example: [("flour", 0.30), ("water", 0.20), ...]
            nutrition: Dict with USDA nutrients per 100g.
                       Example: {"WATER": {"amount": 35.0, "unit": "g"}, ...}
            taxonomy: Taxonomy string from retriever.
                      One of: leavened, whipped, doughs, preserves, creams, meats, seafood, other
            category: Physical family from classifier.

        Returns:
            Dict with 11 feature values keyed by feature name.
        """
        features = {}

        # 1-6: Direct USDA nutrients (per 100g)
        features["water_g"] = nutrition.get("WATER", {}).get("amount", 0) or 0
        features["protein_g"] = nutrition.get("PROTEIN", {}).get("amount", 0) or 0
        features["fat_g"] = nutrition.get("FAT", {}).get("amount", 0) or 0
        features["carbs_g"] = nutrition.get("CARB", {}).get("amount", 0) or 0
        features["sodium_mg"] = nutrition.get("NA", {}).get("amount", 0) or 0
        features["energy_kcal"] = nutrition.get("ENERGY", {}).get("amount", 0) or 0

        # 7: Baker's hydration (water / flour * 100)
        base = self._analyze_base_ingredients(ingredients)
        if base["flour_pct"] > 0:
            features["hydration_bakers"] = round((base["water_pct"] / base["flour_pct"]) * 100, 1)
        else:
            features["hydration_bakers"] = 0.0

        # 8-9: Physical properties from mixing rule
        density, alpha = self._compute_physical_properties(nutrition)
        features["density_kg_m3"] = round(density, 1)
        features["thermal_diffusivity"] = round(alpha, 4)

        # 10-11: Encodings
        features["taxonomy_encoded"] = TAXONOMY_MAP.get(taxonomy, TAXONOMY_MAP["other"])
        features["category_encoded"] = CATEGORY_MAP.get(category, CATEGORY_MAP["batter_baked"])

        return features

    def get_feature_names(self) -> List[str]:
        """Return list of 11 feature names."""
        return self.feature_names.copy()

    def get_target_names(self) -> List[str]:
        """Return list of oven prediction target variables.

        Currently active: temperature_C, time_min
        Reserved for future: preheat_bool, mode_encoded, humidity_pct
        """
        return OVEN_TARGETS.copy()


def extract_features(
    ingredients: List[Tuple[str, float]],
    nutrition: dict,
    taxonomy: str,
    category: str = "batter_baked",
) -> dict:
    """Convenience function."""
    extractor = RecipeFeatureExtractor()
    return extractor.extract(ingredients, nutrition, taxonomy, category)


if __name__ == "__main__":
    # Quick test with fake data
    test_ingredients = [
        ("flour", 0.35),
        ("water", 0.25),
        ("butter", 0.15),
        ("sugar", 0.15),
        ("egg", 0.10),
    ]
    test_nutrition = {
        "WATER": {"amount": 30.0, "unit": "g"},
        "PROTEIN": {"amount": 8.0, "unit": "g"},
        "FAT": {"amount": 15.0, "unit": "g"},
        "CARB": {"amount": 45.0, "unit": "g"},
        "NA": {"amount": 400.0, "unit": "mg"},
        "ENERGY": {"amount": 350.0, "unit": "kcal"},
    }

    result = extract_features(test_ingredients, test_nutrition, "leavened")
    print("Extracted features:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"\nFeature count: {len(result)}")
    print(f"Targets: {RecipeFeatureExtractor().get_target_names()}")
