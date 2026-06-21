---
name: ha-config-fetch
description: >-
  Fetch local Home Assistant config snapshots from ha-data/ via
  fetch-ha-data.sh, gated by a freshness check. Use when a request
  touches existing automations, scenes, scripts, configuration.yaml, or
  Core/Supervisor logs — none of which the MCP server exposes.
---

# HA Config Fetch

## When to use

- The request involves existing automations, scenes, scripts, `configuration.yaml`, or logs.
- The MCP server does not expose these — `ha-data/` snapshots are the only source.

## Freshness gate

Before reading any file from `ha-data/`, run:

```bash
find ha-data/ -name '*.yaml' -mmin +1440 -print -quit | grep -q . && echo STALE || echo FRESH
```

- **STALE, missing, or debugging request** → run `./fetch-ha-data.sh` from this skill's folder.
- **FRESH and not a debugging task** → read directly, skip the fetch.

Debugging requests (troubleshooting, log analysis, error investigation) always re-fetch — logs and state change frequently.

If `ha-data/` does not exist at all, treat it as stale.

## Fetch step

Run from the repository root:

```bash
.github/skills/ha-config-fetch/fetch-ha-data.sh
```

Optional: override the config directory (default `/config`):

```bash
.github/skills/ha-config-fetch/fetch-ha-data.sh /custom/path
```

## File map

After the script completes, read the file(s) you need:

- `ha-data/automations.yaml` — all automations
- `ha-data/scenes.yaml` — all scenes
- `ha-data/scripts.yaml` — all scripts
- `ha-data/configuration.yaml` — main configuration
- `ha-data/logs/core.log` — latest HA Core container logs (debugging)
- `ha-data/logs/supervisor.log` — latest Supervisor container logs (debugging)

## Rules

- Never modify or commit files inside `ha-data/` — gitignored, local-only snapshots.
- Do not assume file contents — always check freshness first.
