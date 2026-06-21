# Reference: Scoring Rubrics and Output Templates

## Scoring Rubrics

### D1 — 📊 Coverage (15%)

How many release features, new integrations, integration improvements,
and breaking changes did the model include?

- **0** 🔴 — Fewer than 30% of release highlights covered
- **1** 🟠 — 30-50% covered
- **2** 🟡 — 50-65% covered
- **3** 🟢 — 65-80% covered
- **4** 🟢 — 80-95% covered
- **5** 🏆 — 95%+ of all highlights, integrations, and breaking changes covered

Count method: tally features in the release blog, then check which ones
appear in the model's output. Calculate `covered / total`.

### D2 — 🎯 Factual Accuracy (25%)

Are claims about the user's setup correct? Cross-reference every entity ID,
automation alias, integration name, and device reference against
`GetLiveContext` and config snapshots fetched via the `ha-config-fetch` skill.

- **0** 🔴 — Multiple fabricated setup details (hallucinated devices/integrations)
- **1** 🟠 — 1-2 fabricated details plus multiple minor inaccuracies
- **2** 🟡 — No fabrications but several incorrect claims
- **3** 🟢 — No fabrications, 1-2 minor inaccuracies
- **4** 🟢 — All setup references verified correct, minor imprecision in feature descriptions
- **5** 🏆 — Every claim about the setup and every feature description is verifiably accurate

Key checks:

- Does the model reference integrations/devices that don't exist in the setup?
- Are automation aliases spelled correctly and matched to the right behavior?
- Are entity IDs valid and in the correct domain?

### D3 — 🏠 Personalization Depth (20%)

How specifically does the model connect release features to the user's
actual automations, devices, and workflows?

- **0** 🔴 — Generic descriptions with no setup references
- **1** 🟠 — Mentions area/device names but no specific automations or entity IDs
- **2** 🟡 — References some automations by alias but doesn't explain the connection
- **3** 🟢 — Names specific automations/entities and explains how the feature relates
- **4** 🟢 — Provides actionable advice tied to specific automations with correct technical detail
- **5** 🏆 — Deep cross-referencing: names automations, quotes trigger/condition patterns,
  explains exactly what changes and why

### D4 — 🔧 Technical Correctness (15%)

When the model explains how a feature applies to the setup, is the
technical reasoning sound?

- **0** 🔴 — Fundamental misunderstanding of HA concepts
- **1** 🟠 — Multiple technical errors in feature-to-setup mapping
- **2** 🟡 — Mostly correct but misclassifies trigger types or misapplies feature scope
- **3** 🟢 — Sound reasoning with 1-2 edge-case errors
- **4** 🟢 — Technically correct throughout, minor imprecision
- **5** 🏆 — Flawless technical analysis

Common pitfalls to check:

- Confusing standard state triggers with `for:` vs purpose-specific triggers
- Misidentifying integration backends (e.g., Tuya device claimed as ESPHome)
- Confusing `delay` actions with trigger durations
- Misattributing entity domains

### D5 — ⚠️ Breaking Changes Rigor (10%)

How thoroughly does the model assess backward-incompatible changes?

- **0** 🔴 — Breaking changes section missing or copy-pasted
- **1** 🟠 — Lists breaking changes but doesn't check against setup
- **2** 🟡 — Checks some breaking changes, misses others
- **3** 🟢 — Checks all, provides Yes/No but limited explanation
- **4** 🟢 — Checks all, explains why each does/doesn't apply with config references
- **5** 🏆 — Checks all, cites specific YAML lines/entities, explains migration path

### D6 — ✅ Actionability (10%)

Does the output tell the user what to do after updating?

- **0** 🔴 — No action items
- **1** 🟠 — Generic "safe to update" without specifics
- **2** 🟡 — Mentions a few things to check post-update
- **3** 🟢 — Lists concrete follow-up actions tied to setup
- **4** 🟢 — Prioritized action list with specific automations/entities to review
- **5** 🏆 — Step-by-step post-update checklist with entities, expected new features,
  and optional improvements

### D7 — 📝 Format Compliance (5%)

Does the output follow the `ha-release-notes` prompt's format spec?

- **0** 🔴 — Ignores the format entirely
- **1** 🟠 — Partial structure, missing major sections
- **2** 🟡 — All sections present but uses tables where bullet points are required
- **3** 🟢 — Correct structure, minor formatting issues
- **4** 🟢 — Fully compliant, all section links work, proper markdown
- **5** 🏆 — Perfect compliance: correct headings, linked feature names, no tables,
  proper front matter

Format spec requirements (from the prompt):

- Use only headings and bullet points (NO markdown tables)
- Feature names must be clickable links to release note anchors
- Sections: features, new integrations, integration improvements,
  breaking changes, update recommendation
- Front matter with required fields

## Benchmark Spec Template

Use this template when writing `.temp/<version>/ha-release-<version>-benchmark-spec.md`.

````markdown
---
release_version: "<VERSION>"
release_date: "<DATE>"
release_url: "<URL>"
spec_generated: "<TIMESTAMP>"
models_detected:
  - model_1
  - model_2
---

## Features in Release

<!-- Every highlight section from the release blog -->
- [ ] Feature 1 (`#anchor-id`) — 🟢 Relevant / 🟡 Potentially relevant / ⚪ Not relevant
- [ ] Feature 2 (`#anchor-id`) — ...

## New Integrations in Release

- [ ] Integration 1 — 🟢 Relevant / ⚪ Not relevant — reason
- [ ] Integration 2 — ...

## Integration Improvements in Release

- [ ] Integration 1: description — 🟢 Relevant / ⚪ Not relevant — reason
- [ ] Integration 2: ...

## Breaking Changes in Release

- [ ] Breaking change 1 — Affects setup: ❌ Yes / ✅ No — evidence
- [ ] Breaking change 2 — ...

## Setup Cross-Reference

### Integrations Confirmed in Setup

- integration_name — evidence (entity IDs, YAML references)

### Automations Relevant to This Release

- alias: "Name" — why relevant to release features

### Entities Relevant to This Release

- entity_id — why relevant

### Known Non-Matches

<!-- Things models must NOT claim exist in the setup -->
- integration_x: NOT present — checked GetLiveContext and the `ha-config-fetch` skill snapshots
- device_y: NOT present

### Trigger Type Classification

<!-- For releases with trigger-related features -->
- alias: "Name" — trigger type: standard state with `for:` / purpose-specific / delay action
````

## Benchmark Results Template

Use this template when writing `.temp/<version>/ha-release-<version>-benchmark-results.md`.

````markdown
---
release_version: "<VERSION>"
benchmark_date: "<DATE>"
models_evaluated:
  - model_1
  - model_2
spec_file: "ha-release-<VERSION>-benchmark-spec.md"
---

## Model: <MODEL_NAME>

### Output File

`.temp/<VERSION>/<model-name>/ha-release-<VERSION>.md`

### Scores

| Dimension | Score (0-5) | Weight | Weighted |
|---|---|---|---|
| 📊 D1 Coverage | X | 15% | X.X |
| 🎯 D2 Factual Accuracy | X | 25% | X.X |
| 🏠 D3 Personalization Depth | X | 20% | X.X |
| 🔧 D4 Technical Correctness | X | 15% | X.X |
| ⚠️ D5 Breaking Changes Rigor | X | 10% | X.X |
| ✅ D6 Actionability | X | 10% | X.X |
| 📝 D7 Format Compliance | X | 5% | X.X |
| **Total** | | | **X.X / 100** |

### 📊 D1 Coverage Notes

- Features covered: X / Y
- New integrations covered: X / Y
- Integration improvements covered: X / Y
- Breaking changes covered: X / Y
- Notable omissions: ...

### 🎯 D2 Factual Accuracy Notes

- Fabricated claims: ...
- Incorrect references: ...
- Verified correct references: ...

### 🏠 D3 Personalization Depth Notes

- Automations named: ...
- Entity IDs referenced: ...
- Quality of mapping: ...

### 🔧 D4 Technical Correctness Notes

- Trigger type errors: ...
- Feature scope misapplications: ...
- Correct technical insights: ...

### ⚠️ D5 Breaking Changes Notes

- Breaking changes checked: X / Y
- False negatives: ...
- False positives: ...

### ✅ D6 Actionability Notes

- Post-update actions listed: ...
- Specificity: ...

### 📝 D7 Format Compliance Notes

- Missing sections: ...
- Link quality: ...
- Table/bullet compliance: ...

### 💪 Strengths

- ...

### 👎 Weaknesses

- ...

### 🚨 Notable Hallucinations

- ...

---

<!-- Repeat the above block for each model -->

## 🏁 Comparative Summary

### Final Scores

| Model | 📊 D1 | 🎯 D2 | 🏠 D3 | 🔧 D4 | ⚠️ D5 | ✅ D6 | 📝 D7 | Total |
|---|---|---|---|---|---|---|---|---|
| model_1 | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X / 100 |
| model_2 | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X / 100 |

### 🥇 Ranking

1. **Model X** — Total: XX.X/100 — [1-sentence verdict]
2. **Model Y** — Total: XX.X/100 — [1-sentence verdict]

### 🏅 Dimension Winners

| Dimension | Best Model | Why |
|---|---|---|
| 📊 D1 Coverage | | |
| 🎯 D2 Factual Accuracy | | |
| 🏠 D3 Personalization | | |
| 🔧 D4 Technical Correctness | | |
| ⚠️ D5 Breaking Changes | | |
| ✅ D6 Actionability | | |
| 📝 D7 Format Compliance | | |

### 💡 Key Observations

- ...
- ...
- ...
````
