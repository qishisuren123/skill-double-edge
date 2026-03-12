# Deep Dive: The Seven Paradoxes of LLM Skills

*Findings from the pilot experiment (10 scenarios × 6 models) that shaped the full study.*

---

## Paradox 1: The Skill Paradox

Weak models are simultaneously the **biggest beneficiary** and the **biggest victim** of skills.

| Model | Best Skill Effect | Worst Skill Effect |
|-------|------------------|--------------------|
| Haiku | S03: +12pp | **S08: -100pp** |
| GPT-4o-mini | S08: +100pp | **S09: -83pp** |
| GPT-4.1-mini | S05: +100pp | **S04: -100pp** |
| Gemini Flash | S01: +100pp | (no harm) |
| Sonnet | 0pp (all) | 0pp (all) |
| Opus | 0pp (all) | 0pp (all) |

Each weak model has scenarios where skills take it from 0% → 100%, and other scenarios where skills take it from 100% → 0%. **The same mechanism that enables knowledge transfer also enables knowledge poisoning.**

---

## Paradox 2: Exact Match > Near Miss Danger

A skill written *for the exact task* is **more dangerous** than a completely unrelated skill.

**S08 Haiku experiment:**

| Condition | Score |
|-----------|-------|
| No skill | 7/7 (100%) |
| Exact-match skill (Sonnet-authored) | **0/7 (0%)** |
| Wrong-domain skill (S09's skill) | 7/7 (100%) |

The model ignores irrelevant skills entirely, but tries hard to follow relevant ones — introducing fatal adaptation errors in the process.

---

## Paradox 3: The Strongest Models Are Most Vulnerable to Poison

We injected deliberately bad advice into skills ("always convert numbers to strings", "for loops are faster than numpy"):

| Model | Clean Skill | Poisoned Skill | Δ |
|-------|-------------|---------------|---|
| Haiku | 6/6 | 5/6 | -1 |
| Sonnet | 5/6 | 5/6 | 0 |
| **Opus** | **5/6** | **0/6** | **-5** |

**Opus, the most capable model, suffered the most damage.** Its superior instruction-following ability becomes a liability — it faithfully executes every piece of advice, including the malicious ones. Haiku's limited ability to implement complex instructions accidentally protects it.

---

## Paradox 4: Author-Specificity of Toxicity

Skill toxicity depends on the specific author-user combination:

**Haiku using skills by different authors (S08):**

| Skill Author | Haiku Score |
|-------------|-------------|
| No skill | 7/7 (100%) |
| Haiku-authored | 7/7 (100%) |
| **Sonnet-authored** | **0/7 (0%)** |
| Opus-authored | 7/7 (100%) |

**Sonnet using skills by different authors (S02):**

| Skill Author | Sonnet Score |
|-------------|--------------|
| No skill | 9/9 (100%) |
| Haiku-authored | 9/9 (100%) |
| Sonnet-authored | 9/9 (100%) |
| **Opus-authored** | **0/9 (0%)** |

**Mechanism:** Higher-capability authors embed "expert" API choices (e.g., `squeeze_me=True`) that lower-capability consumers faithfully follow but cannot handle the downstream consequences of.

---

## Paradox 5: Partial Skills Can Be More Dangerous Than Complete Skills

**S09 Haiku ablation:**

| Condition | Score |
|-----------|-------|
| No skill | 6/6 |
| Full skill | 6/6 |
| First half only | **0/6** |
| Second half only | 6/6 |
| Overview only | 5/6 |

The first half contained toxic code patterns (deprecated pandas APIs). The second half's additional context **neutralized** the toxicity. Removing context made the skill *more* dangerous, not less.

---

## Paradox 6: Skills Increase Defensive Coding — But Not Always Helpfully

| Metric | Without Skill | With Skill | Change |
|--------|--------------|------------|--------|
| Lines of code | 283 avg | 287 avg | +1.4% |
| try/except blocks | 3.6 avg | 4.6 avg | **+28%** |
| Defensive ratio | 0.48 | 0.63 | **+31%** |

Skills make models write more defensively, but over-defense (catching errors too broadly) sometimes masks real bugs that would have been caught by test assertions.

---

## The Four Toxicity Mechanisms

| # | Mechanism | Example | Root Cause |
|---|----------|---------|------------|
| T1 | **Adaptation Error** | Haiku S08: `enumerate(1, start=1)` instead of `enumerate(f, start=1)` | Model attempts to adapt reference code pattern but introduces typo |
| T2 | **Stale API** | GPT-4o-mini S09: uses deprecated `infer_datetime_format` | Skill contains outdated code, weak model copies uncritically |
| T3 | **Dangerous Default** | Sonnet + Opus skill: `squeeze_me=True` breaks validation | Expert API option works in skill author's context but not consumer's |
| T4 | **Library Dependency** | GPT-4o-mini S08: `import jsonlines` (not installed) | Model's own bad habit; skill *fixes* this by providing stdlib pattern |

T1–T3 are skill-induced harm. T4 is skill-*cured* harm. The distinction matters: skills both create and solve problems, depending on the scenario and model.
