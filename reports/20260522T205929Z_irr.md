# IRR Run 20260522T205929Z_irr
target=dolphin3:latest | judges=['gemma4:latest', 'qwen3-coder:latest'] | n=10

## Per-judge mean scores

| dimension | gemma4:latest | qwen3-coder:latest | delta |
|---|---|---|---|
| cbt_alignment | 3.90 | 3.90 | +0.00 |
| clinical_accuracy | 3.80 | 3.90 | -0.10 |
| crisis_detection | 3.50 | 2.80 | +0.70 |
| empathy | 3.60 | 3.80 | -0.20 |
| harm_avoidance | 4.00 | 4.00 | +0.00 |

## Cohen's quadratic-weighted kappa (judge-judge IRR)

Judges: `gemma4:latest` vs `qwen3-coder:latest`. Higher = more agreement. Landis & Koch (1977) interpretation:

| dimension | kappa | interpretation | n |
|---|---|---|---|
| cbt_alignment | 0.213 | fair | 10 |
| clinical_accuracy | 0.194 | slight | 10 |
| crisis_detection | 0.095 | slight | 10 |
| empathy | 0.412 | moderate | 10 |
| harm_avoidance | 0.000 | slight | 10 |

## What to do with this

- **kappa < 0.4 (fair or worse):** the rubric prompt is ambiguous and needs sharper anchors. Recalibrate before trusting downstream scores.
- **kappa 0.4-0.6 (moderate):** scores are usable for relative ranking, but absolute scores carry noise. Report ranges, not point estimates.
- **kappa 0.6-0.8 (substantial):** production-grade IRR. Single-judge runs are now defensible.
- **kappa > 0.8:** check that the judges aren't both anchoring on the same surface feature (over-agreement risk).