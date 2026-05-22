"""
Inter-rater reliability (IRR) extension to the eval harness.

Runs target once. Each response is scored by two judges independently.
Computes Cohen's quadratic-weighted kappa per rubric dimension —
the appropriate IRR statistic for ordinal 1-5 scales.

Why this matters: single-judge LLM-as-judge has documented bias toward
verbose, hedging responses. Two judges from different families with
weighted-kappa reporting catches systematic disagreement before it
gets baked into a model-selection decision.

Usage:
    python irr.py --target meditron:latest --judges gemma4:latest,qwen3-coder:latest --n 10

Kappa interpretation (Landis & Koch 1977):
  < 0.0 : less than chance
  0.0-0.2 : slight
  0.2-0.4 : fair
  0.4-0.6 : moderate
  0.6-0.8 : substantial
  0.8-1.0 : almost perfect
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluate import (
    DEFAULT_OLLAMA,
    PROMPTS,
    REPORTS,
    init_db,
    judge_response,
    ollama_chat,
)


def quadratic_weighted_kappa(
    rater_a: list[int], rater_b: list[int], k: int = 5
) -> float | None:
    """Cohen's quadratic-weighted kappa for k-point ordinal scales.

    Returns None if not computable (e.g. one rater is constant).
    """
    if len(rater_a) != len(rater_b) or not rater_a:
        return None

    n = len(rater_a)
    # observed agreement matrix O[i][j]
    O = [[0] * k for _ in range(k)]
    for a, b in zip(rater_a, rater_b):
        O[a - 1][b - 1] += 1

    # marginal distributions
    a_marginal = [sum(O[i]) for i in range(k)]
    b_marginal = [sum(O[i][j] for i in range(k)) for j in range(k)]

    # expected agreement E[i][j] under independence
    E = [[(a_marginal[i] * b_marginal[j]) / n for j in range(k)] for i in range(k)]

    # quadratic disagreement weights
    W = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]

    num = sum(W[i][j] * O[i][j] for i in range(k) for j in range(k))
    den = sum(W[i][j] * E[i][j] for i in range(k) for j in range(k))
    if den == 0:
        return None
    return 1.0 - (num / den)


def interpret_kappa(kappa: float | None) -> str:
    if kappa is None:
        return "n/a (one rater constant or insufficient data)"
    if kappa < 0:
        return "less than chance"
    if kappa < 0.2:
        return "slight"
    if kappa < 0.4:
        return "fair"
    if kappa < 0.6:
        return "moderate"
    if kappa < 0.8:
        return "substantial"
    return "almost perfect"


def run_irr(target: str, judges: list[str], n: int, host: str) -> str:
    if target in judges:
        print(f"ERROR: target {target} cannot also be a judge", file=sys.stderr)
        return ""
    if len(set(judges)) != len(judges):
        print(f"ERROR: judges must be distinct: {judges}", file=sys.stderr)
        return ""
    if len(judges) < 2:
        print(f"ERROR: IRR requires at least 2 judges, got {len(judges)}", file=sys.stderr)
        return ""

    cases = json.loads(PROMPTS.read_text(encoding="utf-8"))[:n]
    conn = init_db()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_irr"
    ts = datetime.now(timezone.utc).isoformat()
    print(f"=== mental-health-llm-eval IRR ===")
    print(f"run_id={run_id}  target={target}  judges={judges}  n={n}")
    print(f"host={host}\n")

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']} ({case['category']}) ...", end="", flush=True)
        t0 = time.time()
        try:
            response = ollama_chat(
                target,
                [{"role": "user", "content": case["text"]}],
                host,
                timeout=180,
            )
        except Exception as e:
            print(f" target failed: {e!s}")
            continue

        for judge in judges:
            scores = judge_response(judge, case["text"], response, host)
            for dim, s in scores.items():
                conn.execute(
                    "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, ts, target, judge, case["id"], case["category"],
                     case["text"], response, dim, s["score"], s["justification"]),
                )
        conn.commit()
        print(f" {time.time() - t0:.1f}s")

    report_path = write_irr_report(conn, run_id, target, judges, n)
    print(f"\nReport: {report_path}")
    conn.close()
    return run_id


def write_irr_report(
    conn: sqlite3.Connection, run_id: str, target: str, judges: list[str], n: int
) -> Path:
    REPORTS.mkdir(exist_ok=True)
    a, b = judges[0], judges[1]

    rows = conn.execute(
        "SELECT case_id, dimension, judge, score FROM runs "
        "WHERE run_id = ? AND score IS NOT NULL",
        (run_id,),
    ).fetchall()

    # nest: case_id -> dim -> judge -> score
    nested: dict[str, dict[str, dict[str, int]]] = {}
    for case_id, dim, judge, score in rows:
        nested.setdefault(case_id, {}).setdefault(dim, {})[judge] = score

    dim_kappas: dict[str, tuple[float | None, int]] = {}
    per_judge_means: dict[str, dict[str, list[int]]] = {a: {}, b: {}}

    for case_id, dim_map in nested.items():
        for dim, judge_scores in dim_map.items():
            if a in judge_scores:
                per_judge_means[a].setdefault(dim, []).append(judge_scores[a])
            if b in judge_scores:
                per_judge_means[b].setdefault(dim, []).append(judge_scores[b])

    dimensions = sorted({dim for dim_map in nested.values() for dim in dim_map.keys()})
    for dim in dimensions:
        rater_a, rater_b = [], []
        for case_id in sorted(nested.keys()):
            j = nested[case_id].get(dim, {})
            if a in j and b in j:
                rater_a.append(j[a])
                rater_b.append(j[b])
        k = quadratic_weighted_kappa(rater_a, rater_b)
        dim_kappas[dim] = (k, len(rater_a))

    lines = [
        f"# IRR Run {run_id}",
        f"target={target} | judges={judges} | n={n}\n",
        "## Per-judge mean scores",
        "",
        f"| dimension | {a} | {b} | delta |",
        "|---|---|---|---|",
    ]
    for dim in dimensions:
        ma = statistics.mean(per_judge_means[a].get(dim, [0]))
        mb = statistics.mean(per_judge_means[b].get(dim, [0]))
        lines.append(f"| {dim} | {ma:.2f} | {mb:.2f} | {ma - mb:+.2f} |")

    lines += [
        "",
        "## Cohen's quadratic-weighted kappa (judge-judge IRR)",
        "",
        f"Judges: `{a}` vs `{b}`. Higher = more agreement. Landis & Koch (1977) interpretation:",
        "",
        "| dimension | kappa | interpretation | n |",
        "|---|---|---|---|",
    ]
    for dim in dimensions:
        k, count = dim_kappas[dim]
        k_str = f"{k:.3f}" if k is not None else "n/a"
        lines.append(f"| {dim} | {k_str} | {interpret_kappa(k)} | {count} |")

    lines += [
        "",
        "## What to do with this",
        "",
        "- **kappa < 0.4 (fair or worse):** the rubric prompt is ambiguous and needs sharper anchors. Recalibrate before trusting downstream scores.",
        "- **kappa 0.4-0.6 (moderate):** scores are usable for relative ranking, but absolute scores carry noise. Report ranges, not point estimates.",
        "- **kappa 0.6-0.8 (substantial):** production-grade IRR. Single-judge runs are now defensible.",
        "- **kappa > 0.8:** check that the judges aren't both anchoring on the same surface feature (over-agreement risk).",
    ]
    out = REPORTS / f"{run_id}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    latest = REPORTS / "latest_irr.md"
    latest.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True, help="Model under test")
    p.add_argument(
        "--judges",
        required=True,
        help="Comma-separated list of two judge models from different families",
    )
    p.add_argument("--n", type=int, default=10, help="Number of prompts (max 20)")
    p.add_argument("--host", default=DEFAULT_OLLAMA, help="Ollama host URL")
    args = p.parse_args()
    judges = [j.strip() for j in args.judges.split(",") if j.strip()]
    run_irr(args.target, judges, args.n, args.host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
