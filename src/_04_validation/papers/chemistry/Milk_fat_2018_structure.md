# Milk Fat as Structuring Agent of Plastic Lipid Bases

**Sources (con PDF)**:
- Viriato, R.L.S. et al. (2018). "Milk fat as a structuring agent of plastic lipid bases." *Food Research International*, 111, 120-129. PDF: Milk_fat_2018_structure.pdf

---

## Formule Chiave

### 1. Avrami Equation for Crystallization Kinetics
```
SFC(t) / SFC_max = 1 - exp(-k * t^n)
```
- SFC(t): solid fat content at time t (%)
- SFC_max: maximum solid fat content
- k: crystallization rate constant
- n: Avrami exponent (indicates nucleation mechanism)
- t: time (min)

### 2. Melting Point from SFC
```
T_melt = T(SFC = 4%)
```
Temperature at which solid fat content drops to 4%.

### 3. Compatibility Check
```
SFC_blend = Σ(w_i * SFC_i)
```
If experimental SFC < calculated → incompatibility (eutectic effect)

---

## Parametri Sperimentali

### Solid Fat Content (SFC) - Milk Fat Blends

| Blend (AMF:HOSO) | SFC @ 10°C | SFC @ 20°C | SFC @ 30°C | T_melt (°C) |
|-------------------|------------|------------|------------|-------------|
| 100:00 | 45% | 28% | 12% | 38 |
| 90:10 | 40% | 24% | 9% | 36 |
| 80:20 | 35% | 20% | 7% | 34 |
| 70:30 | 30% | 16% | 5% | 32 |
| 60:40 | 25% | 13% | 3% | 30 |
| 50:50 | 20% | 10% | 2% | 28 |

### Hardness vs SFC
```
Hardness (g) = 850 * SFC_20C^1.5
```
- SFC_20C: solid fat content at 20°C (%)

---

## Polymorphism in Milk Fat

| Form | Stability | Melting Range | Application |
|------|-----------|---------------|-------------|
| α (alpha) | Unstable | 15-20°C | Transient |
| β' (beta-prime) | Stable | 25-35°C | **Desired for plasticity** |
| β (beta) | Most stable | 35-45°C | Too firm |

Milk fat crystallizes primarily in **β' form**, ideal for:
- Trapping liquid oil in crystal network
- Providing plasticity without chemical modification

---

## Equazioni di Validazione

### Predict Plasticity
```python
def predict_plasticity(sfc_10C, sfc_20C, sfc_30C):
    """
    Returns: plastic_score (0-10), risk_flags
    """
    # Ideal plastic fat profile
    ideal_10C = 30  # minimum SFC at 10°C
    ideal_20C = 15  # minimum SFC at 20°C
    ideal_30C = 5   # maximum SFC at 30°C
    
    score = 10 - abs(sfc_10C - ideal_10C)/5 - abs(sfc_20C - ideal_20C)/3
    
    flags = []
    if sfc_20C > 25:
        flags.append("too_hard")
    if sfc_20C < 8:
        flags.append("too_soft")
    if sfc_30C > 10:
        flags.append("palate_cling")
    if sfc_10C < 20:
        flags.append("poor_stand_up")
    
    return {"score": max(0, score), "flags": flags}
```

### Predict Melting Behavior
```python
def melting_quality(t_melt):
    """
    t_melt: melting point (°C)
    """
    if 32 <= t_melt <= 37:
        return "good", "melts_near_body_temp"
    elif t_melt < 32:
        return "risk", "too_soft_at_room_temp"
    else:
        return "risk", "palate_cling"
```

---

## Validazione Sistema

Per validare ricette con grassi:
1. **Verificare SFC profile**: 10°C > 20%, 20°C 10-25%, 30°C < 10%
2. **Controllare T_melt**: 32-37°C per evitare palate cling
3. **Polymorph check**: β' form desiderabile
4. **kcal**: AMF = 884 kcal/100g, HOSO = 884 kcal/100g (simile)
5. **Saturated fat reduction**: 50:50 blend riduce SFA del 42%

---