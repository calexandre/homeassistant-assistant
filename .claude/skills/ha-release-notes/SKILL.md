---
name: ha-release-notes
description: >-
  Compares a Home Assistant release against the live setup and produces a
  personalized summary of highlights, new integrations, improvements, and
  breaking changes, saving the result to ha-release-notes/ha-release-[VERSION].md.
  Use when the user wants a release summary tailored to their actual devices,
  automations, scenes, scripts, and configuration.
disable-model-invocation: true
---

# HA Release Notes

## When to use

- The user wants a personalized summary of a Home Assistant release based on the current live setup.
- The request includes a release notes URL or no URL, in which case the latest release from the HA blog should be used.
- The user wants highlights, new integrations, integration improvements, or backward-incompatible change impact assessed against their actual devices, automations, scenes, scripts, and configuration.

## Input

- Release URL: provide the exact Home Assistant blog URL for the release notes.
- No URL provided: use the latest release from `https://www.home-assistant.io/blog/`.

## Workflow

### Step 1 — Get current setup context

1. Call `GetLiveContext` to retrieve all devices, entities, and areas in the Home Assistant instance.
2. Note the integrations, device types, and domains in use.
3. Treat this as the ground truth for personalization.

### Step 2 — Fetch Home Assistant config snapshots

1. Invoke the `ha-config-fetch` skill to refresh and read the latest automations, scenes, scripts, configuration YAML, and logs from the live instance.
2. Note all integrations, services, entity IDs, triggers, conditions, and actions referenced in the config files.
3. Use this information to check whether a breaking change or deprecated feature is actually used.

### Step 3 — Fetch release notes

1. Fetch the release notes page from the provided URL.
2. Extract all highlights, new integrations, improvements, and breaking changes.
3. Capture section anchors: record the HTML anchor IDs for each highlight section, such as `#home-dashboard-improvements` or `#new-integrations`.
4. Prefer the official Home Assistant release page as the source of truth.

### Step 4 — Generate the personalized summary

For each major highlight, include:

- Feature name: a brief description with a clickable link to the release notes section anchor.
- What's New: 1-2 sentences explaining the feature.
- Hint for Your Setup: a short explanation of how it could help the user's specific devices or areas.

### Step 5 — Review new integrations

- List new integrations that could be relevant to the current setup.
- Highlight any integration that matches the user's existing device categories.
- Link each relevant integration to its documentation or release section.

### Step 6 — Review integration improvements

- Focus on improvements to integrations already in use.
- Note any changes that affect the current devices or automations.
- Link each improvement to the relevant section in the release notes.

### Step 7 — Assess backward-incompatible changes

Cross-reference each breaking change against both the live entity context and the fetched config files.

For each breaking change, confirm:

- Integration name
- Affects You? Yes or No
- Config impact: list the automations, scenes, or scripts that reference the affected integration or deprecated feature
- Action required: what to change and which config files need updates

A breaking change counts as affecting the user only if the integration, service, entity ID, or deprecated feature appears in the live entity state or in the fetched YAML files.

## Output format

Use only headings and bullet points throughout the entire report. Do not use markdown tables in any section.

```markdown
# 🏠 Release Summary for [Version]

## [Feature Name](URL#anchor)
- **What's New**: 1-2 sentence explanation of the feature
- **Hint for Your Setup**: How this could benefit your specific devices/areas

## [Another Feature](URL#anchor)
- **What's New**: ...
- **Hint for Your Setup**: ...

> Repeat for each major highlight. Feature names must be clickable links to the release notes section.

## 🔌 New Integrations of Interest
- **[Integration Name](URL#anchor)**: Brief description and why it's relevant to your setup
- Each integration name should link to its documentation or release section

## 🔧 Improvements to Your Integrations
- **[Integration Name](URL#anchor)**: Description of improvement and affected devices
- Include links to the relevant section in the release notes

## Backward-Incompatible Changes ✅ or ⚠️

> Use ✅ if none of the breaking changes affect the user's setup. Use ⚠️ if there are considerations to be taken.

**Summary**: Brief 1-2 sentence overview stating whether the user has problems or not based on their setup analysis.

### [Integration Name](URL#anchor)
- **Affects You?**: Yes/No
- **Config Impact**: List automations, scenes, or scripts that reference the affected integration (if any)
- **Action Required**: What you need to do and which config files need updating (if affected)

> Repeat for each breaking change. Link each integration to its section in the release notes.

## ✅ Update Recommendation
- Safe to update / Review required / Wait for patch
```

## File output

Save the generated summary to the `ha-release-notes/` folder using this naming convention:

- Filename: `ha-release-[VERSION].md` (for example, `ha-release-2026.1.md`)
- The file must begin with the YAML front matter block before the first heading
- If the file already exists, update it with the latest content
- If the file already exists without front matter, prepend the YAML block before the first heading
- If the file does not exist, create it with the YAML front matter block first

The required front matter is:

```yaml
---
author: "<name of the user who ran the query>"
categories:
  - home-assistant
  - release-notes
tags:
  - ha-<VERSION>
model: "<AI model that generated this file>"
summary: "<one-sentence summary of the release impact on this setup>"
date: "<YYYY-MM-DD date of generation>"
---
```

## Example usage

```text
Analyze https://www.home-assistant.io/blog/2026/01/07/release-20261/
```

## Rules

- Use the release note URL exactly as provided, or derive it from the HA blog when none is supplied.
- Always cross-check the release changes against both `GetLiveContext` and the fetched config files before claiming an impact.
- Do not claim a breaking change affects the user unless it is actually present in the live setup or config YAML.
- Do not write markdown tables; use headings and bullet points only.
- Save all generated summaries under `ha-release-notes/`.
- Do not invent unsupported integrations, features, or breaking changes.
- This skill is intentionally user-invoked only and is not model-discoverable.
