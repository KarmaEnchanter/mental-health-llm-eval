# Post-mortem: Rubrics v2 Didn't Work, And Here's What That Means

**Author:** Jeremiah Trojan
**Date:** 2026-05-22
**Repo:** github.com/KarmaEnchanter/mental-health-llm-eval
**Companion to:** [postmortem-irr.md](postmortem-irr.md), [postmortem-irr-target-dependence.md](postmortem-irr-target-dependence.md)

## Summary

I ran the same 2-judge IRR test (`dolphin3` target, `gemma4` + `qwen3-coder` judges, n=10) with two rubric sets — the original v1 (generic per-score anchors) and the new v2 (per-dimension sharper anchors). Hypothesis: v2's sharper anchors should raise kappa by spreading the score distribution.

**Result: hypothesis refuted.**

| dimension | v1 kappa | v2 kappa | direction |
|---|---|---|---|
| empathy | 0.412 | **0.000** | DROPPED |
| clinical_accuracy | 0.194 | **0.342** | improved |
| harm_avoidance | 0.000 | **-0.047** | DROPPED (below chance) |
| cbt_alignment | 0.213 | **0.000** | DROPPED |
| crisis_detection | 0.095 | **0.000** | DROPPED |

Four out of five dimensions got worse. Only `clinical_accuracy` improved.

## What this tells me (the real finding)

The hypothesis was clear: "kappa is low because the rubric anchors are ambiguous; sharper anchors should help." The test was clean: same prompts, same judges, same target, only the rubric prompt changes. The result is unambiguous: sharper anchors did not help; they actively hurt on most dimensions.

The forward inference: **the inter-judge disagreement is structural to LLM-as-judge on these dimensions, not driven by rubric ambiguity.** The judges are responding to surface features (verbosity, register, hedging patterns) that vary independently of the rubric anchors.

My v1 post-mortem said this explicitly as the alternative hypothesis: *"If kappa doesn't improve, the disagreement is structural (judge bias) and the fix is a clinician-graded calibration subset, not a rubric rewrite."* That alternative is now confirmed by the test.

## Why might v2 have made things worse?

Three candidate explanations, in decreasing order of how much evidence supports each:

1. **More anchors = more disagreement surface.** v1 gave judges 1 generic anchor per score level. v2 gave them dimension-specific anchors with explicit active/passive distinctions, examples, and edge cases. More text in the prompt = more places the two judges can interpret a clause differently. With LLM-as-judge, longer rubric prompts are not strictly better.
2. **Mean-score delta widened on 3 of 5 dimensions.** v1 deltas: -0.50 to +0.70. v2 deltas: -1.20 to +0.10. `gemma4` got systematically harsher on v2 across cbt_alignment, empathy, and crisis_detection — likely because the v2 anchors gave it more grounds to score down. `qwen3-coder` didn't follow the same pattern. The asymmetric response to sharper anchors is itself a judge-bias finding.
3. **Low-variance artifact persisted.** harm_avoidance went from kappa=0.000 (both judges score 4) to kappa=-0.047 (both still cluster near 4 with slight crossover). The rubric didn't fail to discriminate — the model's harm-avoidance behavior is just genuinely uniform on a 50-prompt set where most prompts aren't safety-critical edge cases.

## What I'd do next (and what I should NOT do)

**SHOULD NOT do:** Rewrite rubrics_v2 again with even more detail. The hypothesis that rubric refinement helps is now refuted; doing v3 would be ignoring the evidence.

**SHOULD do:**

1. **Calibration subset graded by a licensed clinician.** Hand a clinician 20 prompts + dolphin3's responses. They produce ground-truth scores. Compute kappa between each LLM judge and the clinician. The judge with the highest kappa-against-clinician is the production judge. This is the standard move in clinical eval methodology and the path the v1 post-mortem flagged as the fallback.
2. **Ensemble majority vote with 3+ judges.** Adding a third judge from a third family doesn't fix systematic bias, but it does dilute single-judge errors when bias directions are uncorrelated.
3. **Per-dimension judge selection.** clinical_accuracy improved with v2 — different rubrics may need different judge prompts. There's no rule that says all 5 dimensions need the same anchor style.

## The intellectual-honesty point

The reason I'm publishing this negative finding instead of quietly deleting `rubrics_v2.py` is that the entire point of an eval discipline is that *negative findings are findings*. A consultant who only ships "v2 worked, kappa improved" reports has no signal in the reports. A consultant who ships "I tested v2, hypothesis refuted, here's what the refutation tells us" is doing the discipline as designed.

If you're a paying customer and your engineer comes back with "I added more anchors and the agreement got worse" — that's not a failure of the engineer, that's the eval working as designed. You learned the disagreement is structural; you now know to spend on clinician calibration instead of rubric iteration.

## Reproducibility

```bash
git clone https://github.com/KarmaEnchanter/mental-health-llm-eval.git
cd mental-health-llm-eval
ollama pull dolphin3:latest gemma4:latest qwen3-coder:latest
pip install -r requirements.txt

python irr.py --target dolphin3:latest --judges gemma4:latest,qwen3-coder:latest --n 10
python irr.py --target dolphin3:latest --judges gemma4:latest,qwen3-coder:latest --n 10 --rubrics-v2
```

Reports: `reports/20260522T205929Z_irr.md` (v1) and `reports/20260522T233235Z_irr.md` (v2).

## What this changes for the audit-service pitch

The pitch now has a clean story arc:
- v1 IRR uncovers low kappa on safety rubrics
- I test the obvious hypothesis (sharper rubrics → higher kappa) and publish the refutation
- The remaining hypothesis (structural judge bias) is what I sell calibration-subset clinician-grading engagements to fix

That's a real, defensible service. Not "I'll write you better rubrics" (which I just showed doesn't work) but "I'll set up the clinician-calibration loop that does work, then run it on a continuous schedule." Different scope, different price, different value.
