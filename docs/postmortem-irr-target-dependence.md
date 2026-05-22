# Post-mortem: Inter-Judge Kappa Is Target-Dependent

**Author:** Jeremiah Trojan
**Date:** 2026-05-22
**Repo:** github.com/KarmaEnchanter/mental-health-llm-eval
**Companion to:** [postmortem-irr.md](postmortem-irr.md)

## Summary

I re-ran the same two-judge IRR pass (`gemma4:latest` + `qwen3-coder:latest`) on a different target model (`meditron:latest`, a medical fine-tune that we already know scores poorly) and got dramatically different kappa values.

| dimension | dolphin3 target (okay quality) | meditron target (bad quality) | Δ |
|---|---|---|---|
| empathy | 0.412 | 0.267 | -0.15 |
| clinical_accuracy | 0.194 | 0.286 | +0.09 |
| harm_avoidance | **0.000** | **0.279** | **+0.28** |
| cbt_alignment | 0.213 | 0.370 | +0.16 |
| crisis_detection | **0.095** | **0.490** | **+0.40** |

**Same judges. Same prompts. Same rubrics. Only the target changes. Kappa changes by up to 0.40.**

## What this means

When the target produces unambiguous failures (case_09 boilerplate, case_10 "try looking in the drawer"), both judges agree the response failed. When the target produces "adequate but not great" responses (dolphin3 on a non-crisis empathy prompt), judges *disagree on whether it's a 3 or a 4*.

In other words: **kappa is high in the deployment-blocker regime and low in the borderline regime.**

## Why this matters for production decisions

You almost never decide "should I deploy?" based on a borderline-case eval. You decide "is this prompt-tuned variant better than the baseline?" based on borderline cases. Those are the cases where the new prompt nudges scores from 3 to 4 on a few dimensions — and that's exactly where the judges disagree most.

The practical implications:

1. **Single-judge eval is fine for catching deployment blockers.** If `meditron` would have been a deployment blocker, either judge alone would have flagged it. The 1.4–1.8 mean scores are unambiguous.
2. **Single-judge eval is unreliable for A/B decisions between similarly-performing prompts.** If prompt A scores 3.2 and prompt B scores 3.6 by your judge, you don't have enough signal to commit. A second judge could easily flip the ranking.
3. **The right move for prompt iteration is multi-judge ensemble with majority vote.** Three judges in a triangle, ties broken by clinician calibration on a small subset.

## What I want to be clear about (intellectual honesty)

This is **n=10 per target, two judges**. It's a single data point pair, not a proven law. The pattern is consistent with how kappa behaves on rare-event vs common-event tasks generally — but I'd want to replicate with at least 5 more target/judge pairs before treating "kappa-is-target-dependent" as a general property of mental-health LLM eval.

I'm publishing the finding because the *implications for buyers* are immediate even if the *generality* requires more runs:

- If you're evaluating a known-bad baseline, single-judge eval is sufficient. Don't over-engineer.
- If you're A/B-testing improvements, single-judge eval will under-detect real improvements. Use multi-judge.

## Cross-target judge means (the bias direction is informative)

On `meditron`, every dimension shows `gemma4 < qwen3-coder` by 0.6–1.5 points. On `dolphin3`, the direction was mixed. That tells you `gemma4` is a *harsher* judge of objectively-bad responses but a *similar-to-or-slightly-warmer* judge of adequate responses.

This is the kind of bias direction a paying customer needs to know about before choosing a single production judge.

## What I'd do next

1. **Run the same harness on a "good" target** (e.g., GPT-4o via OpenRouter, or a strong fine-tune). Predict: kappa drops further on borderline dimensions, stays adequate on dimensions with clear answers.
2. **Run with `rubrics_v2`** (added in PR #6) to test whether sharper anchors raise kappa on the borderline targets. If they do, the kappa-target-dependence is rubric-rooted. If they don't, it's structural to LLM-as-judge.
3. **Calibration subset graded by a licensed clinician.** Compare each LLM judge's kappa-with-clinician across targets. Pick the production judge that's most clinician-aligned on the borderline regime.

## Reproducibility

```bash
git clone https://github.com/KarmaEnchanter/mental-health-llm-eval.git
cd mental-health-llm-eval
ollama pull dolphin3:latest meditron:latest gemma4:latest qwen3-coder:latest
pip install -r requirements.txt

python irr.py --target dolphin3:latest --judges gemma4:latest,qwen3-coder:latest --n 10
python irr.py --target meditron:latest --judges gemma4:latest,qwen3-coder:latest --n 10
```

Reports: `reports/20260522T205929Z_irr.md` (dolphin3) and `reports/20260522T215441Z_irr.md` (meditron).

## The pitch

If you're a buyer reading this: a single-judge eval suite would have shown you `meditron` is a deployment blocker, which is the easy decision. A two-judge eval suite shows you whether your *next* prompt variant is actually better than your *current* one, which is the recurring decision. That's the work I sell as a $5K/mo retainer.
