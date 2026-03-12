#!/usr/bin/env python3
"""
SkillBench 统计汇总脚本。
用法: python stats_summary.py --data ../data/experiment_results.csv
"""

import argparse
import pandas as pd
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="SkillBench statistics summary")
    parser.add_argument("--data", default="../data/experiment_results.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    print(f"Loaded {len(df)} trials\n")

    # ── 总体统计 ──
    models = df["model"].nunique()
    scenarios = df["scenario"].nunique()
    conditions = df["condition"].nunique()
    print(f"Models: {models}")
    print(f"Scenarios: {scenarios}")
    print(f"Conditions: {conditions}")
    print(f"Total trials: {len(df)}")

    # ── RQ1: Skill Completeness ──
    print("\n" + "=" * 60)
    print("RQ1: Skill Completeness Effect (L0 vs L4)")
    print("=" * 60)
    rq1 = df[
        (df["mutation_type"] == "none") &
        (~df["condition"].str.startswith("rq3_"))
    ]
    for model in sorted(df["model"].unique()):
        l0 = rq1[(rq1["model"] == model) & (rq1["skill_level"] == "L0_none")]["pass_rate"].mean()
        l4 = rq1[(rq1["model"] == model) & (rq1["skill_level"] == "L4_full")]["pass_rate"].mean()
        delta = (l4 - l0) * 100
        print(f"  {model:<15}: L0={l0:.1%}  L4={l4:.1%}  Δ={delta:+.1f}pp")

    # ── RQ2: Mutation Tolerance ──
    print("\n" + "=" * 60)
    print("RQ2: Mutation Tolerance (Δ from clean)")
    print("=" * 60)
    rq2 = df[(df["mutation_type"] != "none") | (df["condition"] == "clean_full")]
    for model in sorted(df["model"].unique()):
        clean = rq2[(rq2["model"] == model) & (rq2["condition"] == "clean_full")]["pass_rate"].mean()
        mutations = {}
        for mt in ["logic_error", "missing_edge_case", "stale_api", "wrong_default", "wrong_import"]:
            cond = f"mutated_{mt}"
            vals = rq2[(rq2["model"] == model) & (rq2["condition"] == cond)]["pass_rate"]
            if len(vals) > 0:
                mutations[mt] = (vals.mean() - clean) * 100
        parts = ", ".join(f"{k}={v:+.1f}pp" for k, v in mutations.items())
        print(f"  {model:<15}: clean={clean:.1%}  {parts}")

    # ── RQ3: Wrong Skill & Vaccination ──
    print("\n" + "=" * 60)
    print("RQ3: Wrong Skill & Vaccination Effects")
    print("=" * 60)
    rq3 = df[df["condition"].str.startswith("rq3_")]
    for model in sorted(df["model"].unique()):
        for cond in ["rq3_no_skill", "rq3_full_skill", "rq3_wrong_skill", "rq3_vaccinated"]:
            vals = rq3[(rq3["model"] == model) & (rq3["condition"] == cond)]["pass_rate"]
            if len(vals) > 0:
                label = cond.replace("rq3_", "")
                print(f"  {model:<15} {label:<15}: {vals.mean():.1%} (n={len(vals)})")
        print()


if __name__ == "__main__":
    main()
