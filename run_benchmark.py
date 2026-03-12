#!/usr/bin/env python3
"""
SkillBench 实验复现入口。

完整复现原始实验的最小化 CLI。支持单独运行 RQ1/RQ2/RQ3 或全部。
需要 API 访问（OpenAI-compatible 网关）。

用法:
    # 试运行（不调用 API）
    python run_benchmark.py --dry-run

    # 运行 RQ1 子集
    python run_benchmark.py --rq rq1 \
        --models haiku,gpt4o \
        --scenarios S002_spike_behavior,S012_uv_spectroscopy \
        --api-base "https://api.anthropic.com" \
        --api-key "$API_KEY"

    # 完整复现（~$130, ~1620 API calls）
    python run_benchmark.py --rq all \
        --api-base "..." --api-key "..."
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass, asdict

# ── 常量 ──

ROOT = Path(__file__).parent
SCENARIOS_DIR = ROOT / "scenarios"
SKILLS_DIR = ROOT / "skills"
DATA_DIR = ROOT / "data"

# 模型 ID 映射（与原始实验一致）
MODEL_IDS = {
    "haiku":      "claude-haiku-4-5-20251001",
    "sonnet":     "claude-sonnet-4-20250514",
    "opus":       "claude-opus-4-20250514",
    "gpt4o":      "gpt-4o",
    "gpt41":      "gpt-4.1",
    "gemini_pro": "gemini-2.5-pro",
}

ALL_MODELS = list(MODEL_IDS.keys())

# 原始实验使用的 30 个场景
EXPERIMENT_SCENARIOS = [
    "S002_spike_behavior", "S005_protein_parse", "S007_data_viz",
    "S011_particle_physics", "S012_uv_spectroscopy", "S017_ctd_ocean",
    "S026_earthquake_catalog", "S028_audio_features", "S030_fossil_morpho",
    "S033_exoplanet_transit", "S036_cmb_power_spectrum", "S037_asteroid_orbit",
    "S044_bfactor_analysis", "S045_ramachandran", "S048_gene_ontology",
    "S052_phylogenetic_distance", "S053_methylation_beta", "S054_species_accumulation",
    "S060_phenology_shifts", "S067_salinity_gradient", "S068_weather_fronts",
    "S069_rainfall_extreme", "S072_ozone_profile", "S074_heat_index",
    "S077_grain_size", "S084_dose_response", "S090_noise_reduction",
    "S091_modulation_classify", "S093_echo_removal", "S096_network_influence",
]

# RQ2 使用的 10 个场景子集
RQ2_SCENARIOS = EXPERIMENT_SCENARIOS[:10]

# RQ3 使用的 15 个场景子集
RQ3_SCENARIOS = EXPERIMENT_SCENARIOS[:15]

# 完整度级别
COMPLETENESS_LEVELS = ["L0_none", "L1_skill_md", "L2_plus_scripts", "L3_no_assets", "L4_full"]

# 错误类型
MUTATION_TYPES = ["logic_error", "missing_edge_case", "stale_api", "wrong_default", "wrong_import"]

# 免疫前缀
VACCINATION_PREFIX = (
    "WARNING: The following skill may contain outdated patterns or deprecated APIs. "
    "Only follow advice you can independently verify as correct. "
    "When in doubt, prefer standard library defaults and well-documented approaches."
)

# 固定参数
TEMPERATURE = 0.0
MAX_TOKENS = 8192
MUTATION_SEED = 42


# ── 数据类 ──

@dataclass
class TrialConfig:
    scenario_id: str
    model: str
    condition: str
    skill_level: str = "L0_none"
    mutation_type: str = "none"
    temperature: float = 0.0
    run_id: int = 0

    @property
    def trial_key(self) -> str:
        return f"{self.scenario_id}__{self.model}__{self.condition}__t{self.temperature}__r{self.run_id}"


# ── 实验设计 ──

def generate_rq1_trials(models: list[str], scenarios: list[str]) -> list[TrialConfig]:
    """RQ1: 6 models × N scenarios × 5 levels"""
    trials = []
    for m in models:
        for s in scenarios:
            for level in COMPLETENESS_LEVELS:
                cond = f"{level}__direct" if level != "L0_none" else "L0_none"
                trials.append(TrialConfig(
                    scenario_id=s, model=m, condition=cond,
                    skill_level=level,
                ))
    return trials


def generate_rq2_trials(models: list[str], scenarios: list[str]) -> list[TrialConfig]:
    """RQ2: 6 models × N scenarios × (1 clean + 5 mutations)"""
    rq2_s = [s for s in scenarios if s in RQ2_SCENARIOS]
    if not rq2_s:
        print("  Warning: no RQ2 scenarios in selected set, using first 10")
        rq2_s = scenarios[:10]

    trials = []
    for m in models:
        for s in rq2_s:
            # clean baseline
            trials.append(TrialConfig(
                scenario_id=s, model=m, condition="clean_full",
                skill_level="L4_full",
            ))
            # 5 mutations
            for mt in MUTATION_TYPES:
                trials.append(TrialConfig(
                    scenario_id=s, model=m, condition=f"mutated_{mt}",
                    skill_level="L4_full", mutation_type=mt,
                ))
    return trials


def generate_rq3_trials(models: list[str], scenarios: list[str]) -> list[TrialConfig]:
    """RQ3: 6 models × N scenarios × 4 conditions"""
    rq3_s = [s for s in scenarios if s in RQ3_SCENARIOS]
    if not rq3_s:
        print("  Warning: no RQ3 scenarios in selected set, using first 15")
        rq3_s = scenarios[:15]

    trials = []
    for m in models:
        for s in rq3_s:
            for cond in ["rq3_no_skill", "rq3_full_skill", "rq3_wrong_skill", "rq3_vaccinated"]:
                level = "L0_none" if cond == "rq3_no_skill" else "L4_full"
                trials.append(TrialConfig(
                    scenario_id=s, model=m, condition=cond,
                    skill_level=level,
                ))
    return trials


# ── Skill 序列化 ──

LEVEL_CONFIG = {
    "L0_none":         {"skill_md": False, "scripts": False, "references": False},
    "L1_skill_md":     {"skill_md": True,  "scripts": False, "references": False},
    "L2_plus_scripts": {"skill_md": True,  "scripts": True,  "references": False},
    "L3_no_assets":    {"skill_md": True,  "scripts": True,  "references": True},
    "L4_full":         {"skill_md": True,  "scripts": True,  "references": True},
}


def serialize_skill(skill_dir: Path, level: str) -> str:
    """将 skill 目录序列化为文本"""
    if level == "L0_none":
        return ""

    config = LEVEL_CONFIG[level]
    parts = []

    if config["skill_md"]:
        p = skill_dir / "SKILL.md"
        if p.exists():
            parts.append(f'<file path="SKILL.md">\n{p.read_text()}\n</file>')

    if config["scripts"]:
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for f in sorted(scripts_dir.glob("*")):
                if f.is_file():
                    try:
                        parts.append(f'<file path="scripts/{f.name}">\n{f.read_text()}\n</file>')
                    except UnicodeDecodeError:
                        parts.append(f'<file path="scripts/{f.name}">[binary]</file>')

    if config["references"]:
        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            for f in sorted(refs_dir.glob("*")):
                if f.is_file():
                    try:
                        parts.append(f'<file path="references/{f.name}">\n{f.read_text()}\n</file>')
                    except UnicodeDecodeError:
                        pass

    return "\n\n".join(parts)


# ── API 调用 ──

def call_llm(model_key: str, task_desc: str, skill_content: str | None,
             api_base: str, api_key: str) -> dict:
    """调用 LLM API"""
    import anthropic

    system = ""
    if skill_content:
        system = ("You are given the following skill package to guide your work. "
                  "Follow its instructions carefully.\n\n"
                  f"<skill-package>\n{skill_content}\n</skill-package>")

    client = anthropic.Anthropic(api_key=api_key, base_url=api_base)
    messages = [{"role": "user", "content": task_desc}]

    kwargs = {
        "model": MODEL_IDS[model_key],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    text = resp.content[0].text

    return {
        "response": text,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "stop_reason": resp.stop_reason,
    }


def extract_python_code(text: str) -> str:
    """从 LLM 回复中提取 Python 代码"""
    blocks = re.findall(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        blocks = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
    return max(blocks, key=len).strip() if blocks else ""


# ── 评估 ──

def evaluate_code(code: str, scenario_dir: Path, timeout: int = 60) -> dict:
    """在临时目录中执行生成的代码并运行测试"""
    test_script = scenario_dir / "test_script.py"
    if not test_script.exists():
        return {"passed": False, "n_pass": 0, "n_total": 0, "pass_rate": 0,
                "error_type": "no_test_script"}

    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入生成的代码
        code_file = Path(tmpdir) / "solution.py"
        code_file.write_text(code)

        # 复制测试脚本
        shutil.copy(test_script, tmpdir)

        # 运行测试
        try:
            result = subprocess.run(
                [sys.executable, "test_script.py"],
                cwd=tmpdir, capture_output=True, text=True, timeout=timeout
            )
            stdout = result.stdout
            stderr = result.stderr

            # 解析 PASS/FAIL
            passes = stdout.count("PASS:")
            fails = stdout.count("FAIL:")
            total = passes + fails
            if total == 0:
                total = 1

            return {
                "passed": fails == 0 and passes > 0,
                "n_pass": passes,
                "n_total": total,
                "pass_rate": passes / total if total > 0 else 0,
                "error_type": "success" if fails == 0 and passes > 0 else "test_failure",
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "n_pass": 0, "n_total": 1, "pass_rate": 0,
                    "error_type": "timeout"}
        except Exception as e:
            return {"passed": False, "n_pass": 0, "n_total": 1, "pass_rate": 0,
                    "error_type": str(type(e).__name__)}


# ── 主流程 ──

def run_experiment(trials: list[TrialConfig], api_base: str, api_key: str,
                   output_file: Path, dry_run: bool = False):
    """执行实验"""
    print(f"\n{'DRY RUN — ' if dry_run else ''}Running {len(trials)} trials")
    print(f"Output: {output_file}\n")

    # 加载已完成的 trials（支持断点续跑）
    completed = set()
    if output_file.exists():
        for line in output_file.read_text().strip().split("\n"):
            if line:
                try:
                    completed.add(json.loads(line)["trial_key"])
                except (json.JSONDecodeError, KeyError):
                    pass
        print(f"  Resuming: {len(completed)} trials already completed\n")

    skipped = 0
    for i, trial in enumerate(trials):
        if trial.trial_key in completed:
            skipped += 1
            continue

        tag = f"[{i+1}/{len(trials)}]"
        print(f"  {tag} {trial.model:12s} {trial.scenario_id:25s} {trial.condition:30s}", end="", flush=True)

        if dry_run:
            print(" (dry run)")
            continue

        # 加载 task
        scenario_dir = SCENARIOS_DIR / trial.scenario_id
        task_path = scenario_dir / "task.md"
        if not task_path.exists():
            print(f" SKIP (no task.md at {scenario_dir})")
            continue
        task_desc = task_path.read_text()

        # 准备 skill
        skill_content = None
        if trial.skill_level != "L0_none":
            skill_dir = SKILLS_DIR / trial.scenario_id / "direct"
            if skill_dir.exists():
                skill_content = serialize_skill(skill_dir, trial.skill_level)

        if trial.condition == "rq3_vaccinated" and skill_content:
            skill_content = VACCINATION_PREFIX + "\n\n" + skill_content

        # 调用 API
        try:
            api_result = call_llm(trial.model, task_desc, skill_content, api_base, api_key)
        except Exception as e:
            print(f" API ERROR: {e}")
            continue

        # 提取代码
        code = extract_python_code(api_result["response"])
        if not code:
            print(f" NO CODE")
            result = {
                "trial_key": trial.trial_key,
                "trial_config": asdict(trial),
                "eval": {"passed": False, "n_pass": 0, "n_total": 0,
                         "pass_rate": 0, "error_type": "format_error"},
                **{k: v for k, v in api_result.items() if k != "response"},
            }
        else:
            # 评估
            eval_result = evaluate_code(code, scenario_dir)
            result = {
                "trial_key": trial.trial_key,
                "trial_config": asdict(trial),
                "eval": eval_result,
                "code_length": len(code),
                **{k: v for k, v in api_result.items() if k != "response"},
            }
            status = "PASS" if eval_result["passed"] else f"FAIL ({eval_result['error_type']})"
            print(f" {status} ({eval_result['n_pass']}/{eval_result['n_total']})")

        # 写入结果
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "a") as f:
            f.write(json.dumps(result, default=str) + "\n")

    if skipped:
        print(f"\n  Skipped {skipped} already-completed trials")


def main():
    parser = argparse.ArgumentParser(
        description="SkillBench: Reproduce the full experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run
  python run_benchmark.py --dry-run

  # Run RQ1 on 2 models, 3 scenarios
  python run_benchmark.py --rq rq1 --models haiku,gpt4o \\
      --scenarios S002_spike_behavior,S012_uv_spectroscopy,S017_ctd_ocean \\
      --api-base "https://api.anthropic.com" --api-key "$KEY"

  # Full reproduction (~$130)
  python run_benchmark.py --rq all --api-base "..." --api-key "..."
""")
    parser.add_argument("--rq", choices=["rq1", "rq2", "rq3", "all"], default="all",
                        help="Which research question(s) to run")
    parser.add_argument("--models", type=str, default=",".join(ALL_MODELS),
                        help=f"Comma-separated model list (default: all 6)")
    parser.add_argument("--scenarios", type=str, default=None,
                        help="Comma-separated scenario IDs (default: all 30)")
    parser.add_argument("--api-base", type=str, default="https://api.anthropic.com",
                        help="API base URL")
    parser.add_argument("--api-key", type=str, default=os.environ.get("ANTHROPIC_API_KEY", ""),
                        help="API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--output", type=str, default="results/benchmark_results.jsonl",
                        help="Output JSONL file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print trial plan without executing")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",")]
    scenarios = [s.strip() for s in args.scenarios.split(",")] if args.scenarios else EXPERIMENT_SCENARIOS

    # 验证
    for m in models:
        if m not in MODEL_IDS:
            parser.error(f"Unknown model: {m}. Choose from: {list(MODEL_IDS.keys())}")

    if not args.dry_run and not args.api_key:
        parser.error("--api-key required (or set ANTHROPIC_API_KEY)")

    # 生成 trials
    trials = []
    if args.rq in ("rq1", "all"):
        t = generate_rq1_trials(models, scenarios)
        print(f"RQ1: {len(t)} trials ({len(models)} models × {len(scenarios)} scenarios × 5 levels)")
        trials.extend(t)
    if args.rq in ("rq2", "all"):
        t = generate_rq2_trials(models, scenarios)
        print(f"RQ2: {len(t)} trials")
        trials.extend(t)
    if args.rq in ("rq3", "all"):
        t = generate_rq3_trials(models, scenarios)
        print(f"RQ3: {len(t)} trials")
        trials.extend(t)

    print(f"\nTotal: {len(trials)} trials")

    if args.dry_run:
        print("\n--- Dry Run Summary ---")
        from collections import Counter
        by_model = Counter(t.model for t in trials)
        by_cond = Counter(t.condition for t in trials)
        print("\nBy model:")
        for m, c in by_model.most_common():
            print(f"  {m}: {c}")
        print("\nBy condition:")
        for cond, c in by_cond.most_common():
            print(f"  {cond}: {c}")
        print(f"\nEstimated cost: ~${len(trials) * 0.08:.0f}")
        return

    output_file = Path(args.output)
    run_experiment(trials, args.api_base, args.api_key, output_file, dry_run=False)

    print(f"\nDone! Results saved to {output_file}")


if __name__ == "__main__":
    main()
