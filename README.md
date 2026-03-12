<div align="center">

# Skill-Double-Edge

### Skills Are a Double-Edged Sword for LLM Code Generation

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Trials](https://img.shields.io/badge/Trials-1%2C620-blue.svg)](#experiment-design)
[![Models](https://img.shields.io/badge/Models-6-orange.svg)](#experiment-design)
[![Scenarios](https://img.shields.io/badge/Scenarios-30-purple.svg)](#experiment-design)
[![Cost](https://img.shields.io/badge/Cost-%24129-red.svg)](#experiment-design)

*We spent $129 running 1,620 controlled experiments across 6 LLMs and found:*

**Skills help weak models gain +18pp — but the exact same skills make them lose -100pp in other scenarios.**
**Strong models are immune to skills — but most vulnerable to skill poisoning.**

</div>

---

## The Seven Paradoxes

Our experiments reveal a series of counter-intuitive findings about how LLM skills actually work:

| # | Paradox | Finding |
|---|---------|---------|
| 1 | **Skill Paradox** | Weak models are simultaneously the biggest beneficiary (+100pp) AND the biggest victim (-100pp) of skills |
| 2 | **Exact-match Danger** | A skill written *for the exact task* is more dangerous than a completely unrelated skill |
| 3 | **Poison Sensitivity** | The strongest model (Opus) is *most* vulnerable to poisoned skills, not least |
| 4 | **Author Toxicity** | Skill toxicity depends on the specific author-user combination (Opus→Sonnet: fatal; Haiku→Sonnet: safe) |
| 5 | **Partial > Full Danger** | Showing half a skill can be more dangerous than showing the whole thing |
| 6 | **Vaccination Backfire** | Adding "please be critical" helps weak models but *hurts* strong ones (-16pp) |
| 7 | **Import Lethality** | Models tolerate logic errors, stale APIs, wrong defaults — but wrong `import` statements are universally fatal |

> **Deep dive:** [docs/deep_dive_paradoxes.md](docs/deep_dive_paradoxes.md) — detailed tables and root cause analysis for each paradox.

---

## Main Results

### RQ1: How does skill completeness affect performance?

<img src="figures/fig_rq1_heatmap.png" width="700">

- **GPT-4o benefits most**: +18.2pp from No Skill to Full Skill
- **Opus benefits least**: +8.8pp — already strong without help
- **L1 (just SKILL.md text) captures most of the gain** — scripts and references provide diminishing returns

### RQ2: How tolerant are models to skill errors?

<img src="figures/fig_rq2_tolerance.png" width="700">

- `stale_api` and `wrong_default` have **zero impact** across all models
- `wrong_import` is the **fatal mutation**: GPT-4o drops -40pp, GPT-4.1 drops -20pp
- **Opus is the only model immune** to wrong imports (+9pp, actually benefits!)

### RQ3: What happens with wrong skills and "vaccination"?

<img src="figures/fig_rq3_conditions.png" width="700">

- Wrong-domain skills **hurt weak models** (GPT-4o: -5pp) but don't affect strong ones
- "Vaccination" (adding a warning prefix) **helps weak models** recover but **hurts Opus** (-16pp)
- Strong models already have good judgment — extra instructions add noise

### Overview: Does adding a skill help?

<img src="figures/fig_overview.png" width="600">

Each dot = one (model, scenario) pair. Above diagonal = skill helped. Most points cluster above — **skills generally help**, especially for hard scenarios (low baseline).

---

## What is a "Skill"?

In Claude Code and similar AI coding tools, a **skill** is a structured knowledge package that provides domain-specific guidance. We test 5 completeness levels:

| Level | Contents | Description |
|-------|----------|-------------|
| L0 | — | No skill (baseline) |
| L1 | `SKILL.md` | Natural language guidance, pitfalls, patterns |
| L2 | + `scripts/` | Reference code implementations |
| L3 | + `references/` | API docs, examples, edge cases |
| L4 | All of the above | Full skill package |

---

## Experiment Design

| Parameter | Value |
|-----------|-------|
| **Models** | Haiku 3.5, GPT-4o, GPT-4.1, Gemini 2.0 Pro, Sonnet 3.5, Opus 3.5 |
| **Scenarios** | 30 scientific computing tasks across 15+ domains |
| **Conditions** | 15 (5 skill levels + 6 mutation types + 4 robustness conditions) |
| **Total Trials** | 1,620 |
| **Total Cost** | $129.05 |
| **Evaluation** | Automated test suites: 5–15 assertions per scenario |
| **Temperature** | 0.0 (deterministic) |
| **Seed** | 42 (for mutations) |

Three research questions, non-overlapping trial allocation:

| RQ | Focus | Trials |
|----|-------|--------|
| RQ1 | Skill Completeness (L0–L4) | 6 × 30 × 5 = 900 |
| RQ2 | Error Tolerance (5 mutations + clean) | 6 × 10 × 6 = 360 |
| RQ3 | Wrong Skills & Vaccination | 6 × 15 × 4 = 360 |
| **Total** | | **1,620** |

> **Full details:** [MANIFEST.md](MANIFEST.md) — model versions, prompt template, skill injection format, evaluation pipeline, result schema, coverage tables, SHA-256 hashes.

---

## Repository Structure

```
skill-double-edge/
├── README.md
├── MANIFEST.md                    # Dataset card & reproducibility protocol
├── run_benchmark.py               # Re-run the full experiment
├── requirements.txt
│
├── data/
│   ├── experiment_results.csv     # All 1,620 trial results
│   └── scenarios_meta.csv         # 30 scenario metadata
├── figures/                       # 4 publication-ready charts
│
├── scenarios/                     # 10 example scenarios + test suites
├── skills/                        # 8 example skill packages
│   ├── S002_spike_behavior/       #   (5 from experiment scenarios)
│   ├── S012_uv_spectroscopy/
│   ├── fits-aperture-photometry/  #   (3 from generated-skills showcase)
│   ├── spatial-transcriptomics-preprocess/
│   └── swissprot-protein-parser/
│
├── tools/                         # Skill generation tools
│   ├── conversation-to-skill/     #   Extract skill from chat logs
│   └── requirement-to-skill/      #   Generate skill from text requirements
│
├── analysis/
│   ├── generate_figures.py        # Reproduce all charts
│   ├── stats_summary.py           # Statistical summary
│   └── export_data.py             # Data conversion utilities
│
└── docs/
    ├── blog_zh.md                 # 中文博客 (Chinese blog post)
    ├── deep_dive_paradoxes.md     # The 7 paradoxes in detail
    └── reports/
        ├── pilot_report_v2.md     # Pilot findings (10 scenarios × 6 models)
        └── comparison_report.md   # Three skill-generator systems compared
```

> **Scope:** This repo publishes all 1,620 trial results, 10 example scenarios, 8 skill packages, and 2 skill generators. The internal codebase has 100 scenarios and 51 skills; see [MANIFEST.md](MANIFEST.md) for the full breakdown.

---

## Quick Start

```bash
pip install -r requirements.txt
```

### Reproduce the figures

```bash
cd analysis
python generate_figures.py --data ../data/experiment_results.csv --outdir ../figures
```

### Re-run the benchmark

```bash
# Dry run — shows what would be executed
python run_benchmark.py --dry-run

# Run a subset
python run_benchmark.py --rq rq1 --models haiku,gpt4o \
    --scenarios S002_spike_behavior,S012_uv_spectroscopy \
    --api-base "https://api.anthropic.com" --api-key "$KEY"

# Full reproduction (~$130)
python run_benchmark.py --rq all --api-base "..." --api-key "..."
```

### Explore a scenario + skill

```bash
cat scenarios/S012_uv_spectroscopy/task.md              # Task spec
cat skills/S012_uv_spectroscopy/direct/SKILL.md         # Skill guidance
python scenarios/S012_uv_spectroscopy/test_script.py    # Evaluation
```

### Generate skills from scratch

```bash
# See tools/conversation-to-skill/ or tools/requirement-to-skill/
cat tools/requirement-to-skill/SKILL.md  # How the skill generator works
```

---

## Practical Takeaways

**For skill/prompt designers:**
1. **SKILL.md alone gets you 80% of the benefit** — invest in clear text first
2. **Never include wrong imports** — the only fatal error type. Always validate.
3. **Skip "vaccination" for strong models** — warning prefixes add noise
4. **Be careful with expert-level API choices** — they can poison weaker consumers

**For tool builders:**
1. **Weaker models benefit most** — prioritize skill support for cost-effective models
2. **Build import validation** — a simple static check prevents the worst failures
3. **L1 text-only skills are nearly as effective as full packages** — simplify your skill format

**For researchers:**
1. **Skill safety is model-dependent** — findings for one model don't transfer
2. **Exact-match is more dangerous than near-miss** — overturns intuitive assumptions
3. **Instruction-following ability is a double-edged sword** — it enables both knowledge transfer and knowledge poisoning

---

## Also in This Repo

| Resource | Description |
|----------|-------------|
| [docs/deep_dive_paradoxes.md](docs/deep_dive_paradoxes.md) | The 7 paradoxes with detailed tables and root cause analysis |
| [docs/blog_zh.md](docs/blog_zh.md) | 中文博客：完整分析 + 对实践者的建议 |
| [docs/reports/pilot_report_v2.md](docs/reports/pilot_report_v2.md) | Pilot study: 10 scenarios × 6 models, cross-model toxicity, poison experiments |
| [docs/reports/comparison_report.md](docs/reports/comparison_report.md) | Three skill-generator systems compared (all achieve 100% practical pass rate) |
| [tools/](tools/) | Two skill generators: conversation-to-skill and requirement-to-skill |

---

## Citation

```
@misc{skilldoubleedge2026,
  title={Skills Are a Double-Edged Sword for LLM Code Generation},
  author={Skill-Double-Edge Authors},
  year={2026},
  url={https://github.com/qishisuren123/skill-double-edge}
}
```

## License

MIT — see [LICENSE](LICENSE).

---

<details>
<summary><b>中文摘要 (Chinese Summary)</b></summary>

## LLM 技能包是一把双刃剑

我们花了 **$129** 运行了 **1,620 组对照实验**，发现了一系列关于 LLM 技能包的反直觉结论：

### 七个悖论

1. **技能悖论**：弱模型同时是技能的最大受益者（+100pp）和最大受害者（-100pp）
2. **精确匹配更危险**：精确匹配的技能比错误领域的技能更危险
3. **强模型对毒化最敏感**：Opus 被毒化技能从 5/6 打到 0/6，而 Haiku 只掉 1 分
4. **作者特异性毒性**：同一个技能，不同作者写的对不同使用者产生截然不同的效果
5. **部分 > 完整的危险**：只给一半技能可能比给完整技能更危险
6. **免疫反噬**：告诉强模型"请批判性参考"反而让它变差（-16pp）
7. **唯一致命错误**：模型能容忍逻辑错误、过时 API、错误默认值，但 `wrong_import` 是致命的

### 实践建议

- **写好 SKILL.md 就够了**——80% 的收益来自自然语言描述
- **务必检查 import 语句**——唯一致命的错误类型
- **弱模型 + 技能 = 性价比之王**
- **强模型不需要免疫前缀**——信任它的判断

详细中文分析：[docs/blog_zh.md](docs/blog_zh.md)

</details>
