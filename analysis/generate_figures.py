#!/usr/bin/env python3
"""
生成 SkillBench 博客所需的 4 张核心图表。
用法: python generate_figures.py --data ../data/experiment_results.csv --outdir ../figures
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch

# ── 全局样式 ──
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
})

# 颜色方案
MODEL_COLORS = {
    "haiku":      "#7FB3D8",
    "gpt4o":      "#76C7A5",
    "gpt41":      "#A8D08D",
    "gemini_pro": "#F4B860",
    "sonnet":     "#E8907E",
    "opus":       "#B07CC6",
}

MODEL_LABELS = {
    "haiku":      "Haiku 3.5",
    "gpt4o":      "GPT-4o",
    "gpt41":      "GPT-4.1",
    "gemini_pro": "Gemini 2.0 Pro",
    "sonnet":     "Sonnet 3.5",
    "opus":       "Opus 3.5",
}

LEVEL_LABELS = {
    "L0_none":         "L0\nNo Skill",
    "L1_skill_md":     "L1\nSKILL.md",
    "L2_plus_scripts": "L2\n+ Scripts",
    "L3_no_assets":    "L3\n+ Refs",
    "L4_full":         "L4\nFull",
}

MODEL_ORDER = ["haiku", "gpt4o", "gpt41", "gemini_pro", "sonnet", "opus"]
LEVEL_ORDER = ["L0_none", "L1_skill_md", "L2_plus_scripts", "L3_no_assets", "L4_full"]


def load_data(path):
    """加载实验数据"""
    df = pd.read_csv(path)
    return df


def fig_rq1_heatmap(df, outdir):
    """RQ1 热力图: model × skill_level → pass_rate (仅非 mutation 场景)"""
    # 筛选 RQ1 数据
    mask = (
        (df["mutation_type"] == "none") &
        (~df["condition"].str.startswith("rq3_"))
    )
    sub = df[mask].copy()

    # 计算平均 pass_rate
    pivot = sub.groupby(["model", "skill_level"])["pass_rate"].mean().unstack()
    pivot = pivot.reindex(index=MODEL_ORDER, columns=LEVEL_ORDER)

    fig, ax = plt.subplots(figsize=(10, 5))

    # 热力图数据
    data = pivot.values * 100  # 转百分比

    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=20, vmax=60)

    # 标注
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            color = "white" if val < 30 or val > 55 else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=11, fontweight="bold", color=color)

    # 轴标签
    ax.set_xticks(range(len(LEVEL_ORDER)))
    ax.set_xticklabels([LEVEL_LABELS[l] for l in LEVEL_ORDER], fontsize=10)
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], fontsize=11)

    # Delta 注释列
    for i, m in enumerate(MODEL_ORDER):
        l0 = pivot.loc[m, "L0_none"] * 100
        l4 = pivot.loc[m, "L4_full"] * 100
        delta = l4 - l0
        color = "#2E7D32" if delta > 5 else ("#C62828" if delta < -2 else "#666")
        sign = "+" if delta > 0 else ""
        ax.text(len(LEVEL_ORDER) + 0.3, i, f"Δ={sign}{delta:.1f}pp",
                ha="left", va="center", fontsize=10, fontweight="bold", color=color)

    ax.set_title("RQ1: How Does Skill Completeness Affect Performance?",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Skill Completeness Level", labelpad=10)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.20)
    cbar.set_label("Mean Pass Rate (%)", fontsize=10)

    plt.tight_layout()
    path = os.path.join(outdir, "fig_rq1_heatmap.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"  ✓ {path}")


def fig_rq2_tolerance(df, outdir):
    """RQ2 分组柱状图: mutation_type × model → Δpass_rate"""
    # RQ2 数据: mutation 条件 + clean baseline
    mask = (
        (df["mutation_type"] != "none") | (df["condition"] == "clean_full")
    )
    sub = df[mask].copy()

    mutation_types = ["logic_error", "missing_edge_case", "stale_api", "wrong_default", "wrong_import"]
    mutation_labels = ["Logic\nError", "Missing\nEdge Case", "Stale\nAPI", "Wrong\nDefault", "Wrong\nImport"]

    # 计算 clean baseline 和 mutation deltas
    baselines = {}
    for m in MODEL_ORDER:
        clean = sub[(sub["model"] == m) & (sub["condition"] == "clean_full")]["pass_rate"]
        baselines[m] = clean.mean() if len(clean) > 0 else 0

    fig, ax = plt.subplots(figsize=(12, 5.5))

    x = np.arange(len(mutation_types))
    width = 0.13
    offsets = np.arange(len(MODEL_ORDER)) - (len(MODEL_ORDER) - 1) / 2

    for idx, m in enumerate(MODEL_ORDER):
        deltas = []
        for mt in mutation_types:
            cond = f"mutated_{mt}"
            vals = sub[(sub["model"] == m) & (sub["condition"] == cond)]["pass_rate"]
            avg = vals.mean() if len(vals) > 0 else 0
            deltas.append((avg - baselines[m]) * 100)

        bars = ax.bar(x + offsets[idx] * width, deltas, width * 0.9,
                      label=MODEL_LABELS[m], color=MODEL_COLORS[m],
                      edgecolor="white", linewidth=0.5)

    ax.axhline(y=0, color="black", linewidth=0.8, linestyle="-")
    ax.set_xticks(x)
    ax.set_xticklabels(mutation_labels, fontsize=10)
    ax.set_ylabel("Δ Pass Rate (pp) vs. Clean Skill", fontsize=11)
    ax.set_title("RQ2: How Tolerant Are Models to Skill Errors?",
                 fontsize=14, fontweight="bold", pad=15)
    ax.legend(loc="lower left", ncol=3, fontsize=9, framealpha=0.9)
    ax.set_ylim(-50, 20)
    ax.grid(axis="y", alpha=0.3)

    # 标注 wrong_import 是致命的
    ax.annotate("← Fatal for most models",
                xy=(4.3, -35), fontsize=9, color="#C62828", fontweight="bold")

    plt.tight_layout()
    path = os.path.join(outdir, "fig_rq2_tolerance.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"  ✓ {path}")


def fig_rq3_conditions(df, outdir):
    """RQ3 分组柱状图: condition × model → pass_rate"""
    mask = df["condition"].str.startswith("rq3_")
    sub = df[mask].copy()

    conditions = ["rq3_no_skill", "rq3_full_skill", "rq3_wrong_skill", "rq3_vaccinated"]
    cond_labels = ["No Skill", "Full Skill", "Wrong Skill", "Vaccinated"]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    x = np.arange(len(conditions))
    width = 0.13
    offsets = np.arange(len(MODEL_ORDER)) - (len(MODEL_ORDER) - 1) / 2

    for idx, m in enumerate(MODEL_ORDER):
        rates = []
        for c in conditions:
            vals = sub[(sub["model"] == m) & (sub["condition"] == c)]["pass_rate"]
            rates.append(vals.mean() * 100 if len(vals) > 0 else 0)

        ax.bar(x + offsets[idx] * width, rates, width * 0.9,
               label=MODEL_LABELS[m], color=MODEL_COLORS[m],
               edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(cond_labels, fontsize=11)
    ax.set_ylabel("Mean Pass Rate (%)", fontsize=11)
    ax.set_title("RQ3: Wrong Skills & Vaccination Effects",
                 fontsize=14, fontweight="bold", pad=15)
    ax.legend(loc="upper right", ncol=2, fontsize=9, framealpha=0.9)
    ax.set_ylim(0, 85)
    ax.grid(axis="y", alpha=0.3)

    # 注释
    ax.annotate("Vaccination helps\nweak models",
                xy=(3.0, 68), fontsize=9, color="#2E7D32",
                ha="center", fontstyle="italic")
    ax.annotate("Vaccination hurts\nstrong models",
                xy=(3.0, 48), fontsize=9, color="#C62828",
                ha="center", fontstyle="italic")

    plt.tight_layout()
    path = os.path.join(outdir, "fig_rq3_conditions.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"  ✓ {path}")


def fig_overview(df, outdir):
    """总览散点图: L0 vs L4 pass_rate per scenario, 每个模型一种颜色"""
    # 筛选 L0 和 L4 数据
    mask_l0 = (df["skill_level"] == "L0_none") & (df["mutation_type"] == "none") & (~df["condition"].str.startswith("rq3_"))
    mask_l4 = (df["skill_level"] == "L4_full") & (df["mutation_type"] == "none") & (~df["condition"].str.startswith("rq3_"))

    l0_data = df[mask_l0].groupby(["model", "scenario"])["pass_rate"].mean().reset_index()
    l4_data = df[mask_l4].groupby(["model", "scenario"])["pass_rate"].mean().reset_index()

    merged = l0_data.merge(l4_data, on=["model", "scenario"], suffixes=("_l0", "_l4"))

    fig, ax = plt.subplots(figsize=(8, 8))

    # 对角线
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1, label="_nolegend_")
    ax.fill_between([0, 1], [0, 1], [1, 1], alpha=0.06, color="green")
    ax.fill_between([0, 1], [0, 0], [0, 1], alpha=0.06, color="red")

    for m in MODEL_ORDER:
        sub = merged[merged["model"] == m]
        ax.scatter(sub["pass_rate_l0"] * 100, sub["pass_rate_l4"] * 100,
                   c=MODEL_COLORS[m], label=MODEL_LABELS[m],
                   s=80, alpha=0.7, edgecolors="white", linewidth=0.5, zorder=3)

    ax.set_xlabel("Pass Rate without Skill — L0 (%)", fontsize=12)
    ax.set_ylabel("Pass Rate with Full Skill — L4 (%)", fontsize=12)
    ax.set_title("Overview: Does Adding a Skill Help?",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax.grid(alpha=0.2)

    # 区域标注
    ax.text(15, 90, "Skill Helps ↑", fontsize=11, color="#2E7D32",
            fontweight="bold", alpha=0.7)
    ax.text(70, 15, "Skill Hurts ↓", fontsize=11, color="#C62828",
            fontweight="bold", alpha=0.7)

    plt.tight_layout()
    path = os.path.join(outdir, "fig_overview.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"  ✓ {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate SkillBench blog figures")
    parser.add_argument("--data", default="../data/experiment_results.csv",
                        help="Path to experiment_results.csv")
    parser.add_argument("--outdir", default="../figures",
                        help="Output directory for figures")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    print(f"Loading data from {args.data} ...")
    df = load_data(args.data)
    print(f"  {len(df)} trials loaded")

    print("\nGenerating figures ...")
    fig_rq1_heatmap(df, args.outdir)
    fig_rq2_tolerance(df, args.outdir)
    fig_rq3_conditions(df, args.outdir)
    fig_overview(df, args.outdir)

    print(f"\nDone! {4} figures saved to {args.outdir}/")


if __name__ == "__main__":
    main()
