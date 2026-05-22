# Post-mortem: Why Two LLM Judges Disagree on Safety-Critical Rubrics

**Author:** Jeremiah Trojan
**Date:** 2026-05-22
**Repo:** github.com/KarmaEnchanter/mental-health-llm-eval
**Companion to:** [postmortem-meditron.md](postmortem-meditron.md)

## Summary

I ran 10 mental-health prompts through `dolphin3:latest` (target), scored each response with **two independent judges from different model families** (`gemma4:latest` and `qwen3-coder:latest`), and computed Cohen's quadratic-weighted kappa per rubric dimension. The result:

| dimension | kappa | interpretation |
|---|---|---|
| empathy | **0.412** | moderate |
| cbt_alignment | **0.213** | fair |
| clinical_accuracy | **0.194** | slight |
| crisis_detection | **0.095** | slight (~chance) |
| harm_avoidance | **0.000** | slight (low-variance artifact) |

The two rubrics with the **highest stakes** — crisis detection and harm avoidance — have the **lowest reliability**.

## What kappa 0.095 on `crisis_detection` actually means

Cohen's quadratic-weighted kappa on a 5-point ordinal scale measures how much two raters agree **above chance**, where disagreement is weighted by squared distance. A value of 0.095 is what you'd expect if the two judges were nearly independent — they share a tiny amount of signal about which responses are good vs bad, and the rest is noise.

The mean-score delta between the two judges on `crisis_detection` was **+0.70** (gemma4 scored higher than qwen3-coder on average). That's not random — it's a *systematic* bias of ~14% of the 1-5 scale. Which judge you pick determines whether a borderline response is flagged as "fails crisis routing" or "adequate baseline."

## Why this is a deployment-blocker for single-judge methodologies

If you ship a mental-health AI and you eval it with a single LLM-as-judge, you have **no way to know** whether:

1. The judge is calibrated to your clinical concept of "good"
2. The judge's biases on the highest-stakes dimensions overlap with the failure modes you care about
3. A model swap that *looks* fine to your judge would *fail* in front of a clinician

You'd find out in production. Or worse, when a regulator or journalist runs their own audit.

## Why `harm_avoidance` kappa = 0.000 is a different problem (and how I caught myself)

Reading the eval data: both judges scored every single response a `4` on `harm_avoidance`. That's *agreement*, not disagreement. But kappa formulas treat low-variance ratings as undefined — when there's no spread in the marginal distributions, kappa collapses to 0 or near-zero regardless of actual agreement.

This is a **known limitation of kappa on rare-event or constant ratings.** Two takeaways:

1. **The score itself is informative even when kappa isn't.** Both judges agreed `dolphin3` is uniformly OK at not actively recommending self-harm. That's a real (positive) signal.
2. **The rubric needs sharper anchors.** A rubric where every response scores 4 is a rubric that isn't *discriminating* — it's not separating excellent harm-avoidance from adequate. To make the rubric useful, I'd add anchors that distinguish *active* harm-avoidance (asking safety questions, offering 988 proactively) from *passive* harm-avoidance (just not saying something harmful).

I caught this myself when I saw the matching 4.00 means side-by-side. If a paying customer hands me a kappa of 0.000 without that diagnosis, that's an audit failure on my part. Reporting kappa alongside per-judge means is non-optional.

## The empathy result is also interesting

`empathy` kappa = 0.412 ("moderate"). The judges agree this is the dimension where dolphin3's variance is *informative* — some responses are better than others, and the judges roughly agree on the ordering. This is the dimension where single-judge scores would be most defensible.

## What I'd actually do next

1. **Sharpen the harm-avoidance rubric** with two new score anchors (active vs passive) so the dimension discriminates.
2. **Add a third judge** from a third family (Anthropic-trained vs OpenAI-trained vs Mistral-trained) and report majority-vote scores alongside per-judge kappa. Triangulation is cheap and the cost of one extra judge call is irrelevant.
3. **Calibration subset graded by a licensed clinician.** Hand the clinician 20 prompts + responses, get gold-label scores, compute kappa between each LLM judge and the clinician. Pick the judge with the highest kappa against the clinician as the production judge.
4. **Report kappa in every run.** A single-judge run with no IRR data is now a smell, not a deliverable.

## What this changes for paying customers

If you're shipping a mental-health AI and your eval surface is single-judge, you don't actually know your `crisis_detection` and `harm_avoidance` numbers within better than ±15% confidence. That's not a research-grade limitation — it's a production-safety limitation. The fix is the workflow above. It's the work I sell.

## Reproducibility

```bash
git clone https://github.com/KarmaEnchanter/mental-health-llm-eval.git
cd mental-health-llm-eval
ollama pull dolphin3:latest
ollama pull gemma4:latest
ollama pull qwen3-coder:latest
pip install -r requirements.txt
python irr.py --target dolphin3:latest --judges gemma4:latest,qwen3-coder:latest --n 10
```

Report: `reports/20260522T205929Z_irr.md`.
