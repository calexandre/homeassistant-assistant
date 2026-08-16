---
name: ha-config-fetch
description: >-
  Fetches Home Assistant snapshots from ha-data/ via fetch-ha-data.sh,
  checking freshness before reading automations, scenes, scripts,
  configuration.yaml, customize.yaml, logs, or other saved config files.
  Use when the MCP server does not expose these files and you need the
  local snapshot to inspect the current setup.
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
- `ha-data/customize.yaml` — entity customizations
- `ha-data/esphome/*.yaml` — every ESPHome device YAML found under the ESPHome data dir (`secrets.yaml` is always skipped, never snapshotted)
- `ha-data/zigbee2mqtt/configuration.yaml` — Zigbee2MQTT main config
- `ha-data/zigbee2mqtt/devices.yaml` — Zigbee2MQTT device definitions
- `ha-data/zigbee2mqtt/groups.yaml` — Zigbee2MQTT groups
- `ha-data/zigbee2mqtt/state.json` — Zigbee2MQTT runtime state (not YAML; freshness gate does not cover it — debugging requests always re-fetch)
- `ha-data/logs/core.log` — latest HA Core container logs (debugging)
- `ha-data/logs/supervisor.log` — latest Supervisor container logs (debugging)

## Rules

- Never modify or commit files inside `ha-data/` — gitignored, local-only snapshots.
- Do not assume file contents — always check freshness first.
