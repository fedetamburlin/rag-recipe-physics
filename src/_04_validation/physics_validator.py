"""Physics-based recipe validation module."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

class ValidationLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ValidationResult:
    code: str
    message: str
    level: ValidationLevel
    suggestion: Optional[str] = None

@dataclass 
class RecipeValidation:
    is_valid: bool
    category: str
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "category": self.category,
            "errors": [{"code": e.code, "message": e.message, "suggestion": e.suggestion} for e in self.errors],
            "warnings": [{"code": w.code, "message": w.message, "suggestion": w.suggestion} for w in self.warnings]
        }

def validate_spread(fat_pct: float, sugar_pct: float) -> dict:
    """Validate cookie spread ratio using Miller 1997."""
    spread_ratio = 1.5 + 0.015 * fat_pct + 0.01 * sugar_pct
    return {"spread_ratio": round(spread_ratio, 2), "risk": "high" if spread_ratio > 3.5 else "low"}

def validate_bread_hydration(hydration_pct: float) -> dict:
    """Validate bread hydration level."""
    if hydration_pct < 50:
        return {"status": "error", "message": "Too low - dense crumb", "suggestion": "Increase to 55-70%"}
    elif hydration_pct < 55:
        return {"status": "warning", "message": "Low - tight crumb", "suggestion": "Consider 60-65%"}
    elif hydration_pct <= 70:
        return {"status": "valid", "message": "Good range for most breads"}
    elif hydration_pct <= 80:
        return {"status": "warning", "message": "High - sticky", "suggestion": "Reduce to below 75%"}
    else:
        return {"status": "error", "message": "Too high", "suggestion": "Use 65-70%"}

def validate_pizza_proof(yeast_pct: float, salt_pct: float, temp_C: float = 25) -> dict:
    """Estimate pizza proof time from yeast/salt/temp."""
    activity = max(0.1, 1.0 - (salt_pct - 2) * 0.5) if salt_pct > 2 else 1.0
    temp_factor = 1.0 if 20 <= temp_C <= 30 else (0.5 if temp_C < 20 else max(0.1, 1.5 - (temp_C - 30) * 0.1))
    base_time = 0.5 / yeast_pct if yeast_pct > 0 else 999
    proof_time = base_time / (activity * temp_factor)
    return {"proof_time_h": round(proof_time, 1), "rise_ratio": round(2.0 * activity * temp_factor, 1)}

def validate_yeast_fermentation(yeast_pct: float, salt_pct: float, sugar_pct: float, protein_pct: float = 10, temp_C: float = 25) -> dict:
    """Full yeast fermentation validation."""
    activity = max(0.1, 1.0 - (salt_pct - 2) * 0.5) if salt_pct > 2 else 1.0
    if sugar_pct > 5:
        activity *= max(0.2, 1.0 - (sugar_pct - 5) * 0.3)
    temp_factor = 1.0 if 20 <= temp_C <= 30 else (0.5 if temp_C < 20 else max(0.1, 1.5 - (temp_C - 30) * 0.1))
    base_proof = 0.5 / yeast_pct if yeast_pct > 0 else 999
    proof_time_h = base_proof / (activity * temp_factor)
    risk_flags = []
    if salt_pct > 2.5: risk_flags.append("high_salt_inhibits_yeast")
    if sugar_pct > 5: risk_flags.append("high_sugar_inhibits_yeast")
    if protein_pct < 8: risk_flags.append("low_protein_weak_structure")
    return {"proof_time_h": round(proof_time_h, 1), "risk_flags": risk_flags, "is_valid": len(risk_flags) == 0}

def validate_recipe(ingredients: Dict[str, float], category: str, **kwargs) -> dict:
    """Main validation entry point."""
    errors, warnings = [], []
    
    # Parse baker's %
    flour = ingredients.get("flour", 100)
    if flour == 0: flour = 100
    bakers = {k: (v/flour)*100 for k, v in ingredients.items() if v and v > 0}
    
    # Calculate water content
    water = ingredients.get("water", 0)
    water += ingredients.get("milk", 0) * 0.87
    water += ingredients.get("eggs", 0) * 0.75
    water += ingredients.get("butter", 0) * 0.15
    hydration = (water / flour) * 100 if flour > 0 else 0
    
    # Category-specific validation
    if category in ["bread", "sourdough"]:
        if hydration < 50:
            errors.append({"code": "BREAD_HYD_LOW", "message": f"Hydration {hydration:.0f}% too low", "suggestion": "Increase to 55-70%"})
        elif hydration > 80:
            errors.append({"code": "BREAD_HYD_HIGH", "message": f"Hydration {hydration:.0f}% too high", "suggestion": "Reduce to below 75%"})
        salt = bakers.get("salt_pct", bakers.get("salt", 0))
        yeast = bakers.get("yeast_pct", bakers.get("yeast", 0))
        if salt > 2 and yeast > 2:
            errors.append({"code": "BREAD_YEAST_INHIBITED", "message": "High salt + high yeast inhibits fermentation", "suggestion": "Reduce salt or yeast"})
            
    elif category in ["cookie", "biscuit"]:
        fat = bakers.get("fat_pct", 50)
        sugar = bakers.get("sugar_pct", 60)
        spread = 1.5 + 0.015 * fat + 0.01 * sugar
        if spread < 2.0:
            warnings.append({"code": "COOKIE_SPREAD_LOW", "message": f"Low spread ({spread:.1f})", "suggestion": "Increase fat"})
        elif spread > 4.0:
            warnings.append({"code": "COOKIE_SPREAD_HIGH", "message": f"High spread ({spread:.1f})", "suggestion": "Reduce fat"})
            
    elif category in ["pizza", "calzone"]:
        if hydration < 50:
            errors.append({"code": "PIZZA_HYD_LOW", "message": f"Hydration {hydration:.0f}% too low", "suggestion": "Increase to 55-65%"})
        temp_C = kwargs.get("bake_temp_C", 180)
        time_min = kwargs.get("bake_time_min", 15)
        if temp_C >= 450 and time_min > 2.5:
            errors.append({"code": "PIZZA_OVERBAKE", "message": f"HiT {temp_C}°C for {time_min}min = acrylamide risk", "suggestion": "Limit to 2 min"})
            
    return {"is_valid": len(errors) == 0, "category": category, "errors": errors, "warnings": warnings}

if __name__ == "__main__":
    print("=== Bread Validation ===")
    print(validate_recipe({"flour": 500, "water": 325, "yeast": 5, "salt": 10}, "bread"))
    
    print("\n=== Cookie Spread ===")
    print(validate_spread(60, 80))
    
    print("\n=== Pizza Proof ===")
    print(validate_pizza_proof(0.04, 1.8, 25))
