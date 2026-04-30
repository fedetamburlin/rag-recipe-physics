# Validation Papers - Summary Table

## Panoramica

| # | Paper | PDF | MD | Categoria | Utilità | Difficoltà |
|---|-------|-----|----|-----------|---------|------------|
| 1 | **Miller_1997_elongational_viscosity** | ✅ | ✅ | cookie_science | Gordonier equation per cookie spread | ★★☆ |
| 2 | **Fatty_acids_cookie_2017** | ✅ | ✅ | cookie_science | Effetto composizione acidi grassi su texture cookie | ★★☆ |
| 3 | **Fats_oils_cookie_review_2016** | ✅ | ✅ | cookie_science | Review generale grassi nei cookie | ★★☆ |
| 4 | **Milk_fat_2018_structure** | ✅ | ✅ | chemistry | Avrami crystallization, SFC profiles | ★★☆ |
| 5 | **fat_crystallization** | - | ✅ | chemistry | SFI, polymorphism, melting point effects | ★★☆ |
| 6 | **Salt_reduction_2016_bread** | ✅ | ✅ | bakers_percentage | Effetto sale su dough, replacers, sourdough | ★☆☆ |
| 7 | **bakers_percent_standard** | - | ✅ | bakers_percentage | Standard ratios per categoria | ★☆☆ |
| 8 | **baking_loss_empirical** | - | ✅ | heat_mass_transfer | Weight loss % durante baking | ★☆☆ |
| 9 | **Toasting_2020_cereals** | ✅ | ✅ | heat_mass_transfer | Fasi toasting, Maillard, energy balance | ★★☆ |
| 10 | **Puff_pastry_fat_reduction_2015** | ✅ | ✅ | lamination_physics | Lift mechanism, lamination, fat reduction | ★★★ |
| 11 | **starch_gelatinization_review** | ✅ | ✅ | starch_gelatinization | DSC, kinetics, ingredient effects | ★★★ |
| 12 | **gluten_denaturation** | - | ✅ | protein_chemistry | Temperature denaturazione, rete glutenica | ★★★ |
| 13 | **Masi_2023_pizza_leavening** | ✅ | ✅ | pizza_chemistry | Volume kinetics, 48h leavening, SEM | ★★★ |
| 14 | **Giovanelli_2024_pizza_quality** | ✅ | ✅ | pizza_chemistry | HiT baking, acrylamide, HMF, color | ★★☆ |
| 15 | **Almeida_2018_pizza_soy_fiber** | ✅ | ✅ | pizza_chemistry | Pizza arricchita, rheology, nutrition | ★★☆ |
| 16 | **pizza_physics** | - | ✅ | pizza_chemistry | Flour requirements, fermentation | ★★☆ |

---

## PDF Eliminati (contenuto non pertinente)

| Nome file originale | Contenuto reale | Azione |
|---------------------|-----------------|--------|
| Bot_2021_fat_crystallization.pdf | Packaging nanocomposite (thermal buffering) | ❌ Eliminato |
| Cake_batter_rheology_2011.pdf | Fish freshness sensor array | ❌ Eliminato |
| Cake_sugar_reduction_2022.pdf | Chitosan copper corrosion | ❌ Eliminato |
| Fat_type_cookie_2007.pdf | Freeze-dried space yogurt | ❌ Eliminato |
| Rask_1989_thermal_properties.pdf | Aerosol science | ❌ Eliminato |
| Leonardi_2005_pizza_yeast_fermentation.pdf | Sesame meal moisture sorption | ❌ Eliminato |
| Dough_bread_rheology_2006.pdf | Bacillus stearothermophilus growth | ❌ Eliminato |
| Cake_batter_heat_treatment_2011.pdf | Frozen bread dough weight loss | ❌ Eliminato |
| Laminated_dough_layers_2014.pdf | PEF egg white proteins | ❌ Eliminato |
| Cho_2021_gluten_denaturation.pdf | Lignin mango seed husk extraction | ❌ Eliminato |

---

## Priorità Implementazione

### Fase 1 (Immediata) - Difficoltà ★☆☆
- bakers_percent_standard (confronto ratios)
- Salt_reduction_2016_bread (validazione sale)
- baking_loss_empirical (weight loss)

### Fase 2 (Breve termine) - Difficoltà ★★☆
- Miller_1997_elongational_viscosity (cookie spread)
- Fatty_acids_cookie_2017 (dough texture)
- Milk_fat_2018_structure (SFC/profiles)
- fat_crystallization (spread validation)
- Toasting_2020_cereals (Maillard/color)
- Giovanelli_2024_pizza_quality (baking temp)
- Almeida_2018_pizza_soy_fiber (enriched dough)

### Fase 3 (Medio termine) - Difficoltà ★★★
- starch_gelatinization_review (structure)
- gluten_denaturation (protein network)
- Masi_2023_pizza_leavening (leavening model)
- Puff_pastry_fat_reduction_2015 (laminated pastry)

---

## Mappa File

```
papers/
├── README.md (questo file)
├── PAPERS_STATUS.md
├── inventory.json
├── bakers_percentage/
│   ├── bakers_percent_standard.md
│   └── Salt_reduction_2016_bread.md
├── chemistry/
│   ├── fat_crystallization.md
│   └── Milk_fat_2018_structure.md
├── cookie_science/
│   ├── Miller_1997_elongational_viscosity.md
│   ├── Fatty_acids_cookie_2017.md
│   └── Fats_oils_cookie_review_2016.md
├── heat_mass_transfer/
│   ├── baking_loss_empirical.md
│   └── Toasting_2020_cereals.md
├── lamination_physics/
│   └── Puff_pastry_fat_reduction_2015.md
├── pizza_chemistry/
│   ├── pizza_physics.md
│   ├── Masi_2023_pizza_leavening.md
│   ├── Giovanelli_2024_pizza_quality.md
│   └── Almeida_2018_pizza_soy_fiber.md
├── protein_chemistry/
│   └── gluten_denaturation.md
└── starch_gelatinization/
    └── starch_gelatinization_review.md
```