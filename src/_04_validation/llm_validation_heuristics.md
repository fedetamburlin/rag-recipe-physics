# Recipe Validation Heuristics for LLM Output

## Physical-Chemical-Nutritional Formula Summary

### 1. Cookie/Pastry Spread (Elongational Viscosity)

```python
def validate_cookie_spread(fat_pct: float, flour_pct: float, 
                         sugar_pct: float, moisture: float) -> dict:
    """
    fat_pct, flour_pct, sugar_pct: weight percentages
    moisture: decimal (0-1)
    Returns: spread_ratio, viscosity_ratio, risk_level
    """
    # Elongational viscosity ratio (fat/flour baseline)
    base_viscosity = 1.0
    fat_effect = 0.003 * fat_pct  # each % fat increases eta_E
    sugar_effect = 0.002 * sugar_pct
    viscosity_ratio = base_viscosity + fat_effect + sugar_effect
    
    # Expected spread ratio (D_final/D_initial)
    spread_ratio = 1.5 + 0.015 * fat_pct + 0.01 * sugar_pct - 0.02 * flour_pct
    
    # Clamp reasonable range
    spread_ratio = max(1.5, min(4.0, spread_ratio))
    
    risk_level = "low" if 2.0 <= spread_ratio <= 3.5 else "medium"
    if spread_ratio < 1.5 or spread_ratio > 4.0:
        risk_level = "high"
    
    return {"spread_ratio": spread_ratio, 
            "viscosity_ratio": viscosity_ratio,
            "risk": risk_level}
```

### 2. Baking Time & Temperature

```python
def validate_bake_time(thickness_cm: float, hydration: float,
                      fat_pct: float, sugar_pct: float) -> dict:
    """
    Returns: suggested_temp_C, suggested_time_min, moisture_loss_pct
    """
    # Base time from thickness
    base_time = thickness_cm * 8  # ~8 min per cm
    
    # Hydration adjustment
    hydration_factor = 1.0 + (hydration - 0.35)
    
    # Fat slows moisture loss, sugar slows browning
    fat_factor = 1.0 + 0.001 * fat_pct
    sugar_factor = 1.0 + 0.002 * sugar_pct
    
    time_min = base_time * hydration_factor * fat_factor * sugar_factor
    
    # Temperature selection
    if thickness_cm < 1:
        temp_C = 180  # cookies
    elif thickness_cm < 3:
        temp_C = 175  # muffins, cakes
    else:
        temp_C = 190  # breads
    
    moisture_loss = 15 + (hydration * 20)  # expected loss %
    
    return {"temp_C": temp_C, "time_min": round(time_min),
            "moisture_loss_pct": round(moisture_loss, 1)}
```

### 3. Yeast Fermentation (Pizza/Bread)

```python
def validate_yeast_proof(yeast_pct: float, salt_pct: float,
                       sugar_pct: float, protein_pct: float,
                       temp_C: float) -> dict:
    """
    Returns: proof_time_h, rise_ratio, risk_flags
    """
    # Yeast activity affected by salt
    if salt_pct > 2:
        activity = max(0.1, 1.0 - (salt_pct - 2) * 0.5)
    else:
        activity = 1.0
    
    # Sugar inhibition
    if sugar_pct > 5:
        activity *= max(0.2, 1.0 - (sugar_pct - 5) * 0.3)
    
    # Temperature correction (optimal 25°C)
    if 20 <= temp_C <= 30:
        temp_factor = 1.0
    elif temp_C < 20:
        temp_factor = 0.5
    else:
        temp_factor = max(0.1, 1.5 - (temp_C - 30) * 0.1)
    
    # Base proof time
    base_proof_h = 0.5 / yeast_pct if yeast_pct > 0 else 999
    
    proof_time_h = base_proof_h / (activity * temp_factor)
    rise_ratio = 2.0 * activity * temp_factor
    
    risk_flags = []
    if salt_pct > 2.5:
        risk_flags.append("high_salt_inhibits_yeast")
    if sugar_pct > 5:
        risk_flags.append("high_sugar_inhibits_yeast")
    if protein_pct < 8:
        risk_flags.append("low_protein_weak_structure")
    if proof_time_h > 3:
        risk_flags.append("long_proof_time")
    
    return {"proof_time_h": round(proof_time_h, 1),
            "rise_ratio": round(rise_ratio, 1),
            "risk_flags": risk_flags}
```

### 4. Nutritional Balance

```python
def validate_nutrition(flour_pct: float, fat_pct: float, 
                     sugar_pct: float, protein_pct: float) -> dict:
    """
    Returns: calories_per_100g, macro_ratios, risk_flags
    """
    # Simplified kcal/100g calculation
    kcal = (4 * flour_pct * 0.9) + (9 * fat_pct) + (4 * sugar_pct) + (4 * protein_pct * 0.9)
    
    # Macro percentages
    total_macro = flour_pct + fat_pct + sugar_pct + protein_pct
    carb_pct = flour_pct + sugar_pct
    fat_ratio = fat_pct / total_macro if total_macro > 0 else 0
    sugar_ratio = sugar_pct / total_macro if total_macro > 0 else 0
    
    risk_flags = []
    if fat_ratio > 0.4:
        risk_flags.append("high Fat (>40%)")
    if sugar_ratio > 0.3:
        risk_flags.append("high Sugar (>30%)")
    if protein_pct < 5:
        risk_flags.append("low Protein for structure")
    
    return {"kcal_per_100g": round(kcal, 0),
            "fat_pct_of_total": round(fat_ratio * 100, 1),
            "sugar_pct_of_total": round(sugar_ratio * 100, 1),
            "risk_flags": risk_flags}
```

## Quick Validation Rules

| Issue | Check | Threshold |
|-------|-------|----------|
| Spread too much | Reduce fat, increase flour | Fat < 30% |
| Dense crumb | Increase protein, reduce sugar | Protein > 8% |
| Burning | Reduce sugar, lower temp | Sugar < 25% |
| Collapse | Increase protein, reduce yeast | Protein > 9%, Yeast < 2% |
| Dry texture | Increase hydration, fat | Hydration > 35% |
| Raw center | Increase time/temp, reduce thickness | < 2cm thick |

## Priority Warnings

1. **CRITICAL**: Protein < 8% → bread won't rise properly
2. **CRITICAL**: Yeast > 3% + Salt > 2% → yeast inhibited
3. **HIGH**: Fat > 50% at > 180°C → burnt fat taste
4. **HIGH**: Sugar > 40% → excessive browning, burnt
5. **MEDIUM**: Hydration > 50% → difficult handling
6. **MEDIUM**: Salt > 3% → too salty