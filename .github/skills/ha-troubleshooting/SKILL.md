---
name: ha-troubleshooting
description: >-
  Docs-backed Home Assistant troubleshooting playbook — config check, logs,
  traces, Developer Tools, debug logging. Use when an automation, integration,
  or entity is failing, erroring, or misbehaving.
---

# HA Troubleshooting Playbook

## When to use

- An automation, integration, or entity is failing, erroring, or misbehaving.
- The user asks to debug, diagnose, or investigate a problem.

## Prerequisites

- Always re-fetch config snapshots for debugging — logs and state change frequently. Invoke the `ha-config-fetch` skill instead of reading `ha-data/` directly.
- Use the `ha-docs-sitemap` skill to look up docs for the failing integration or feature before answering.

## Playbook

Run these in order, stopping when the cause is found:

1. **Validate configuration** — Settings → System → Repairs → Check configuration.
2. **Review logs** — Settings → System → Logs; for raw logs invoke the `ha-config-fetch` skill and read `core.log` / `supervisor.log` from the refreshed snapshots.
3. **Inspect automation traces** — Automations → select automation → Traces.
4. **Use Developer Tools** — States, Services; Template editor to test Jinja.
5. **Enable debug logging** for the specific integration per the official docs.

## Rules

- Cite the exact docs section used for each step (see `ha-docs-sitemap`).
- Prefer supported features; avoid unsupported hacks.
- Recommend a backup before major config changes.