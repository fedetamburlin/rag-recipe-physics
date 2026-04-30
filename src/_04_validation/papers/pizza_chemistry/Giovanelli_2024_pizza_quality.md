# High-Temperature Pizza Baking - Quality and Heat-Related Byproducts

**Sources (con PDF)**:
- Giovanelli, G. et al. (2024). "Impact of high-temperature household electric ovens on quality attributes and heat-related byproducts content of homemade pizzas." *J Food Compos Anal*, 133, 106460. PDF: Giovanelli_2024_pizza_quality.pdf

---

## Formule Chiave

### 1. Cooking Weight Loss
```
WL% = (Raw_weight - Cooked_weight) / Raw_weight * 100
```
- HiT (450°C, 1-3.5 min): 18-25% WL
- MeT (310°C, 4.5-9 min): 20-28% WL
- LoT (250°C, 14 min): 22-30% WL

### 2. Maillard Reaction Products (MRPs)
```
MRPs ∝ T^α * t^β * [Reducing_Sugars]^γ
```
- α, β, γ: reaction order constants
- Higher T → more MRPs in shorter time
- Optimal: HiT 90s or MeT 6-7 min

### 3. Acrylamide Formation
```
AA (μg/kg) = k * [Asparagine] * [Reducing_Sugars] * exp(-Ea/RT) * t
```
- Ea ~ 100-130 kJ/mol
- Critical: surface T > 150°C + time > 2 min
- EU benchmark: <50 μg/kg for wheat bread

### 4. HMF Formation
```
HMF (μg/kg) = A * exp(-Ea_HMF/RT) * [Hexoses] * t
```
- Ea_HMF ~ 80-100 kJ/mol
- Higher in crust than whole pizza
- White bread reference: 4281 μg/kg

---

## Parametri di Cottura

### Temperature/Time Combinations Tested

| Condition | Temp (°C) | Time (min) | WL% | Crust Color | Quality |
|-----------|-----------|------------|-----|-------------|---------|
| HiT-1 | 450 | 1.0 | ~15% | Very light | Undercooked |
| HiT-1.5 | 450 | 1.5 | ~18% | Light golden | Good |
| HiT-2 | 450 | 2.0 | ~20% | Golden | Optimal |
| HiT-2.5 | 450 | 2.5 | ~22% | Brown | Good |
| HiT-3 | 450 | 3.0 | ~24% | Dark brown | Risk AA |
| HiT-3.5 | 450 | 3.5 | ~26% | Very dark | Burnt |
| MeT-4.5 | 310 | 4.5 | ~18% | Light | Undercooked |
| MeT-5 | 310 | 5.0 | ~20% | Golden | Good |
| MeT-6.5 | 310 | 6.5 | ~23% | Brown | Optimal |
| MeT-8 | 310 | 8.0 | ~26% | Dark | Risk AA |
| MeT-9 | 310 | 9.0 | ~28% | Very dark | Overcooked |
| LoT-14 | 250 | 14.0 | ~25% | Brown | Dry, hard |

### Acrylamide Levels by Condition

| Condition | AA (μg/kg) | Risk Level |
|-----------|-----------|------------|
| HiT-1.5 | <10 | Very low |
| HiT-2 | 15-25 | Low |
| HiT-2.5 | 30-45 | Medium |
| HiT-3 | 50-80 | High (near limit) |
| MeT-5 | <15 | Very low |
| MeT-6.5 | 20-35 | Low |
| MeT-8 | 40-60 | Medium |
| LoT-14 | 25-40 | Low (but dry) |

### Moisture Content After Baking

| Fraction | HiT (2 min) | MeT (6.5 min) | LoT (14 min) |
|----------|-------------|---------------|--------------|
| Crust | 35-40% | 32-38% | 28-35% |
| Whole pizza | 50-55% | 48-53% | 45-50% |

---

## Heat Transfer in Pizza Ovens

```
Wood-fired: Q_rad (dome) + Q_cond (floor) → 485°C, 60-90s
Electric HiT: Q_rad + Q_conv → 450°C, 1-3.5 min
Electric MeT: Q_conv dominant → 310°C, 4.5-9 min
Home oven: Q_conv → 250°C, 14 min
```

### Quality Attributes by Method
| Attribute | HiT (90s) | MeT (6.5 min) | LoT (14 min) |
|-----------|-----------|---------------|--------------|
| Crust color | Golden, leopard spots | Uniform brown | Uniform, less vibrant |
| Crust texture | Soft, elastic | Slightly firm | Firm, dry |
| Bottom | Charred spots | Light brown | Pale |
| Moisture retention | Excellent | Good | Poor |
| Maillard flavor | Intense | Moderate | Weak |
| AA risk | Low-medium | Low | Low |

---

## Equazioni di Validazione

### Predict Weight Loss
```python
def predict_weight_loss(temp_C, time_min, initial_moisture=55):
    """
    Returns predicted weight loss %
    """
    # Base loss from temperature
    base_loss = 10 + 0.02 * temp_C
    
    # Time effect
    time_factor = 1 + 0.05 * time_min
    
    # Moisture effect
    moisture_factor = initial_moisture / 50
    
    wl = base_loss * time_factor * moisture_factor - 5
    return min(35, max(10, wl))
```

### Predict Acrylamide Risk
```python
def acrylamide_risk(temp_C, time_min, surface_moisture_pct):
    """
    Returns risk category and estimated AA (μg/kg)
    """
    # Acrylamide forms when surface is dry and hot
    if surface_moisture_pct > 25:
        return "very_low", "<10"
    
    # Thermal dose for AA
    thermal_dose = (temp_C - 150) * time_min if temp_C > 150 else 0
    
    if thermal_dose < 300:
        return "low", "10-25"
    elif thermal_dose < 600:
        return "medium", "25-50"
    elif thermal_dose < 900:
        return "high", "50-100"
    else:
        return "critical", ">100"
```

### Optimal Baking Recommendation
```python
def recommend_baking(oven_type, pizza_thickness_cm):
    """
    Returns recommended temp and time
    """
    if oven_type == "wood_fired":
        return {"temp_C": 485, "time_s": 60 + 15*pizza_thickness_cm}
    elif oven_type == "electric_HiT":
        return {"temp_C": 450, "time_s": 90 + 20*pizza_thickness_cm}
    elif oven_type == "electric_MeT":
        return {"temp_C": 310, "time_s": 300 + 60*pizza_thickness_cm}
    else:  # home oven
        return {"temp_C": 250, "time_s": 600 + 120*pizza_thickness_cm}
```

---

## Validazione Sistema

Per validare ricette pizza:
1. **Tempo massimo HiT**: 2.5 min a 450°C per evitare AA >50 μg/kg
2. **Tempo ottimale MeT**: 5-7 min a 310°C per equilibrio qualità/sicurezza
3. **Moisture crust**: >30% per morbidezza, <25% = secco
4. **Weight loss**: 18-25% = ottimale, >30% = troppo secco
5. **Colorazione**: L* 50-65 = golden, L* <45 = overcooked
6. **Temperature sicurezza**: Core >95°C (immediato a 450°C)
7. **Nutrizione**: AA benchmark EU = 50 μg/kg per pane/frumento

---