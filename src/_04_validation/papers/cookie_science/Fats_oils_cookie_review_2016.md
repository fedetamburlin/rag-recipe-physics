# Physicochemical, Rheological and Functional Properties of Fats and Oils in Relation to Cookie Quality

**Sources (con PDF)**:
- Devi, A. & Khatkar, B.S. (2016). "Physicochemical, rheological and functional properties of fats and oils in relation to cookie quality: a review." *J Food Sci Technol*, 53(10), 3633-3641. PDF: Fats_oils_cookie_review_2016.pdf

---

## Formule Chiave

### 1. Solid Fat Content (SFC) for Cookie Making
```
Optimal SFC @ 20°C = 15-20%
```
- Higher SFC → higher breaking force (harder cookies)
- Lower SFC → more spread, softer dough
- Upper limit more critical than lower limit

### 2. Melting Point Order
```
Saturated FA > Trans FA > Cis FA
```
- Short chain + unsaturated + cis → lower melting point
- Melting profile impacts: air incorporation, rheology, mouthfeel, shelf life

### 3. Fat Functionality Balance
```
Air incorporation = f(SFC, crystal form, mixing time)
```
- Solid part: incorporates air
- Liquid part: provides lubrication

---

## Parametri per Tipo di Grasso

### Fatty Acid Composition Summary

| Fat/Oil | SFA% | UFA% | Key Characteristics |
|---------|------|------|---------------------|
| Butter | 50-55 | 45-50 | Short chain FA (butyric), excellent flavor, β' crystals |
| Hydrogenated fat | 50-55 | 45-50 | High SFC, trans FA possible, good aeration |
| Palm oil | 50 | 50 | Palmitic acid 42%, β' polymorph, versatile |
| Coconut oil | 92 | 8 | Lauric acid 48-59%, very saturated, low mp |
| Sunflower oil | 12 | 88 | High linoleic, very soft, high spread |
| Groundnut oil | 19 | 81 | Oleic acid 48%, good stability |

### Solid Fat Content @ 20°C

| Fat | SFC @ 20°C | Cookie Effect |
|-----|-----------|---------------|
| Butter | 20-22% | Good flavor, moderate spread |
| Palm oil | 22-25% | Good structure, neutral flavor |
| Lard | 18-20% | Tender, flaky |
| Shortening | 25-35% | High volume, less spread |
| Margarine | 20-30% | Variable, depends on formulation |
| Liquid oils | 0% | Maximum spread, no aeration |

### Polymorphism in Cookie Fats

| Form | Stability | Crystal Size | Effect on Cookies |
|------|-----------|--------------|-------------------|
| α (alpha) | Unstable | Very small | Transient, not useful |
| β' (beta-prime) | Stable | 1-5 μm | **Ideal**: smooth texture, good aeration |
| β (beta) | Most stable | 20-100 μm | Sandy/grainy mouthfeel |

---

## Key Functional Properties

### 1. Air Incorporation (Creaming)
```
Volume_air = f(SFC, mixing_speed, mixing_time, temperature)
```
- Optimal: SFC 15-20% at room temperature
- Too high SFC: poor aeration, dense cookies
- Too low SFC: cannot retain air, flat cookies

### 2. Spread Control
```
Spread ∝ 1/SFC ∝ 1/(SFA%)
```
- Oils (SFC=0): maximum spread
- Butter (SFC~20%): moderate spread
- Shortening (SFC~60%): minimal spread

### 3. Texture/Hardness
```
Breaking_force = k1*SFC + k2*Crystal_size - k3*UFA%
```
- Higher SFC → harder cookies
- Larger crystals → harder, grainy
- More unsaturated → softer, more tender

---

## Equazioni di Validazione

### Predict Cookie Quality from Fat Properties
```python
def predict_cookie_quality(fat_type, sfc_20C, crystal_form):
    """
    Returns quality predictions
    """
    quality = {"spread": None, "texture": None, "volume": None, "flags": []}
    
    # Spread prediction
    if sfc_20C < 5:
        quality["spread"] = "very_high"
    elif sfc_20C < 15:
        quality["spread"] = "high"
    elif sfc_20C < 25:
        quality["spread"] = "moderate"
    else:
        quality["spread"] = "low"
    
    # Texture
    if crystal_form == 'β\'':
        quality["texture"] = "smooth"
    elif crystal_form == 'β':
        quality["texture"] = "grainy"
    else:
        quality["texture"] = "unknown"
    
    # Volume/aeration
    if 15 <= sfc_20C <= 25:
        quality["volume"] = "good"
    elif sfc_20C > 30:
        quality["volume"] = "low"
        quality["flags"].append("HIGH_SFC: poor aeration")
    else:
        quality["volume"] = "moderate"
    
    return quality
```

### Fat Selection Guide
```python
def select_fat_for_cookie(target_spread, target_texture):
    """
    Returns recommended fat type
    """
    recommendations = {
        ("high", "tender"): ["sunflower_oil", "groundnut_oil"],
        ("moderate", "smooth"): ["butter", "margarine"],
        ("low", "crisp"): ["shortening", "palm_oil"],
        ("moderate", "flaky"): ["lard", "butter"]
    }
    return recommendations.get((target_spread, target_texture), ["butter"])
```

---

## Validazione Sistema

Per validare ricette cookie:
1. **SFC check**: 15-20% @ 20°C per ottimale aerazione
2. **Crystal form**: β' preferibile per smooth texture
3. **Spread control**: 
   - High spread → oil or low-SFC fat
   - Low spread → shortening or high-SFC fat
4. **Flavor**: butter > margarine > shortening > oil
5. **Shelf life**: saturated fats più stabili, UFA>80% richiede antiossidanti
6. **Health**: bilanciare SFA/UFA secondo target nutrizionali

---