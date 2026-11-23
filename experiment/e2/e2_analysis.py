#!/usr/bin/env python3
"""Mechanical analysis of the E2 reviewer-isolation experiment.

Recomputes every number the report quotes about E2 from the preserved
per-run records (`score.json` + `verdict.json` under
`experiment/e2/results/sp*/`), so the table in report section 3 is
derived, not hand-asserted. Also cross-checks `summary.json` against the
score files and flags the known metric wrinkle: `planted_defect_caught`
is a keyword-based flag over the verdict object and can disagree with the
final verdict (a run can write the defect into its reasoning and still
approve with zero formal findings). The report's catch rates are
verdict-based; this script reports both so the discrepancy is visible
rather than buried.

Usage:
    python3 experiment/e2/e2_analysis.py            # writes analysis.md
    python3 experiment/e2/e2_analysis.py --check    # exit 1 on inconsistency

Local files only; no network, no provider calls.
"""

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT = RESULTS / "analysis.md"


def load_runs():
    runs = []
    for score_path in sorted(RESULTS.glob("sp*/[AB]/score.json")):
        score = json.loads(score_path.read_text())
        verdict_path = score_path.with_name("verdict.json")
        findings = None
        if verdict_path.exists():
            verdict = json.loads(verdict_path.read_text())
            result = verdict.get("result") or {}
            f = result.get("findings")
            if isinstance(f, list):
                findings = len(f)
        usage = score.get("usage") or {}
        runs.append({
            "seed": score.get("seed"),
            "variant": score.get("variant"),
            "verdict": score.get("verdict"),
            "expected": score.get("expected_verdict"),
            "correct": score.get("verdict") == score.get("expected_verdict"),
            "keyword_caught": score.get("planted_defect_caught"),
            "findings": findings,
            "calls": usage.get("calls"),
            "total_tokens": usage.get("total_tokens"),
            "error": score.get("error"),
        })
    return runs


def check_summary(runs):
    """Return list of mismatch strings between score files and summary.json."""
    problems = []
    summary_path = RESULTS / "summary.json"
    if not summary_path.exists():
        return ["summary.json missing"]
    summary = json.loads(summary_path.read_text())
    idx = {(s.get("seed"), s.get("variant")): s for s in summary}
    for r in runs:
        s = idx.get((r["seed"], r["variant"]))
        if s is None:
            problems.append(f"{r['seed']}/{r['variant']}: absent from summary.json")
            continue
        for key_score, key_summary in (
            ("verdict", "verdict"),
            ("expected", "expected_verdict"),
            ("keyword_caught", "planted_defect_caught"),
        ):
            if r[key_score] != s.get(key_summary):
                problems.append(
                    f"{r['seed']}/{r['variant']}: {key_summary} score="
                    f"{r[key_score]!r} summary={s.get(key_summary)!r}")
    if len(summary) != len(runs):
        problems.append(f"summary.json has {len(summary)} rows, "
                        f"score files have {len(runs)}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="only verify consistency; non-zero exit on problems")
    args = ap.parse_args()

    runs = load_runs()
    if not runs:
        print("no score.json files found", file=sys.stderr)
        return 1
    problems = check_summary(runs)
    if args.check:
        for p in problems:
            print(f"MISMATCH: {p}")
        print(f"{len(runs)} runs checked, {len(problems)} problems")
        return 1 if problems else 0

    variants = {}
    for r in runs:
        v = variants.setdefault(r["variant"], [])
        v.append(r)

    lines = ["# E2 mechanical analysis", "",
             "Derived from `score.json` + `verdict.json` by "
             "`experiment/e2/e2_analysis.py`; do not hand-edit the numbers. "
             "Cross-checked against `summary.json` "
             f"({len(problems)} inconsistencies).", ""]
    if problems:
        lines.append("Inconsistencies found:")
        lines += [f"- {p}" for p in problems]
        lines.append("")

    lines += ["| Seed | Variant | Verdict | Expected | Verdict correct | "
              "Keyword-caught flag | Formal findings | Calls | Tokens |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(runs, key=lambda x: (x["seed"], x["variant"])):
        flag = ""
        if r["keyword_caught"] and r["verdict"] == "approve":
            flag = " (disagrees with verdict)"
        findings = r["findings"] if r["findings"] is not None else "n/a"
        lines.append(
            f"| {r['seed']} | {r['variant']} | {r['verdict']} | "
            f"{r['expected']} | {'yes' if r['correct'] else 'no'} | "
            f"{r['keyword_caught']}{flag} | {findings} | {r['calls']} | "
            f"{r['total_tokens']:,} |")
    lines.append("")

    for v in sorted(variants):
        rows = variants[v]
        correct = sum(1 for r in rows if r["correct"])
        kw = sum(1 for r in rows if r["keyword_caught"])
        tokens = sum(r["total_tokens"] or 0 for r in rows)
        calls = sum(r["calls"] or 0 for r in rows)
        lines.append(f"- Variant {v}: verdict-correct {correct}/{len(rows)}; "
                     f"keyword-caught {kw}/{len(rows)}; "
                     f"{tokens:,} tokens across {calls} calls.")
    if "A" in variants and "B" in variants:
        a_tok = sum(r["total_tokens"] or 0 for r in variants["A"])
        b_tok = sum(r["total_tokens"] or 0 for r in variants["B"])
        if a_tok:
            lines.append(f"- Token ratio B/A: {b_tok / a_tok:.2f}x.")
        flips = 0
        a_by_seed = {r["seed"]: r for r in variants["A"]}
        for r in variants["B"]:
            a = a_by_seed.get(r["seed"])
            if a and a["correct"] and not r["correct"]:
                flips += 1
        lines.append(f"- Verdict flips from correct-under-A to "
                     f"wrong-under-B: {flips} of {len(a_by_seed)}.")
    lines.append("")
    lines.append("Catch rates quoted in the report are verdict-correct "
                 "rates. The keyword-caught flag is retained above because "
                 "it can disagree with the verdict (flag true, verdict "
                 "approve, zero formal findings): those rows are where the "
                 "reviewer wrote the defect into its own output and "
                 "approved anyway. That disagreement is evidence for the "
                 "influence claim and is listed as a metric limitation in "
                 "report section 6.")
    lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT} ({len(runs)} runs, {len(problems)} inconsistencies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
