# Feature Extraction Formulas

Features computed from **USDA nutrients** + **ingredient percentages** + **basic mixing rules**.

## Direct USDA Nutrients (per 100g)

| Feature | Source |
|---------|--------|
| `water_g` | `nutrition["WATER"]["amount"]` |
| `protein_g` | `nutrition["PROTEIN"]["amount"]` |
| `fat_g` | `nutrition["FAT"]["amount"]` |
| `carbs_g` | `nutrition["CARB"]["amount"]` |
| `sodium_mg` | `nutrition["NA"]["amount"]` |
| `energy_kcal` | `nutrition["ENERGY"]["amount"]` |

## Derived Features

### `hydration_bakers`
```
hydration_bakers = (water_pct / flour_pct) * 100
```
- `water_pct`: sum of ingredient percentages matching `water`, `acqua`, `milk`, `latte`, `yogurt`, `buttermilk`, `cream`
- `flour_pct`: sum of ingredient percentages matching `flour`, `farina`, `semola`, `manitoba`
- If `flour_pct == 0`: returns `0.0`

### `density_kg_m3`
Mixing rule from macronutrient mass fractions:
```
w_norm = water_g / (water_g + protein_g + fat_g + carbs_g)
p_norm = protein_g / total
f_norm = fat_g / total
c_norm = carbs_g / total

density = w_norm*1000 + p_norm*1300 + f_norm*900 + c_norm*550
```

### `thermal_diffusivity`
```
cp     = w_norm*4186 + p_norm*2000 + f_norm*2000 + c_norm*1700   [J/kg*K]
k      = w_norm*0.60 + p_norm*0.20 + f_norm*0.15 + c_norm*0.10   [W/m*K]
alpha  = (k / (density * cp)) * 1e6                               [mm2/s]
```

### `taxonomy_encoded`
Lookup table:
```
leavened=0, whipped=1, doughs=2, preserves=3,
creams=4, meats=5, seafood=6, other=7
```

## Thermal Properties Used

| Component | ρ (kg/m3) | cp (J/kg*K) | k (W/m*K) |
|-----------|-----------|-------------|-----------|
| Water     | 1000      | 4186        | 0.60      |
| Protein   | 1300      | 2000        | 0.20      |
| Fat       | 900       | 2000        | 0.15      |
| Carbs     | 550       | 1700        | 0.10      |
