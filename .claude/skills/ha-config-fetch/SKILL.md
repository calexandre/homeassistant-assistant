---
name: ha-config-fetch
description: >-
  Fetches read-only SSH snapshots of Home Assistant config files into ha-data/
  with fetch-ha-data.sh, checking freshness first. Use when a request needs
  configuration.yaml or a file it includes, customize.yaml, or Zigbee2MQTT's
  files, which no MCP tool reads, or ESPHome YAMLs and logs when the client
  lacks the MCP tools for them.
---

# HA Config Fetch

## When to use

- The request needs `configuration.yaml`, a file it includes (packages, automation and script folders), `customize.yaml`, or Zigbee2MQTT's `configuration.yaml`, `devices.yaml`, `groups.yaml`, or `state.json`. No MCP tool reads these files, so the snapshot is their only source.
- The `ha-home-map` or `ha-release-notes` skill needs the registries and YAML as files.
- The client lacks the MCP tools for ESPHome device YAMLs (the ESPHome Device Builder set) or for logs (ha-mcp's `ha_get_logs` or the Home Assistant set).

Read automations, scripts, scenes, helpers, and registry entries live through ha-mcp (`ha_config_get_automation`, `ha_config_get_script`, `ha_config_get_scene`, `ha_get_entity`); their snapshot copies exist for the two skills above.

## Freshness gate

Before reading any file from `ha-data/`, run:

```bash
find ha-data/ -name '*.yaml' -mmin +1440 -print -quit | grep -q . && echo STALE || echo FRESH
```

- **STALE, missing, or debugging request** → run the fetch step below.
- **FRESH and not a debugging task** → read directly, skip the fetch.

Debugging requests (troubleshooting, log analysis, error investigation) always re-fetch — logs and state change frequently.

If `ha-data/` does not exist at all, treat it as stale.

## Fetch step

`fetch-ha-data.sh` sits in this skill's folder and writes `ha-data/` into the current directory, so run it by its full path with the working directory at the project root. In a clone of this repository that is:

```bash
.claude/skills/ha-config-fetch/fetch-ha-data.sh
```

When the skill comes from an installed plugin, use the skill folder's absolute path instead.

Optional: override the config directory (default `/config`):

```bash
.claude/skills/ha-config-fetch/fetch-ha-data.sh /custom/path
```

If the script exits with `Cannot reach 'homeassistant' over passwordless SSH`, tell the user SSH snapshots are not set up, point them at the README's "Optional: SSH snapshots" section, and continue with what the MCP tools can read.

## File map

After the script completes, read the file(s) you need:

- `ha-data/automations.yaml` — all automations
- `ha-data/scenes.yaml` — all scenes
- `ha-data/scripts.yaml` — all scripts
- `ha-data/configuration.yaml` — main configuration
- `ha-data/customize.yaml` — entity customizations
- `ha-data/<path>` — every file `configuration.yaml` includes (packages, automation, script, and scene folders), in the same folder layout as on the host; `secrets.yaml` is never fetched
- `ha-data/registry/{areas,devices,entities,entries}.json` — the area, device, entity, and integration registries, trimmed while they download: no credentials, integration titles, MAC addresses, or serial numbers
- `ha-data/esphome/*.yaml` — every ESPHome device YAML found under the ESPHome data dir (`secrets.yaml` is always skipped, never snapshotted)
- `ha-data/zigbee2mqtt/configuration.yaml` — Zigbee2MQTT main config
- `ha-data/zigbee2mqtt/devices.yaml` — Zigbee2MQTT device definitions
- `ha-data/zigbee2mqtt/groups.yaml` — Zigbee2MQTT groups
- `ha-data/zigbee2mqtt/state.json` — Zigbee2MQTT runtime state (not YAML; freshness gate does not cover it — debugging requests always re-fetch)
- `ha-data/logs/core.log` — latest HA Core container logs (debugging)
- `ha-data/logs/supervisor.log` — latest Supervisor container logs (debugging)

## Rules

- Never hand-edit or commit files inside `ha-data/` — `fetch-ha-data.sh` owns these local-only snapshots.
- Do not assume file contents — always check freshness first.
