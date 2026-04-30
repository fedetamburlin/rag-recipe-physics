# Toasting Physics - Breakfast Cereals and Bakery Products

**Sources (con PDF)**:
- Breslin, J.C. & Knott, K. (2020). "Toasting." In *Breakfast Cereals and How They Are Made* (4th ed.), Chapter 15, pp. 299-320. PDF: Toasting_2020_cereals.pdf

---

## Formule Chiave

### 1. Maillard Reaction Activation
```
T_surface > 120°C → Maillard starts
T_surface > 150°C → Caramelization + rapid browning
T_optimal = 140-160°C for controlled Maillard
```

### 2. Energy Balance during Toasting
```
Total Energy = E_dry_mass + E_water_heating + E_evaporation + E_Maillard
```
Phase distribution:
- **Heating phase**: 49% dry mass, 49% water heating, 2% evaporation
- **Constant rate drying**: 17% dry mass, 9% water, 73% evaporation
- **Falling rate**: 27% dry mass, 60% water, 11% evaporation
- **Toasting phase**: 44% dry mass, 46% Maillard, 9% evaporation

### 3. Critical Moisture Content
```
M_critical = 10-12% (wet basis)
```
- Below M_critical: product temperature rises rapidly
- Above M_critical: temperature limited by evaporation cooling

### 4. Glass Transition during Toasting
```
T_g = T_g0 - k * M
```
- T_g: glass transition temperature
- T_g0: T_g of dry material (~150-180°C for starch)
- M: moisture content (%)
- k: ~2-3°C per % moisture

---

## Parametri per Fase di Tostatura

### Four-Phase Toasting Process

| Phase | Moisture Range | Temperature | Key Events |
|-------|---------------|-------------|------------|
| 1. Heat-up | >12% | Rising to 100°C | Energy absorption, water heating |
| 2. Constant rate drying | 8-12% | ~100°C | Surface evaporation, cooling |
| 3. Falling rate drying | 4-8% | 100-120°C | Internal moisture diffusion limited |
| 4. Toasting/color | <4% | >120°C | Maillard, caramelization, expansion |

### Expansion/Puffing
```
T > 105°C + M ~ 6-8% → Steam pressure builds
P_steam > P_starch_matrix → Expansion
```
- Expansion time: <10 seconds
- Moisture drop during puffing: 10.5% → 6.5%

---

## Maillard and Caramelization Kinetics

### Reaction Rate Approximation
```
Rate = A * exp(-Ea / RT) * [Reducing Sugar]^m * [Amino Acid]^n
```
- Ea (Maillard): ~80-120 kJ/mol
- Ea (Caramelization): ~120-160 kJ/mol
- Temperature sensitivity: rate doubles every 10°C

### Color Development
```
L* (lightness) = L0 - k_color * t * exp(-Ea_color / RT)
```
- L0: initial lightness
- k_color: color formation rate constant
- Uniform color requires: controlled T_profile + consistent moisture

---

## Equazioni di Validazione

### Predict Surface Temperature
```python
def predict_surface_temp(t, oven_temp_C, initial_moisture, airflow):
    """
    t: time (min)
    oven_temp_C: oven temperature
    initial_moisture: % wet basis
    airflow: m/s
    """
    if initial_moisture > 12:
        # Constant rate period - limited by evaporation
        return min(100, oven_temp_C * 0.6)
    elif initial_moisture > 4:
        # Falling rate
        return 100 + (oven_temp_C - 100) * (12 - initial_moisture) / 8
    else:
        # Toasting phase
        return oven_temp_C * 0.85
```

### Predict Weight Loss
```python
def weight_loss(initial_moisture, target_moisture, dry_mass):
    """
    Returns total water lost (g)
    """
    initial_water = dry_mass * initial_moisture / (100 - initial_moisture)
    final_water = dry_mass * target_moisture / (100 - target_moisture)
    return initial_water - final_water
```

### Maillard Control Check
```python
def maillard_risk(surface_temp_C, time_min, moisture_pct):
    """
    Returns risk level for over-browning/burning
    """
    if surface_temp_C < 120 or moisture_pct > 8:
        return "low", "insufficient browning"
    
    maillard_index = (surface_temp_C - 120) * time_min / moisture_pct
    
    if maillard_index < 50:
        return "low", "light color"
    elif maillard_index < 150:
        return "medium", "golden brown"
    elif maillard_index < 300:
        return "high", "dark brown"
    else:
        return "critical", "burnt/bitter"
```

---

## Validazione Sistema

Per validare ricette di cottura/toasting:
1. **Temperature core**: >95°C per sicurezza alimentare
2. **Surface temperature**: 120-160°C per Maillard ottimale
3. **Moisture final**: 1-4% per croccantezza, >8% per morbidezza
4. **Weight loss**: tipicamente 10-20% del peso iniziale
5. **Expansion**: richiede M = 6-10% + T > 105°C rapidamente
6. **Color uniformity**: ±5% L* variazione accettabile

---