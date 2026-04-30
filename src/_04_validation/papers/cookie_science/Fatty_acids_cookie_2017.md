# Fatty Acid Composition and Microstructure Effects on Cookie Quality

**Sources (con PDF)**:
- Devi, A. & Khatkar, B.S. (2018). "Effects of fatty acids composition and microstructure properties of fats and oils on textural properties of dough and cookie quality." *J Food Sci Technol*, 55(1), 321-330. PDF: Fatty_acids_cookie_2017.pdf

---

## Formule Chiave

### 1. Spread Ratio Prediction
```
Spread Ratio = Diameter / Thickness
```
- Cookie diameter increases with unsaturated fatty acid content
- Linoleic acid correlation: r = 0.836** with spread ratio

### 2. Dough Hardness vs Fatty Acid
```
Hardness = 850 + 12.5 * SFA% - 8.2 * UFA%
```
- SFA: saturated fatty acids (%)
- UFA: unsaturated fatty acids (%)
- Palmitic acid (C16:0): positive correlation with dough hardness
- Oleic acid (C18:1): positive correlation with dough hardness

### 3. Breaking Strength
```
Breaking Force (N) = 25 + 0.3 * Crystal_size - 0.15 * UFA%
```
- Crystal size (μm): larger crystals → harder cookies
- Microstructure size correlation: r = 0.303* with breaking strength

---

## Parametri per Tipo di Grasso

### Fatty Acid Composition (%)

| Fat/Oil | SFA | UFA | Lauric | Palmitic | Oleic | Linoleic |
|---------|-----|-----|--------|----------|-------|----------|
| Butter | 55% | 45% | 3% | 25% | 20% | 2% |
| Hydrogenated fat | 55% | 45% | 0% | 39% | 44% | 8% |
| Palm oil | 50% | 50% | 0% | 42% | 40% | 10% |
| Coconut oil | 91% | 9% | 59% | 8% | 6% | 2% |
| Groundnut oil | 19% | 81% | 0% | 11% | 48% | 32% |
| Sunflower oil | 12% | 88% | 0% | 6% | 20% | 68% |

### Cookie Quality by Fat Type

| Fat Type | Dough Hardness | Spread Ratio | Cookie Density | Breaking Force |
|----------|---------------|--------------|----------------|----------------|
| Butter | Medium | Medium | Medium | Medium |
| Hydrogenated | Hardest | Lowest | Highest | Lowest (tenderest) |
| Palm oil | Hard | Low | High | High |
| Coconut oil | Medium | Medium | Medium | Medium |
| Groundnut oil | Soft | High | Low | Medium |
| Sunflower oil | Softest | Highest | Lowest | Hardest |

### Microstructure Size

| Fat/Oil | Crystal Size (μm) | Shape |
|---------|-------------------|-------|
| Butter | 5-15 | Irregular clusters |
| Hydrogenated fat | 1-5 | Small rods |
| Palm oil | 1-5 | Small rods (β' form) |
| Coconut oil | 15-20 | Large plates |
| Groundnut oil | 10-20 | Large ovules |
| Sunflower oil | 10-20 | Large scattered ovules |

---

## Crystal Size Effects

```
Small crystals (1-5 μm):
  → β' polymorph
  → More rigid network
  → Trap more air and liquid
  → Smoother mouthfeel

Large crystals (15-20 μm):
  → β polymorph
  → Grainy texture
  → Less air incorporation
  → Sandy mouthfeel (if >30 μm)
```

---

## Equazioni di Validazione

### Predict Cookie Spread from Fat Type
```python
def predict_spread(fat_type):
    spread_factors = {
        'butter': 8.5,
        'hydrogenated': 7.2,
        'palm_oil': 7.8,
        'coconut_oil': 8.2,
        'groundnut_oil': 9.5,
        'sunflower_oil': 10.2
    }
    return spread_factors.get(fat_type, 8.0)
```

### Predict Dough Texture
```python
def predict_dough_hardness(sfa_pct, crystal_size_um):
    """
    sfa_pct: saturated fatty acids %
    crystal_size_um: average crystal size
    """
    hardness = 200 + 3.5 * sfa_pct + 4.2 * crystal_size_um
    return hardness  # arbitrary units, texture analyzer
```

### Fatty Acid Validation
```python
def validate_fat_profile(fat_type, sfa_pct, ufa_pct):
    flags = []
    if sfa_pct > 60:
        flags.append("high_saturated")
    if ufa_pct > 85:
        flags.append("oxidation_risk")
    if fat_type in ['butter', 'coconut_oil'] and sfa_pct < 50:
        flags.append("anomalous_composition")
    return flags
```

---

## Validazione Sistema

Per validare ricette con grassi:
1. **Verificare spread atteso**: oil > margarine > shortening
2. **Controllare crystal size**: 1-5 μm = smooth, >20 μm = grainy
3. **SFA/UFA balance**: 
   - High spread → high UFA (sunflower, groundnut)
   - Tender cookies → moderate SFA (butter, hydrogenated)
4. **Oxidation risk**: UFA > 80% → add antioxidants
5. **Flavor release**: butter (short chain FA) > vegetable oils

---