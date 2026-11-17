---
name: ha-troubleshooting
description: >-
  Diagnoses a failing Home Assistant automation, integration, entity, or MCP
  connection by following its evidence trail through logs, traces, and
  diagnostics before proposing a fix. Use when something fails, errors, or
  misbehaves, or when a Home Assistant MCP tool fails or misses an entity.
---

# HA Troubleshooting

Follow the evidence trail: read what Home Assistant recorded about the failure before proposing a fix. The tools come from ha-mcp (`ha_*`; run one missing from the tool list through `ha_call_tool` after finding it with `ha_search_tools`) and from the MCP Server integration's Home Assistant and ESPHome Device Builder sets. Use whichever the client has.

## Evidence trail

Run the steps in order and stop at the one that explains the failure.

1. **Errors and warnings.** `ha_get_logs` with `source: system` returns Home Assistant's deduplicated errors and warnings with their tracebacks; `system_log__get_entries` is the same list. Search for the integration or entity involved.
2. **Timeline around the failure.** `ha_get_logs` with `source: error_log` for raw Core records, `source: supervisor` with the app's `slug` for an app such as Zigbee2MQTT, or `source: logbook` with an `entity_id` for what changed and what caused it. `hassio__get_logs` merges Core, Supervisor, and app logs for a time window.
3. **The failing piece itself:**
   - Automation or script: `ha_get_automation_traces` lists recent runs; pass a `run_id` to see which trigger fired, which condition failed, and which action errored. `ha_config_get_automation` fills `validation` when the automation failed to load.
   - Integration: `ha_get_integration` with its `domain` gives the state and error reason; add `include_diagnostics: true` for its diagnostics.
   - Entity or device: `ha_get_state`, then `ha_get_history` around the failure; `ha_get_device` shows Zigbee and Z-Wave link details.
   - ESPHome device: `list_devices` for its online state and deployed firmware, then `validate_config` on its file.
4. **Debug logging.** With the user's go-ahead, set `log_level: DEBUG` through `ha_set_integration`, have the user reproduce the failure, read step 2 again, then set `log_level: DEFAULT`.

When the client has none of these tools, invoke `ha-config-fetch`, which re-fetches before any debugging, and read `ha-data/logs/core.log` and `ha-data/logs/supervisor.log`.

Done when the cause is named with the log record, trace step, or state change that shows it, or every step has run and the user has the next thing to try.

## Fix

Write the fix with the `home-assistant-best-practices` skill, installed or read through `ha_get_skill_guide`, and cite the official doc page behind it. Get the user's go-ahead before each tool call that changes Home Assistant or a device.

## MCP connection problems

When an MCP tool call fails or misses something the user names, the cause sits in the MCP setup rather than in the home's configuration. Match the symptom:

1. **An entity missing from `GetLiveContext`.** `GetLiveContext` sees only entities exposed to Assist, while `ha_search` sees every entity. The user exposes it under Settings → Voice assistants → Expose. Cite <https://www.home-assistant.io/voice_control/voice_remote_expose_devices/>.
2. **Calls fail, time out, or return 401.** Check that the Model Context Protocol Server integration is set up, that the client signed in as an administrator, and that the URL matches the Internal or External URL set in Home Assistant. Cite <https://www.home-assistant.io/integrations/mcp_server/#troubleshooting>.
3. **The `ha_*` tools are missing.** ha-mcp is not installed, or its tools don't reach the MCP Server integration: the HA-MCP integration's LLM API option has to be on, and the MCP Server integration has to expose all AI tools or have HA-MCP picked under **AI tools**. Cite <https://github.com/homeassistant-ai/ha-mcp>.
4. **Log, statistics, or ESPHome tools are missing.** The same **AI tools** option controls the Home Assistant and ESPHome Device Builder sets; the ESPHome tools also need the ESPHome Device Builder app. Cite <https://www.home-assistant.io/integrations/mcp_server/#configuration-options>.

After an option change, the client reconnects to load the new tool list.

Done when the user knows which symptom applies and the step that fixes it.
