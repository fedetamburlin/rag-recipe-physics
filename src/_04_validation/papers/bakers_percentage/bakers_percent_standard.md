# Baker's Percentages - Standard Formulas

**Sources (con PDF)**:
- Noal, S. et al. (2016). "Current status of salt reduction in bread and bakery products." *Journal of Cereal Science*, 72, 1-9. PDF: Salt_reduction_2016_bread.pdf

---

---

## Formule Chiave

### Definizione Base
```
Baker's % = (Weight of ingredient / Weight of flour) × 100
```

### Total Formula Percentage
```
Total % = Σ(Baker's %)  (sarà > 100%)
```

### Conversione True Percent → Baker's Percent
```
Baker's % = (True % × 100) / (100 - Other_ingredients_sum%)
```

---

## Standard Formulas per Categoria

### Pane (Bread)

| Ingrediente | Range (%) | Tipico (%) |
|-------------|-----------|------------|
| Farina | 100 | 100 |
| Acqua (Hydration) | 55-80 | 65 |
| Sale | 1.5-2.2 | 2 |
| Lievito | 0.5-2 | 1 |
| Zucchero | 0-10 | 5 |
| Grasso | 0-5 | 2 |

### Brioche (Enriched Bread)

| Ingrediente | Tipico (%) |
|------------|------------|
| Farina | 100 |
| Acqua | 50-60 |
| Uova | 20-40 |
| Zucchero | 10-20 |
| Burro | 20-50 |
| Lievito | 2-3 |
| Sale | 1.5-2 |

### Croissant/Puff

| Ingrediente | Tipico (%) |
|------------|------------|
| Farina | 100 |
| Acqua | 55-65 |
| Burro (in pasta) | 50-80 |
| Sale | 1.5-2 |
| Zucchero | 8-15 |
| Lievito | 2-3 |

### Butter Cake

| Ingrediente | Tipico (%) |
|------------|------------|
| Farina | 100 |
| Zucchero | 80-100 |
| Burro | 50-100 |
| Uova | 50-100 |
| Latte | 30-50 |
| Lievito | 0-3 |

### Cookies (Drop)

| Ingrediente | Tipico (%) |
|------------|------------|
| Farina | 100 |
| Zucchero | 50-80 |
| Burro | 50-80 |
| Uova | 20-40 |
| Latte/Liquido | 10-20 |

### Pie Crust

| Ingrediente | Tipico (%) |
|------------|------------|
| Farina | 100 |
| Burro/Shortening | 50-66 |
| Acqua | 15-25 |
| Sale | 1-2 |

---

## Validazione Sistema

Per validare ricette generate:
```python
def validate_bakers_percent(ingredients: dict, category: str) -> dict:
    """
    ingredients: {'flour': weight, 'sugar': weight, ...}
    Returns: {status, deviations}
    """
    flour = ingredients.get('flour', 0)
    if flour == 0:
        return {'status': 'error', 'message': 'No flour found'}
    
    # Calcola baker's %
    bakers = {k: (v/flour)*100 for k, v in ingredients.items()}
    
    # Valida contro ranges attesi per categoria
    # ...
```

---

## Equazioni di Conversione

### Da Ingredienti a kcal (approccio fisico)
```
Energy = Σ(m_i × E_i)
```
Dove E_i = kcal per grammo ingrediente

### Approx kcal/100g da composition:
```
kcal ≈ 4×(protein + carb) + 9×fat
```
(Atwater formula)

---

## Note

1. Farina = 100% è il riferimento base
2. Total formula > 100% perché include ingredienti oltre la farina
3. Hydration (acqua/farina) è il parametro più critico per texture
4. Per torte: sugar può superare 100% (high-ratio cakes)

---