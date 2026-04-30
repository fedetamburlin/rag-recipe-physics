# Fat Crystallization and Functionality in Baking

**Sources (con PDF)**:
- Viriato, R.L.S. et al. (2018). "Milk fat as a structuring agent of plastic lipid bases." *Food Research International*, 111, 120-129. PDF: Milk_fat_2018_structure.pdf

---

## Formule Chiave

### 1. Solid Fat Index (SFI)
```
SFI(T) = (Solid_fat / Total_fat) × 100
```
Misura la percentuale di grasso solido a temperatura data.

### 2. Melting Point Effect on Spread
```
Spread ∝ 1/T_melt
```
Low T_melt → early spreading → bigger cookies

### 3. Crystallization Kinetics
```
X(t) = X_max × (1 - exp(-k_c × t))
```
Dove X = crystalline fraction

---

## Parametri per Categoria

### Fat Types

| Grasso | T_melt (°C) | SFI @ 20°C | Effetto su Spread |
|--------|-------------|------------|-------------------|
| Butter | 32-35 | 20-30% | Alto |
| Margarine | 33-38 | 25-35% | Alto |
| Lard | 36-42 | 40-50% | Medio |
| Shortening | 45-55 | 60-70% | Basso |
| Coconut oil | 24-26 | 0-10% | Alto |
| Vegetable oil | <0 | 0% | N/A |

### Crystal Forms
- **α** (alpha): instabile, basso punto di fusione
- **β'** (beta-prime): desiderabile per creaming
- **β** (beta): stabile, alto punto di fusione

---

## Equazioni di Validazione

### Cookie Spread
```python
def predict_spread(fat_type):
    melt_points = {
        'butter': 33,
        'margarine': 35,
        'lard': 38,
        'shortening': 50
    }
    T_melt = melt_points.get(fat_type, 40)
    spread_factor = 5.0 - 0.05 * (T_melt - 30)  # inverse relationship
    return clamp(spread_factor, 2.0, 5.0)
```

---

## Validazione Sistema

Per validare ricette con grassi:
1. Verificare tipo grasso: butter vs shortening
2. Stimare effect su spread: butter → more spread
3. kcal: butter=717, shortening≈880 kcal/100g

---