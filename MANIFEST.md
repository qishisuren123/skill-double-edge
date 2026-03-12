# MANIFEST.md — Dataset Card & Reproducibility Protocol

## Dataset Scope

This section clarifies the relationship between the **internal experiment codebase** and the **public release**.

| Asset | Internal | Public (this repo) | Notes |
|-------|----------|---------------------|-------|
| Scenario definitions | 100 | 10 (examples) | Internal set covers 15+ scientific domains |
| Skill packages | 51 | 5 (examples) | Each with SKILL.md, scripts/, references/ |
| Scenarios in main experiment | **30** | 30 (all results) | `data/experiment_results.csv` covers all 30 |
| Models | 6 | 6 (all results) | All 6 model results are published |
| Conditions | 15 | 15 (all results) | All conditions are published |
| Total trials | **1,620** | **1,620** (all results) | Every trial result is published |
| Raw LLM responses | 1,620 | 0 | Excluded (contain generated code, too large) |
| Cost log | 1,620 entries | 0 | Excluded (sensitive) |
| API config | 1 | 0 | Excluded (contains API key) |

### Why 100 scenarios but only 30 in the experiment?

We created 100 candidate scenarios as a scenario pool during development. After piloting and quality filtering, **30 scenarios** were selected for the main experiment based on:
- Clear, unambiguous task specification
- Automated test suite with 5–15 assertions
- No reliance on external data downloads at runtime
- Coverage across diverse scientific domains

The 10 example scenarios in `scenarios/` are a representative subset of these 30; the full 30-scenario results are in `data/experiment_results.csv`.

### Why 51 skills but only 5 in this repo?

Each of the 30 experiment scenarios has a corresponding skill package (some have both "direct" and "pipeline" variants). We publish 5 representative examples to show the structure. The full skill content is reflected in the experimental results.

---

## Trial Coverage Table

All 1,620 trials form a **balanced design within each RQ**. Every (model, scenario, condition) cell has exactly **1 trial** (temperature=0.0, run_id=0).

### RQ1: Skill Completeness — 900 trials

6 models × 30 scenarios × 5 levels = **900 trials**

| | L0 (none) | L1 (SKILL.md) | L2 (+scripts) | L3 (+refs) | L4 (full) |
|---|:-:|:-:|:-:|:-:|:-:|
| Haiku 3.5 | 30 | 30 | 30 | 30 | 30 |
| GPT-4o | 30 | 30 | 30 | 30 | 30 |
| GPT-4.1 | 30 | 30 | 30 | 30 | 30 |
| Gemini 2.0 Pro | 30 | 30 | 30 | 30 | 30 |
| Sonnet 3.5 | 30 | 30 | 30 | 30 | 30 |
| Opus 3.5 | 30 | 30 | 30 | 30 | 30 |

### RQ2: Error Tolerance — 360 trials

6 models × 10 scenarios × 6 conditions = **360 trials**

Scenarios (subset): S002, S005, S007, S011, S012, S017, S026, S028, S030, S033

| | clean | logic_error | missing_edge | stale_api | wrong_default | wrong_import |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Haiku 3.5 | 10 | 10 | 10 | 10 | 10 | 10 |
| GPT-4o | 10 | 10 | 10 | 10 | 10 | 10 |
| GPT-4.1 | 10 | 10 | 10 | 10 | 10 | 10 |
| Gemini 2.0 Pro | 10 | 10 | 10 | 10 | 10 | 10 |
| Sonnet 3.5 | 10 | 10 | 10 | 10 | 10 | 10 |
| Opus 3.5 | 10 | 10 | 10 | 10 | 10 | 10 |

### RQ3: Wrong Skills & Vaccination — 360 trials

6 models × 15 scenarios × 4 conditions = **360 trials**

Scenarios (subset): S002, S005, S007, S011, S012, S017, S026, S028, S030, S033, S036, S037, S044, S045, S048

| | no_skill | full_skill | wrong_skill | vaccinated |
|---|:-:|:-:|:-:|:-:|
| Haiku 3.5 | 15 | 15 | 15 | 15 |
| GPT-4o | 15 | 15 | 15 | 15 |
| GPT-4.1 | 15 | 15 | 15 | 15 |
| Gemini 2.0 Pro | 15 | 15 | 15 | 15 |
| Sonnet 3.5 | 15 | 15 | 15 | 15 |
| Opus 3.5 | 15 | 15 | 15 | 15 |

### Grand Total: 900 + 360 + 360 = **1,620 trials** (non-overlapping)

---

## Reproducibility Protocol

### Model Versions

All experiments were run between March 10–11, 2026, via an OpenAI-compatible API gateway.

| Short Name | API Model ID | Provider | Tier |
|------------|-------------|----------|------|
| haiku | `claude-haiku-4-5-20251001` | Anthropic | weak |
| sonnet | `claude-sonnet-4-20250514` | Anthropic | medium |
| opus | `claude-opus-4-20250514` | Anthropic | strong |
| gpt4o | `gpt-4o` | OpenAI | medium |
| gpt41 | `gpt-4.1` | OpenAI | strong |
| gemini_pro | `gemini-2.5-pro` | Google | strong |

### Generation Parameters

| Parameter | Value |
|-----------|-------|
| Temperature | **0.0** (deterministic) |
| Max tokens | **8,192** |
| Runs per cell | **1** (single run; deterministic at temp=0) |
| Random seed (mutations) | **42** |

### Prompt Template

The system prompt (when a skill is provided):

```
You are given the following skill package to guide your work.
Follow its instructions carefully.

<skill-package>
{serialized_skill_content}
</skill-package>
```

The user message is the raw `task.md` content for each scenario — no additional framing.

When no skill is provided (L0), the system prompt is empty.

### Skill Injection Method

Skills are serialized from their directory structure into a single text block using `<file>` tags:

```xml
<file path="SKILL.md">
...SKILL.md content...
</file>
<file path="scripts/main.py">
...script content...
</file>
<file path="references/api_notes.md">
...reference content...
</file>
```

The completeness level controls which files are included (see README for L0–L4 definitions).

### Vaccination Prefix (RQ3)

```
WARNING: The following skill may contain outdated patterns or deprecated APIs.
Only follow advice you can independently verify as correct.
When in doubt, prefer standard library defaults and well-documented approaches.
```

### Evaluation Pipeline

1. LLM generates Python code in response to `task.md`
2. Code is extracted from the response (longest `python` fenced block)
3. Code is written to a temp file and executed with the scenario's `test_script.py`
4. Test script produces PASS/FAIL for each assertion + numeric scores
5. `pass_rate = n_pass / n_total`; `passed = (n_pass == n_total)`

### Execution Environment

- Python 3.11 (conda)
- Ubuntu 22.04 (PJLab cluster)
- Each trial runs in an isolated temp directory
- No internet access during code execution
- Timeout: 60 seconds per trial

---

## Result Schema

Each row in `data/experiment_results.csv` contains:

| Column | Type | Description |
|--------|------|-------------|
| `trial_key` | str | Unique ID: `{scenario}__{model}__{condition}__t{temp}__r{run_id}` |
| `model` | str | Model short name (haiku, gpt4o, ...) |
| `scenario` | str | Scenario ID (S002_spike_behavior, ...) |
| `condition` | str | Experimental condition (L0_none, mutated_wrong_import, rq3_vaccinated, ...) |
| `skill_level` | str | Completeness level (L0_none through L4_full) |
| `skill_method` | str | Skill source (none, direct, pipeline) |
| `mutation_type` | str | Error type injected (none, logic_error, wrong_import, ...) |
| `temperature` | float | Generation temperature (always 0.0) |
| `run_id` | int | Run index (always 0 in this release) |
| `skill_tokens` | int | Estimated token count of injected skill content |
| `passed` | bool | Whether all test assertions passed |
| `n_pass` | int | Number of assertions passed |
| `n_total` | int | Total number of assertions |
| `pass_rate` | float | `n_pass / n_total` |
| `error_type` | str | Failure category (success, import_error, runtime_error, logic_error, ...) |
| `code_lines` | int | Total lines in generated code |
| `code_length` | int | Character count of generated code |
| `import_count` | int | Number of import statements |
| `function_count` | int | Number of function definitions |
| `try_except_count` | int | Number of try/except blocks |
| `has_argparse` | bool | Whether code uses argparse |
| `input_tokens` | int | API input token count |
| `output_tokens` | int | API output token count |

### Excluded Fields (present in internal data, removed for publication)

| Field | Reason |
|-------|--------|
| `cost_usd` | Sensitive (reveals API pricing structure) |
| `response` | Too large (~10KB per trial), stored in raw/ internally |
| `stdout` / `stderr` | Too large, contains file paths |
| `eval.details` | Per-assertion breakdown (available on request) |

---

## File Integrity

| File | SHA-256 |
|------|---------|
| `data/experiment_results.csv` | `17a2eea25d64dd79475ce9ef4847e1a7ce2a0ec544bf9806ac9b92f31775786d` |

To verify:
```bash
sha256sum data/experiment_results.csv
```
