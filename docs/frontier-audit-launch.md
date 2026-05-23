# Frontier Mental-Health AI Audit — Day-2 Reports on Every New Model Release

**Author:** Jeremiah Trojan
**Date:** 2026-05-22
**Repo:** github.com/KarmaEnchanter/mental-health-llm-eval

## What this is

Every time a frontier model ships (GPT-5.5, Claude 4.x, Gemini 2.x, Llama 4.x, Qwen 3.x), I run my open mental-health LLM eval harness against it within 48 hours and publish the report. Five clinically-grounded rubrics (empathy, clinical accuracy, harm avoidance, CBT alignment, crisis detection per 988 protocols), LLM-as-judge with Cohen's quadratic-weighted kappa for inter-judge IRR, multi-turn attack patterns layered on top.

The audit answers one specific question for any team shipping mental-health-adjacent AI: **does the latest frontier model regress on safety-critical rubrics compared to its predecessor?**

## Why "Day-2" matters

The 48-hour window between release and integration decision is the single highest-leverage moment in any safety-critical AI product team's calendar. Most teams:

1. See the new model land Monday
2. Engineer-tinker with it Monday-Tuesday
3. Make a "should we ship this?" decision Wednesday
4. Ship to staging Thursday
5. Ship to production the following week

Internal eval coverage usually catches up at step 4 or 5 — *after* the call has been made. The Day-2 Audit lands during step 2, with rubric scores anchored to clinical literature (Stade et al. 2024, APA CPG, WHO 2023, Beck Institute 2023, 988 protocols).

## What's in each audit report

**Within 48 hours of release, you get:**

- 5-rubric mean + stdev + min + max for the new model on the 50-prompt mental-health dataset
- Diff vs the previous version of the same model family (regression detection)
- Crisis-case scoring report — every prompt flagged with `crisis_detection ≤ 2` surfaced with the model's full response + judge justification
- Multi-turn social-engineering probe results — 6 attack patterns × 10 harm domains, compliance-gap delta
- Inter-judge kappa per dimension (target stability of the scores themselves)
- Specific deployment-blocker calls (the responses where the model would fail in production)

## Pricing (open and direct)

- **Single audit report ($497):** one report on one specific model release. Delivered within 5 business days, sent to your inbox.
- **Quarterly subscription ($1,497/quarter):** every frontier model release in the quarter, plus a quarterly trend report.
- **Annual + custom rubrics ($9,997/year):** every model release for 12 months + 2 custom rubrics anchored to YOUR internal clinical guidance + private Slack thread for follow-up questions.

## The methodology behind every audit

Open and reproducible: [github.com/KarmaEnchanter/mental-health-llm-eval](https://github.com/KarmaEnchanter/mental-health-llm-eval). Read the 4 post-mortems on the repo:

- [Why a medical fine-tune scored 1/5 on crisis detection](postmortem-meditron.md)
- [Why two LLM judges disagree on safety-critical rubrics](postmortem-irr.md)
- [Why kappa is target-dependent](postmortem-irr-target-dependence.md)
- [Why sharper rubrics didn't help (negative finding)](postmortem-rubrics-v2-failed.md)

If the methodology stands up to your scrutiny, the audit reports built on it will too.

## Subscribe / book

`jeremiahjtrojan@gmail.com` — subject `[audit]` for single, `[subscription]` for quarterly, `[annual]` for custom.

Inspect AI framework adapter: [inspect_task.py](../inspect_task.py). If you already run Inspect internally, the rubrics drop into your pipeline as 5 separate Tasks.

## Trust signals

- Methodology open-source on day 1; no proprietary black boxes
- Negative findings published (rubrics_v2 hypothesis refuted) — not just positive PR
- Clinical-literature substrate (UCLA Psychobiology 2024 + reading-list grounding in CBT/DBT/MI)
- Reproducibility: every report includes the exact prompt set + model versions + judge models so you can re-run

## What this is NOT

- Not a replacement for your internal eval team
- Not a regulatory certification
- Not a clinician — the rubrics are clinically anchored but no licensed clinician signs off on individual scores (calibration subset is a $5K/mo retainer add-on)
- Not a marketing claim — if the new model regresses, the audit says so; if it improves, the audit says so

The point is the Day-2 timing and the methodology rigor, not the brand.
