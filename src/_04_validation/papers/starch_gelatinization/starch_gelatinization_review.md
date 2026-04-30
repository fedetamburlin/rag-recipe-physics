# Starch Gelatinization - Physics and Kinetics

**Sources (con PDF)**:
- Li, C. et al. (2022). "Recent progress in understanding starch gelatinization." *Carbohydrate Polymers*, 293, 119735. PDF: Li_2022_starch_gelatinization.pdf

---

## Formule Chiave Estratte

### 1. Degree of Gelatinization (DSG)
```
DSG(%) = (1 - ΔH_sample / ΔH_native) × 100%
```
Dove:
- ΔH_sample = enthalpy measured after treatment
- ΔH_native = enthalpy of native starch (J/g)

### 2. Arrhenius Model for Gelatinization Kinetics
```
k = k_0 · exp(-Ea / (R·T))
```
Parametri per wheat starch:
- k_0 = 2.8 × 10¹⁸ s⁻¹
- Ea = 139 kJ/mol
- T range: 60-90°C

### 3. Temperature-Dependent Enthalpy
```
ΔH(T) = ΔH_0 · exp(-α/T)
```
Dove ΔH diminuisce con T per gelatinizzazione parziale

---

## Parametri Termici

### Tabella: Temperature di Gelatinizzazione (DSC)

| Amido | T_onset (°C) | T_peak (°C) | T_end (°C) | ΔH (J/g) |
|-------|--------------|-------------|------------|----------|
| Wheat | 55-60 | 60-65 | 70-75 | 10-15 |
| Corn | 60-65 | 65-70 | 75-80 | 12-18 |
| Potato | 50-55 | 58-62 | 65-70 | 14-20 |
| Rice | 55-65 | 65-75 | 75-85 | 8-14 |

### Per Baker's Percent (flour = 100%)
- Gelatinizzazione completa: ~60-70% acqua (baker's)

---

## Modello Fisico

### Swelling Kinetics (Granule)
```
V(t) / V_0 = 1 + k_s·t·exp(-Ea/RT)
```
Dove:
- V(t) = volume granulo al tempo t
- V_0 = volume iniziale
- k_s = swelling rate constant

### Water Absorption
```
w(t) = w_∞ · (1 - exp(-k_w·t))
```
Dove w_∞ = water absorption max

---

## Effetti degli Ingredienti

### Zuccheri
- Aumentano T_gelatinizzazione
- Saccharosi > Glucosio > Fruttosio
- Effetto: 5-10°C di incremento

### Grassi
- Formano complessi con amilosio
- Ritardano gelatinizzazione
- Stabilizzano struttura

### Proteine
- Competono per acqua
- Possono ritardare gelatinizzazione
- Effetto dipende da concentrazione

---

## Validazione Sistema

Per validare ricette:
1. Verificare idratazione (water/flour ratio):
   - Bread: 60-75% → full gelatinization
   - Cake: 35-50% → partial gelatinization
   - Cookie: 15-25% → minimal gelatinization

2. Stimare T_gel da ingredienti:
   ```python
   T_gel_adjusted = T_gel_base + ΔT_sugar + ΔT_fat
   ```

3. Calcolare DSG atteso:
   - High hydration + long bake → high DSG
   - Low hydration + short bake → low DSG

---