---
name: ha-release-notes
description: >-
  Compares a Home Assistant release against the live setup and produces a
  personalized summary of highlights, new integrations, improvements, and
  breaking changes, saving the report to ha-release-notes/ha-release-[VERSION].md
  and replying in chat with the highlights, the warnings that affect your setup,
  and a link to the report. Use when the user wants a release summary tailored to
  their actual devices, automations, scenes, scripts, and configuration.
disable-model-invocation: true
---

# HA Release Notes

## When to use

- The user wants a personalized summary of a Home Assistant release based on the current live setup.
- The request names a release by URL or version (`2026.11`, `2026.11.0`, `2026.11.2`), or names none, in which case the latest release from the HA blog should be used.
- The user wants highlights, new integrations, integration improvements, or backward-incompatible change impact assessed against their actual devices, automations, scenes, scripts, and configuration.

## Input

Resolve the argument to one release post before Step 1:

- Release URL: use the exact Home Assistant blog URL as given.
- Version: every monthly release `<year>.<month>` has one post at `https://www.home-assistant.io/blog/<date>/release-<year><month>/` (for example `release-202611` for 2026.11). Find it in `https://www.home-assistant.io/blog/categories/release-notes/`. A patch version such as `2026.11.2` uses the same post: its changes sit under the post's `#patch-releases` section.
- Nothing provided: use the newest post in `https://www.home-assistant.io/blog/categories/release-notes/`.

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

1. Fetch the release post resolved under Input. For a patch version, also read each patch release section up to and including that version.
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

**Warning headings:** the ⚠️ marks are the user's to-do list, so they go only where this user's setup is touched. Start a heading with ⚠️ only when the analysis confirms the change affects their setup (**Affects You?** Yes) or the user has to change something because of it: a required config edit, a deprecation or removal of something they use, a changed default that alters how their setup behaves, or a step they must take after updating. A heading for a change that doesn't apply, or whose impact the analysis couldn't confirm, keeps its usual form; its bullets still say what to check. Put ⚠️ first, before any link or other emoji.

```markdown
# 🏠 Release Summary for [Version]

## [Feature Name](URL#anchor)
- **What's New**: 1-2 sentence explanation of the feature
- **Hint for Your Setup**: How this could benefit your specific devices/areas

## ⚠️ [Feature That Needs Your Attention](URL#anchor)
- **What's New**: 1-2 sentence explanation of the change
- **Hint for Your Setup**: What changes for your devices or configs, and what to do

> Repeat for each major highlight. Feature names must be clickable links to the release notes section.

## 🔌 New Integrations of Interest
- **[Integration Name](URL#anchor)**: Brief description and why it's relevant to your setup
- Each integration name should link to its documentation or release section

## 🔧 Improvements to Your Integrations
- **[Integration Name](URL#anchor)**: Description of improvement and affected devices
- Include links to the relevant section in the release notes

## ⚠️ Backward-Incompatible Changes

> Use `## ✅ Backward-Incompatible Changes` instead when none of the breaking changes affect the user's setup.

**Summary**: Brief 1-2 sentence overview stating whether the user has problems or not based on their setup analysis.

### ⚠️ [Integration That Affects You](URL#anchor)
- **Affects You?**: Yes
- **Config Impact**: List automations, scenes, or scripts that reference the affected integration
- **Action Required**: What you need to do and which config files need updating

### [Integration That Doesn't](URL#anchor)
- **Affects You?**: No
- **Config Impact**: None found
- **Action Required**: None

> Repeat for each breaking change; only the ones that affect the user's setup get ⚠️. Link each integration to its section in the release notes.

## ✅ Update Recommendation
- Safe to update / Review required / Wait for patch

> Use `## ⚠️ Update Recommendation` when the recommendation is Review required or Wait for patch.
```

## File output

The full report is a file. Save it to `ha-release-notes/` in the current working directory, creating the folder when it is missing. Git ignores that folder on purpose: the report describes the user's home, so it stays on this machine. Write it there anyway; the gitignore is no reason to save it to session storage or anywhere else.

Done when the file exists at `ha-release-notes/ha-release-[VERSION].md` and the chat reply described under Chat reply has been written.

Use this naming convention:

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

## Chat reply

After saving the file, reply in chat with three parts, in this order. Do not paste the full report into the chat.

1. Highlights: a single paragraph that names the release's major highlights and what they mean for this setup. Link each highlight to its release notes section. Use no bullets or headings in this paragraph.
2. Warnings: one bullet for each change in the report whose own heading starts with ⚠️, which covers the highlights and the breaking changes that affect this setup. Skip the section headings. Each bullet links the change to its release notes section and states in one line what the user has to do. Include the update recommendation as a bullet too when its heading carries ⚠️. If no heading starts with ⚠️, write one bullet saying that no warnings apply to this setup.
3. Report: a Markdown link to the saved file, using its path relative to the working directory, for example `[ha-release-notes/ha-release-2026.11.md](ha-release-notes/ha-release-2026.11.md)`.

## Example usage

```text
/ha-release-notes
/ha-release-notes 2026.11.0
/ha-release-notes https://www.home-assistant.io/blog/2026/11/04/release-202611/
```

## Rules

- Use a provided URL exactly as given; resolve a version or a missing argument through the release notes index, as described under Input.
- Always cross-check the release changes against both `GetLiveContext` and the fetched config files before claiming an impact.
- Do not claim a breaking change affects the user unless it is actually present in the live setup or config YAML.
- Do not write markdown tables; use headings and bullet points only.
- Save all generated summaries under `ha-release-notes/`.
- The chat reply holds one highlights paragraph, the warnings that affect this setup, and the report link; the full analysis stays in the file.
- Do not invent unsupported integrations, features, or breaking changes.
- This skill is intentionally user-invoked only and is not model-discoverable.
