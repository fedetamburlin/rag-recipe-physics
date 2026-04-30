# Pizza Dough Leavening - Physico-Chemical Properties and Effect of Time

**Sources (con PDF)**:
- Covino, C. et al. (2023). "Study of Physico-Chemical Properties of Dough and Wood Oven-Baked Pizza Base: The Effect of Leavening Time." *Foods*, 12(7), 1407. PDF: Masi_2023_pizza_leavening.pdf

---

## Formule Chiave

### 1. Volume Growth Kinetics
```
V(t)/V0 = 1 + V_max / (1 + exp(-k*(t - t_0)))
```
- Sigmoid curve with 3 phases:
  - Lag (0-8h): V/V0 reaches 1.3
  - Log (8-30h): volume triples
  - Stationary (>30h): asymptotic

### 2. Stress Relaxation
```
t/F0 = 1/(a*b) + t/a
```
- a: relaxation percentage (%) → 0% = elastic, 100% = viscous
- b: decay rate (N/s)
- Early leavening (4-8h): low a, high elasticity
- Late leavening (>16h): high a, viscous behavior

### 3. Elastic Modulus G'
```
G'(T) = f(gluten_network, starch_gelatinization)
```
- G' decreases with leavening time >16h (gluten weakening)
- Optimal extensibility at 16-24h

### 4. Starch Gelatinization Enthalpy
```
ΔH = 0.975 ± 0.013 J/g (for 16h leavened dough)
```
- T_onset: 55-60°C
- T_peak: 60-65°C
- T_end: 70-75°C

---

## Parametri di Lievitazione

### Standard Neapolitan Pizza Dough

| Ingredient | Amount (%) |
|-----------|-----------|
| Flour (00 type) | 60.35% |
| Water | 37.72% |
| Salt | 1.88% |
| Fresh brewer's yeast | 0.04% |

### Leavening Conditions
- Temperature: 22°C
- Humidity: 80% RH
- Dough ball weight: 250g
- Baking: 60s at 485±30°C (wood oven)

### Volume Development over Time

| Time (h) | V/V0 Index | Phase | Characteristics |
|----------|-----------|-------|----------------|
| 0 | 1.0 | Start | Dense, strong gluten |
| 4 | 1.1-1.2 | Lag | Shape flattens, volume constant |
| 8 | 1.3 | End lag | Slight rise |
| 16 | 2.0-2.5 | Log | Rapid growth, bubble stretching |
| 24 | 2.8-3.0 | Late log | Near maximum |
| 30 | 3.0-3.2 | Stationary | Maximum volume |
| 48 | 3.0 | Over-proofed | Flattening, CO2 loss |

### Rheological Properties by Leavening Time

| Time (h) | Compression Work (J) | Relaxation a (%) | Decay b (N/s) | Diameter (mm) |
|----------|---------------------|------------------|---------------|---------------|
| 0 | High | Low (~20%) | Low | Small |
| 4 | High | ~25% | Medium | Medium |
| 8 | Medium | ~30% | Medium | Medium |
| 16 | Medium | ~40% | High | Large |
| 24 | Low | ~50% | High | Large |
| 48 | Low | ~60% | High | Very large |

---

## Starch Digestibility

### Rapidly Digestible Starch (RDS)

| Sample | RDS (%) | SDS (%) | RS (%) |
|--------|---------|---------|--------|
| Dough 0h | High | Low | Low |
| Dough 16h | Lower | Higher | Higher |
| Pizza base (baked) | Higher | Lower | Lower |

**Note**: Gelatinization during baking increases susceptibility to α-amylase.

### Acrylamide and Reducing Sugars
- Reducing sugars increase with leavening time (starch hydrolysis)
- Free amino groups increase with leavening time
- **Acrylamide remains constant** despite higher precursors (yeast metabolism balances)

---

## Microstructure (SEM)

### Gluten Network Evolution
```
0-8h: Dense, continuous gluten matrix
16h: Open, weaker structure (optimal for extensibility)
24-48h: Discontinuous, relaxed network (CO2 loss risk)
```

### Starch Granules
- 0h: Intact, embedded in gluten
- 16h: Slightly separated
- Baked: Swollen, gelatinized, amylose leached

---

## Equazioni di Validazione

### Predict Volume from Time
```python
def predict_volume(t_hours):
    """
    Returns V/V0 ratio for pizza dough at 22°C, 0.04% yeast
    """
    if t_hours < 8:
        return 1.0 + 0.04 * t_hours
    elif t_hours < 30:
        return 1.3 + 0.06 * (t_hours - 8)
    else:
        return 3.0  # stationary
```

### Optimal Leavening Time
```python
def optimal_leavening(target_property):
    """
    target_property: 'volume', 'extensibility', 'digestibility', 'flavor'
    """
    recommendations = {
        'volume': (20, 30, "Maximum rise"),
        'extensibility': (12, 20, "Optimal for shaping"),
        'digestibility': (16, 24, "Lower glycemic index"),
        'flavor': (16, 24, "Complex aroma development")
    }
    return recommendations.get(target_property, (16, 24, "Balanced"))
```

### Dough Quality Check
```python
def dough_quality_check(leavening_hours, temp_C, yeast_pct):
    """
    Returns quality assessment
    """
    flags = []
    
    # Too short
    if leavening_hours < 8:
        flags.append("UNDERPROOFED: dense, poor volume")
    
    # Too long
    if leavening_hours > 36:
        flags.append("OVERPROOFED: risk of collapse, CO2 loss")
    
    # Temperature check
    if temp_C < 18:
        flags.append("COLD: very slow fermentation")
    if temp_C > 28:
        flags.append("WARM: fast but risk of overproofing")
    
    # Yeast check
    if yeast_pct > 0.1:
        flags.append("HIGH_YEAST: very fast, less flavor complexity")
    if yeast_pct < 0.02:
        flags.append("LOW_YEAST: extremely slow")
    
    return flags
```

---

## Validazione Sistema

Per validare ricette pizza:
1. **Tempo minimo**: 8h per sviluppo base
2. **Tempo ottimale**: 16-24h per volume + estensibilità
3. **Tempo massimo**: 30-36h (oltre = collasso)
4. **Temperatura**: 20-24°C ideale
5. **Umidità**: 75-85% RH per prevenire crosta secca
6. **Yeast**: 0.03-0.05% fresh yeast per lievitazione lenta
7. **Sale**: 1.8-2.2% (fortifica glutine, controlla fermentazione)
8. **Idratazione**: 60-65% per pizza napoletana
9. **Cottura**: 60-90s a 485°C (wood oven) o 2-3 min a 450°C (elettrico)

---