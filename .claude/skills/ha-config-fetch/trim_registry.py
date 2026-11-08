"""Trim one Home Assistant registry file (stdin) to the fields the home map reads (stdout).

Usage: ssh homeassistant "cat /config/.storage/core.device_registry" | trim_registry.py devices

fetch-ha-data.sh pipes each registry through this script, so what it drops never reaches the disk:
- entries: integration settings, credentials, tokens, and titles (cloud integrations often use the
  account's email address as the title). Only the domain is kept, plus the members of group and
  switch_as_x helpers.
- devices: MAC addresses, serial numbers, configuration URLs (which hold IP addresses), and
  firmware versions. Identifiers keep their integration; only Zigbee2MQTT ones keep their value,
  because the map matches MQTT topics to devices through it. Service entries (an account, a
  weather forecast) lose their names, which are often email addresses; the map leaves them out.
- entities: options, capabilities, and the unique IDs of everything but automations and scenes.
"""
import json
import sys

FIELDS = {
    "areas": ["id", "name", "icon", "floor_id"],
    "devices": ["id", "name", "name_by_user", "area_id", "manufacturer", "model", "entry_type", "disabled_by",
                "config_entries", "primary_config_entry", "via_device_id"],
    "entities": ["entity_id", "id", "device_id", "area_id", "platform", "config_entry_id", "disabled_by",
                 "hidden_by", "device_class", "original_device_class"],
}


def trim_entries(data):
    out = {}
    for entry in data["entries"]:
        item = {"domain": entry["domain"]}
        options = entry.get("options") or {}
        if entry["domain"] == "group":
            item["group_type"] = options.get("group_type")
            item["entities"] = [e for e in options.get("entities") or [] if isinstance(e, str)]
        elif entry["domain"] == "switch_as_x" and isinstance(options.get("entity_id"), str):
            item["entities"] = [options["entity_id"]]
        out[entry["entry_id"]] = item
    return out


def trim_item(kind, item):
    out = {key: item.get(key) for key in FIELDS[kind]}
    if kind == "devices":
        if item.get("entry_type") == "service":
            out["name"] = out["name_by_user"] = None
        out["identifiers"] = [
            [str(i[0]), str(i[1])] if len(i) > 1 and str(i[1]).startswith("zigbee2mqtt") else [str(i[0])]
            for i in item.get("identifiers") or [] if i
        ]
    if kind == "entities" and str(item.get("entity_id", "")).startswith(("automation.", "scene.")):
        out["unique_id"] = item.get("unique_id")
    return out


def main():
    kind = sys.argv[1] if len(sys.argv) == 2 else ""
    if kind not in ("areas", "devices", "entities", "entries"):
        sys.exit("usage: trim_registry.py areas|devices|entities|entries < registry.json")
    try:
        data = json.load(sys.stdin)["data"]
    except (ValueError, KeyError, TypeError) as err:
        sys.exit(f"not a Home Assistant registry: {err}")
    if kind == "entries":
        result = trim_entries(data)
    else:
        result = {"data": {kind: [trim_item(kind, item) for item in data[kind]]}}
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
