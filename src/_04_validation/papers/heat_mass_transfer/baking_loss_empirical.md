# Baking Loss and Weight Loss in Bakery Products

**Sources (con PDF)**:
- Holding, D. et al. (2020). "Toasting: Breakfast Cereals and How They Are Made." PDF: Toasting_2020_cereals.pdf

---

## Formule Chiave Estratte

### 1. Baking Loss Definition
```
BL(%) = (m_dough - m_baked) / m_dough × 100
```

### 2. Dough Yield
```
DY(%) = m_dough / m_flour × 100
```

### 3. Baked Goods Yield
```
BGY(%) = m_baked / m_flour × 100
```

### 4. Relazione
```
BGY = DY × (100 - BL) / 100
```

---

## Tabella Valori Tipici

### Pane

| Prodotto | Baking Loss (%) | Note |
|----------|-----------------|------|
| Pane piccolo (<200g) | 15-20% | Alta superficie |
| Pane medio (200-500g) | 12-15% | |
| Pane grande (>500g) | 8-12% | Minor superficie |
| Baguette | 12-16% | |
| Ciabatta | 10-14% | |

### Torte

| Prodotto | Baking Loss (%) |
|----------|-----------------|
| Torta900g | 10-15% |
| Muffins | 12-18% |
| Sponge cake | 15-22% |

### Pastry

| Prodotto | Baking Loss (%) |
|----------|-----------------|
| Croissant | 12-18% |
| Puff pastry | 10-15% |
| Pie crust | 8-12% |

### Biscotti

| Prodotto | Baking Loss (%) |
|----------|-----------------|
| Drop cookies | 5-10% |
| Rolled cookies | 8-12% |
| Biscotti secchi | 3-6% |

---

## Fisica della Perdita di Peso

### Meccanismi
1. **Evaporazione acqua**: Q = m × L_v (L_v = 2260 kJ/kg)
2. **Perdita CO2**: durante lievitazione
3. **Vaporizzazione alcoli**: minima quantità

### Modello Semplificato
```
m_loss ≈ V_product × (ρ_dough - ρ_baked) × loss_factor
```

### Heat-Mass Transfer
```
dM/dt = -h_m × A × (p_v - p_∞)
```
Dove:
- h_m = mass transfer coefficient
- A = superficie
- p_v = vapor pressure at surface
- p_∞ = vapor pressure in oven

---

## Validazione Sistema

Per validare ricette generate:
```python
def validate_weight_loss(product_type, initial_weight, final_weight):
    """Validate weight loss is within expected range"""
    loss_pct = (initial_weight - final_weight) / initial_weight * 100
    
    ranges = {
        'bread_small': (15, 20),
        'bread_large': (8, 12),
        'cake': (10, 15),
        'croissant': (12, 18),
        'cookie': (5, 10)
    }
    
    expected = ranges.get(product_type, (8, 15))
    return expected[0] <= loss_pct <= expected[1]
```

---

## Note Pratiche

1. **Dimensione**: Prodotti più piccoli → maggiore perdita %
2. **Temperatura**: Alta T → maggiore perdita
3. **Tempo**: Più lungo → maggiore perdita
4. **Umidità iniziale**: Più umido → maggiore perdita
5. **Tipo forno**: Convezione > statico per perdita

---