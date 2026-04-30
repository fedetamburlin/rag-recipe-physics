# Miller 1997 - Elongational Viscosity and Cookie Diameter

## Key Formulas

### Gordonier Equation (cookie spread prediction)
```
D = K * (η_E / γ)^(1/3) * (ρ/V)^(1/3) * H^(1/3)
```
- D: cookie diameter
- K: shape constant (~2.4 for circular cookies)
- η_E: elongational viscosity
- γ: strain rate (s⁻¹)
- ρ: batter density (kg/m³)
- V: drop volume (m³)
- H: cookie height (m)

### Elongational Viscosity Model
```
η_E = η_0 * (1 + λ * c)^n
```
- η_0: zero-shear viscosity of flour-water system
- λ: fat droplets per unit volume
- c: fat concentration (wt%)
- n: flow behavior index (~0.7 for fats)

### Sparkes-Creek Formula Correction
```
η_E = A * exp(B/T) * exp(C * σ)
```
- A, B, C: material constants
- T: temperature (K)
- σ: stress (Pa)

## Heuristics for Recipe Validation

### Fat Content Effects
| Fat Level | Expected η_E | Spread Ratio |
|----------|--------------|-------------|
| 0% | Low | 1.0 |
| 50% butter | Medium | 1.3 |
| 100% shortening | High | 1.6 |

### Temperature Dependence
- Every 10°C increase: η_E decreases ~15%
- Optimal baking: 180-200°C (fat melts and spreads before setting)

### Key Validations
1. **Spread ratio**: Calculate D_final/D_initial; should be 2.0-3.5 for typical cookies
2. **Fat melting**: Ensure fats melt below cookie setting temperature (~100°C)
3. **Viscosity ratio**: η_E(fat)/η_E(flour) should be 0.3-0.7 for good spread