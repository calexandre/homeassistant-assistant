---
name: ha-release-benchmark
description: >-
  Benchmark multiple AI model outputs from the ha-release-notes prompt against
  ground truth built from the user's live HA setup. Discovers model results,
  builds a release-specific scoring spec, evaluates each model on 7 weighted
  dimensions, and writes a ranked comparison. Use when user wants to compare,
  evaluate, score, or benchmark release note summaries from different models,
  or says "benchmark", "compare models", "score the results".
---

# HA Release Notes Benchmark

## Gate check

Scan `.temp/<version>/` for subdirectories containing `ha-release-<version>.md`.
**Refuse to run if fewer than 2 model outputs are found.**
Report which models were detected and stop.

## Quick start

```text
User: benchmark the 2026.5 release note results
→ Skill detects .temp/2026.5/gemini31/ and .temp/2026.5/kimi26/
→ Builds ground-truth spec → Scores both → Writes results
```

## Workflow

### Step 1 — Build ground-truth spec

1. Accept HA release version from user (e.g. `2026.5`)
2. Discover models: list dirs in `.temp/<version>/` with `ha-release-<version>.md`
3. Fetch the release blog post from `https://www.home-assistant.io/blog/`
4. Call `GetLiveContext` for live entity/device/area data
5. Read `ha-data/automations.yaml`, `scenes.yaml`, `scripts.yaml`, `configuration.yaml`
6. Extract from the release blog:
   - Every feature highlight (with anchor IDs)
   - Every new integration
   - Every integration improvement
   - Every breaking change
7. Cross-reference each item against the setup:
   - **Relevant** — integration/entity/automation exists
   - **Potentially relevant** — related category exists
   - **Not relevant** — no overlap
8. Identify known non-matches (things models must NOT claim exist)
9. Identify automations using standard state `for:` triggers vs
   purpose-specific triggers (models must not confuse these)
10. Write spec to `.temp/<version>/ha-release-<version>-benchmark-spec.md`

### Step 2 — Score each model

Read each model output. Score 7 dimensions using rubrics in
[REFERENCE.md](REFERENCE.md):

| Dim | Name | Weight |
|---|---|---|
| D1 | Coverage | 15% |
| D2 | Factual Accuracy | 25% |
| D3 | Personalization Depth | 20% |
| D4 | Technical Correctness | 15% |
| D5 | Breaking Changes Rigor | 10% |
| D6 | Actionability | 10% |
| D7 | Format Compliance | 5% |

Weighted score formula: `(score / 5) × weight × 100`

For each model and dimension: list evidence, assign 0-5, calculate weighted.

### Step 3 — Write results

Write to `.temp/<version>/ha-release-<version>-benchmark-results.md` using the
output template in [REFERENCE.md](REFERENCE.md). Must include:

- Per-model evaluation with cited evidence
- Comparative summary table
- Ranked list with 1-sentence verdict per model
- Dimension winners
- Key observations

## Rules

- **Never fabricate ground truth.** Every fact must trace to the release blog,
  `GetLiveContext`, or `ha-data/*.yaml`.
- **Cite evidence.** Quote model text and ground-truth source when scoring.
- **Distinguish trigger types.** Standard state triggers with `for:` are NOT
  purpose-specific triggers. Penalize models that confuse these in D4.
- **Flag hallucinations.** If a model claims a device/integration exists but
  it doesn't, list it explicitly.
- **Output to `.temp/` only.** Never write benchmark files elsewhere.
