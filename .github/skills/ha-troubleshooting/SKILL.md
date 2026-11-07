---
name: ha-troubleshooting
description: >-
  Diagnoses failing Home Assistant automations, integrations, and entities by
  checking the config, logs, traces, and Developer Tools before proposing a
  fix. Use when something is failing, erroring, misbehaving, or needs a
  deeper debugging diagnosis, including a GetLiveContext call that fails or
  misses an entity.
---

# HA Troubleshooting Playbook

## When to use

- An automation, integration, or entity is failing, erroring, or misbehaving.
- The user asks to debug, diagnose, or investigate a problem.
- `GetLiveContext` fails, or its output lacks an entity the user names: go to [MCP connection problems](#mcp-connection-problems).

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

## MCP connection problems

When `GetLiveContext` fails or misses an entity, the cause sits in Home Assistant's Model Context Protocol Server integration rather than in the user's configuration. Skip the playbook above and match the symptom:

1. **Entity missing from the output** — it is not exposed to Assist. The user exposes it under Settings → Voice assistants → Expose. Cite <https://www.home-assistant.io/voice_control/voice_remote_expose_devices/>.
2. **Call fails, times out, or is unauthorized** — check that the integration is set up, its options (tool sets, administrator account, read-only), and the client's sign-in or token. Cite <https://www.home-assistant.io/integrations/mcp_server/>, including its Troubleshooting section.

Done when the user knows which symptom applies and the step that fixes it.

## Rules

- Cite the exact docs section used for each step (see `ha-docs-sitemap`).
- Prefer supported features; avoid unsupported hacks.
- Recommend a backup before major config changes.
