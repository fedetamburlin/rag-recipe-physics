# USDA Nutrition Database

## Schema

| Table | Description |
|-------|-------------|
| `nutrient_codes` | 44 nutrient codes with display names and units |
| `nutrients` | USDA nutrient IDs mapped to codes |
| `foods` | ~19k foods after deduplication |
| `food_nutrients` | Nutrient values per food |
| `ingest_log` | Operations log for traceability |

## Filtering Pipeline

### 1. Nutrient Selection (44 codes)

Only nutrients present in actual food data are included:
- **Macronutrienti**: ENERGY, PROTEIN, CARB, FAT, FIBER, WATER, SUGAR
- **Carboidrati**: SUCROSE, GLUCOSE, FRUCTOSE, LACTOSE, MALTOSE
- **Vitamine**: VITA_RAE, VITB12, VITB6, BIOTIN, CHOLINE, FOLATE, NIACIN, PANTOTHENIC, RIBOFLAVIN, THIAMIN, VITC, VITD, VITE, VITK, BETA_CAROTENE, LYCOPENE
- **Minerali**: CA, FE, K, MG, NA, P, ZN, CU, MN, SE, I, MO, F
- **Altro**: CAFFEINE, CHOLESTEROL, MONO_FAT

**Esclusi** (dati assenti): ALCOHOL, ASH, CR, LUTEIN, OMEGA3, OMEGA6, POLY_FAT, SAT_FAT, STARCH, TRANS_FAT

### 2. Deduplicazione

Per ogni gruppo di alimenti con descrizione identica:
1. Ordina per **completezza macronutrienti** (3+ > 2 > 1)
2. A parità, preferisci **nome più corto** (più generico)
3. Elimina i duplicati meno completi

**Risultato**: 66.420 duplicati rimossi

### 3. Calcolo ENERGY

Per foods con PROTEIN + CARB + FAT ma senza ENERGY:
```
ENERGY_KCAL = PROTEIN * 4 + CARB * 4 + FAT * 9
```

**Risultato**: 2.105 ENERGY calcolati

## Statistiche Finali

| Metrica | Valore |
|---------|--------|
| Foods totali | 19.399 |
| Con ENERGY | 9.939 (51%) |
| Con 4+ macronutrienti | 8.030 (41%) |
| food_nutrients | 279.114 |

## Uso

```python
from src.nutrition import calculate_recipe_nutrients, IngredientMatcher

# Match ingredients to USDA foods
matcher = IngredientMatcher()
matched = matcher.match_ingredients(['butter', 'flour', 'sugar'])

# Calculate nutrition
result = calculate_recipe_nutrients(['butter', 'flour', 'sugar'], matched)
# {'ENERGY': {'amount': 1156.3, 'unit': 'KCAL'}, ...}
```