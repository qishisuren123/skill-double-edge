#!/usr/bin/env python3
"""
从原始 JSONL 导出用于发布的 CSV 数据文件。
去除敏感字段 (API key, cost_usd, stdout/stderr 等)。
"""

import json
import csv
import os
import yaml
import sys

RESULTS_JSONL = os.path.join(os.path.dirname(__file__),
    "../../pilot_experiment/results/experiment_results.jsonl")
SCENARIOS_DIR = os.path.join(os.path.dirname(__file__),
    "../../pilot_experiment/scenarios")
OUT_DIR = os.path.join(os.path.dirname(__file__), "../data")


def export_experiment_results():
    """导出实验结果 CSV，去除敏感字段"""
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    with open(RESULTS_JSONL) as f:
        for line in f:
            d = json.loads(line)
            tc = d.get("trial_config", {})
            ev = d.get("eval", {})
            cm = d.get("code_metrics", {})

            row = {
                "trial_key": d.get("trial_key", ""),
                "model": d.get("model", ""),
                "scenario": d.get("scenario", ""),
                "condition": d.get("condition", ""),
                "skill_level": tc.get("skill_level", ""),
                "skill_method": tc.get("skill_method", ""),
                "mutation_type": tc.get("mutation_type", ""),
                "temperature": d.get("temperature", 0),
                "run_id": d.get("run_id", 0),
                "skill_tokens": d.get("skill_tokens", 0),
                # 评估结果
                "passed": ev.get("passed", False),
                "n_pass": ev.get("n_pass", 0),
                "n_total": ev.get("n_total", 0),
                "pass_rate": ev.get("pass_rate", 0),
                "error_type": ev.get("error_type", ""),
                # 代码指标（不含敏感信息）
                "code_lines": cm.get("total_lines", 0),
                "code_length": d.get("code_length", 0),
                "import_count": cm.get("import_count", 0),
                "function_count": cm.get("function_count", 0),
                "try_except_count": cm.get("try_except_count", 0),
                "has_argparse": cm.get("has_argparse", False),
                # token 统计（不含费用）
                "input_tokens": d.get("input_tokens", 0),
                "output_tokens": d.get("output_tokens", 0),
            }
            rows.append(row)

    out_path = os.path.join(OUT_DIR, "experiment_results.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✓ {out_path} ({len(rows)} rows)")
    return rows


def export_scenarios_meta():
    """导出场景元数据 CSV"""
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    if not os.path.isdir(SCENARIOS_DIR):
        print(f"  ✗ Scenarios dir not found: {SCENARIOS_DIR}")
        return

    for name in sorted(os.listdir(SCENARIOS_DIR)):
        scenario_dir = os.path.join(SCENARIOS_DIR, name)
        yaml_path = os.path.join(scenario_dir, "scenario.yaml")
        task_path = os.path.join(scenario_dir, "task.md")

        if not os.path.isfile(yaml_path):
            continue

        with open(yaml_path) as f:
            meta = yaml.safe_load(f)

        task_text = ""
        if os.path.isfile(task_path):
            with open(task_path) as f:
                task_text = f.read().strip()

        rows.append({
            "scenario_id": meta.get("id", name),
            "name": meta.get("name", ""),
            "domain": meta.get("domain", ""),
            "difficulty": meta.get("difficulty", ""),
            "source": meta.get("source", ""),
            "required_packages": ", ".join(meta.get("required_packages", [])),
            "task_description": task_text[:200] + ("..." if len(task_text) > 200 else ""),
            "n_tests": 0,  # 后面填充
        })

    out_path = os.path.join(OUT_DIR, "scenarios_meta.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✓ {out_path} ({len(rows)} rows)")


def main():
    print("Exporting data ...")
    export_experiment_results()
    export_scenarios_meta()
    print("Done!")


if __name__ == "__main__":
    main()
