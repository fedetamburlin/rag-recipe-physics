# Protein Denaturation in Wheat Dough - Physics and Chemistry

**Sources (con PDF)**:
- Cho, S.W. et al. (2021). "Thermally induced gluten modification observed with rheology and spectroscopies." *International Journal of Biological Macromolecules*, 167, 1319-1330. PDF: Cho_2021_gluten_denaturation.pdf

---

## Formule Chiave

### 1. Temperatura Denaturazione Glutine
```
T_den = 79-81°C (complete denaturation)
T_initial = 56-64°C (structural changes start)
```

### 2. Solubilità Proteica vs Temperatura
```
S(T) = S_0 × exp(-α·T)
```
Dove S diminuisce da 68% a 0% tra 80-135°C

### 3. Reologia - Modulo Elastico
```
G'(T) = G'_0 × (1 + β·exp(T/T_1))
```
G' aumenta con temperatura per aggregazione

---

## Parametri Sperimentali

### Denaturazione Glutine (wheat)

| Fase | Temperatura |的变化 |
|------|-------------|---------|
| Iniziale | 56-64°C | Primi cambiamenti strutturali |
| Denaturazione completa | 79-81°C | Perdita completa funzionalità reologica |
| Aggregazione termica | 108-116°C | Reazioni termosetting |
| Decomposizione | >170°C | Perdita di massa, decarbonilazione |

### Solubilità SDS 2%
```
T=80°C: 68%
T=100°C: 30%
T=135°C: 0%
```

---

## Modello di Formazione Rete Glutenica

### During Mixing
```
Glutenin + Gliadin → Network
H-bonds + Disulfide → Cross-links
```

### During Baking
```
Step 1: 25-56°C - Hydration
Step 2: 56-64°C - Conformational change
Step 3: 64-79°C - Initial denaturation  
Step 4: 79-81°C - Complete denaturation
Step 5: >81°C - Aggregation, thermosetting
```

---

## Equazioni per Validazione

### Densità Network
```
ρ_network = ρ_0 × (1 + γ·exp(-t/τ))
```
Dove t = tempo di lievitazione

### Rigidezza
```
E(T) = E_0 + a·T + b·T²
```
Per T < 80°C: a>0 (aumento), per T>80°C: change

---

## Validazione Sistema

Per validare ricette:
1. Verificare che temperature di baking > 79°C (denaturazione completa)
2. Stimare sviluppo glutine da mixing/time
3. Temperature probe: 
   - Core > 95°C per pane
   - Surface > 150°C per crosta

---