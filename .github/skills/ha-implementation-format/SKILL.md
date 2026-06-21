---
name: ha-implementation-format
description: >-
  Output contract for Home Assistant implementation requests — the YAML /
  How This Works / Customization Ideas structure, runnable output only to
  .temp/, minimal valid YAML. Use when creating or editing automations,
  scripts, scenes, blueprints, or configuration.
---

# HA Implementation Output Contract

## When to use

- The user asks to create or edit an automation, script, scene, blueprint, or configuration.
- You have already called `GetLiveContext` and consulted `ha-docs-sitemap` for the relevant docs.

## File output rule

- Never modify tracked repository files.
- If runnable or multi-file output is helpful, write it only inside `.temp/` (gitignored) and summarize what you created.
- Otherwise, provide the content directly in chat.

## Required response structure

Every response must follow exactly this structure and order — no preambles or epilogues.

### ⭐ YAML

```yaml
# Provide only the minimal YAML for the user's automation/script/blueprint here.
# Do not include file paths or instructions to create files.
```

### 🛠️ How This Works

- Brief, bulleted explanation of the YAML's Trigger(s), Condition(s), and Action(s).
- Reference the exact docs sections used (link them).
- Note modern patterns (e.g., "action" style introduced in 2024.8) when applicable.

Example:

- Trigger: At sunset.
- Condition: Only act if the dimmer is currently off; this avoids altering it if it's already on manually.
- Action: Turns on the dimmer to 50% brightness using the modern `light.turn_on` service — the updated "action" style (introduced in Home Assistant 2024.8). See Automations docs: <https://www.home-assistant.io/docs/automation/>.

### 🔧 Customization Ideas

- Concise bulleted list of practical variations (alternate triggers, conditions for presence, per-room entities, schedules, scenes).
- Keep suggestions aligned with the official docs; link when helpful.

## Answering style

- Provide minimal, working examples first. Keep YAML concise and valid.
- When the UI is preferred in docs, include clear UI steps.
- For YAML, show placement context (e.g., under `automation:` or in a package).
- Include a short verification step (Config Validation, Automation Trace, Template editor).
