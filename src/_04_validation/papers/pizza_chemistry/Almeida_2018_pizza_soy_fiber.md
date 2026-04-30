# Pizza with Soy and Wheat Fiber - Rheological and Quality Characteristics

**Sources (con PDF)**:
- Glicerina, V. et al. (2018). "Influence of the addition of soy product and wheat fiber on rheological, textural, and other quality characteristics of pizza." *J Texture Stud*, 49, 415-423. PDF: Almeida_2018_pizza_soy_fiber.pdf

---

## Formule Chiave

### 1. Water Absorption by Fiber
```
Water_absorbed = Flour_water + Soy_paste_water + Fiber_water
```
- Soy paste: ~60% moisture, binds water via protein
- Wheat fiber: ~5% water uptake capacity
- Total hydration increases with enrichment

### 2. Dough Elasticity Modification
```
E_enriched = E_control * (1 - 0.15 * Fiber% - 0.1 * Soy%)
```
- Fiber and soy interfere with gluten network
- Reduced elasticity but maintained extensibility

### 3. Force Decay (Stress Relaxation)
```
F(t)/F0 = a + (1-a) * exp(-b*t)
```
- a: relaxation percentage (%) → higher = more viscous
- b: decay rate (N/s) → higher = faster relaxation
- Enriched dough: lower resistance to extension

---

## Formulazioni Sperimentali

### Control vs Enriched Pizza

| Ingredient | Control (C) | Enriched (E) |
|-----------|-------------|--------------|
| Wheat flour (type 0) | 100g | 87g |
| Water | 60g | 60g |
| Soy paste | - | 20g |
| Wheat fiber | - | 5g |
| Brewer's yeast | 4g | 4g |
| Sugar | 2g | 2g |
| Salt | 1g | 1g |
| EVO oil | 4g | 4g |

### Hydration Adjustments
- Enriched dough moisture: higher due to soy paste (60% water)
- Effective hydration = 60% + soy contribution
- Fiber binds water but doesn't release it during baking

---

## Parametri di Qualità

### Nutritional Comparison (per 100g)

| Parameter | Control | Enriched | Change |
|-----------|---------|----------|--------|
| Energy (kcal) | ~270 | ~245 | -9% |
| Protein (g) | 8.5 | 10.2 | +20% |
| Fiber (g) | 2.1 | 5.8 | +176% |
| Saturated fat (g) | 2.8 | 2.1 | -25% |
| Cholesterol (mg) | 12 | 8 | -33% |

### Rheological Properties

| Parameter | Control | Enriched | Interpretation |
|-----------|---------|----------|----------------|
| Resistance to extension | Higher | Lower (+soy) | Weaker gluten network |
| Extensibility | Similar | Similar | Good for shaping |
| Dough force | Higher | Lower | Less elastic |
| Moisture content | Lower | Higher | Better water binding |

---

## Equazioni di Validazione

### Predict Enriched Dough Behavior
```python
def enriched_dough_properties(flour_pct, soy_pct, fiber_pct, base_hydration):
    """
    Returns estimated dough characteristics
    """
    # Effective hydration
    soy_water = soy_pct * 0.60  # soy paste is 60% water
    fiber_water_binding = fiber_pct * 0.05
    effective_hydration = base_hydration + soy_water + fiber_water_binding
    
    # Elasticity reduction
    elasticity_factor = 1.0 - 0.15 * (fiber_pct / 100) - 0.10 * (soy_pct / 100)
    
    # Protein increase
    base_protein = 10  # % in flour
    soy_protein = soy_pct * 0.15  # ~15% protein in soy paste
    total_protein = (base_protein * flour_pct/100 + soy_protein) / (flour_pct/100 + soy_pct/100)
    
    flags = []
    if fiber_pct > 8:
        flags.append("HIGH_FIBER: may reduce volume significantly")
    if soy_pct > 25:
        flags.append("HIGH_SOY: strong beany flavor risk")
    if effective_hydration > 70:
        flags.append("HIGH_HYDRATION: sticky dough, hard to handle")
    
    return {
        "effective_hydration": round(effective_hydration, 1),
        "elasticity_factor": round(elasticity_factor, 2),
        "total_protein_pct": round(total_protein, 1),
        "flags": flags
    }
```

### Nutritional Validation
```python
def validate_enriched_pizza(base_kcal, soy_pct, fiber_pct):
    """
    Returns estimated nutritional changes
    """
    kcal_reduction = base_kcal * (0.05 * fiber_pct/100 + 0.02 * soy_pct/100)
    final_kcal = base_kcal - kcal_reduction
    
    return {
        "base_kcal": base_kcal,
        "final_kcal": round(final_kcal),
        "reduction_pct": round(kcal_reduction/base_kcal*100, 1)
    }
```

---

## Validazione Sistema

Per validare ricette pizza arricchite:
1. **Sostituzione massima**: max 20% soy paste + 5% fiber per qualità accettabile
2. **Idratazione**: compensare acqua assorbita da fiber e soy
3. **Lievitazione**: tempo simile, volume leggermente ridotto
4. **Cottura**: stessa temperatura (485°C wood oven, 60-90s)
5. **Texture**: crust più morbido, crumb più umido
6. **Shelf life**: più breve per maggiore umidità
7. **Nutrizione**: 
   - Proteine +15-25%
   - Fibre +150-200%
   - Kcal -5-15%
   - Grassi saturi -20-30%

---