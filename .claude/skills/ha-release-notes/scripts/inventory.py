"""What the home uses, by integration domain, for matching release items against it.

from_snapshot(ha_data) reads the trimmed registries in ha_data/registry/ and the YAML that
configuration.yaml includes (through the home map's loader, which needs PyYAML) and returns:

  {"source": "registries", "domains": {domain: {"entries", "entities", "yaml", "used_by"}},
   "logic": {entity_id: label}}

A domain is in use when a config entry, an entity's platform or own domain, a YAML key or
platform, or an automation, script, or scene (through an action, a device, a trigger, or an
entity it names) points at it. used_by lists those automations, scripts, and scenes.

from_domains(domains) is the fallback without SSH snapshots: the entity domains GetLiveContext
shows, with nothing known about integrations or YAML.
"""
import json
import pathlib
import re
import sys
from collections import defaultdict

ENTITY_ID = re.compile(r"\b([a-z_][a-z0-9_]*\.[a-z0-9_]+)\b")
LOGIC_KEYS = ("automation", "script", "scene")


def home_map_loader():
    """The home map's YAML loader, which follows !include files and packages like Home Assistant."""
    scripts = pathlib.Path(__file__).resolve().parents[2] / "ha-home-map" / "scripts"
    sys.path.insert(0, str(scripts))
    import build_graph  # noqa: E402  (needs PyYAML)
    return build_graph


def blank():
    return {"entries": 0, "entities": 0, "yaml": False, "used_by": set()}


def from_snapshot(ha_data):
    ha_data = pathlib.Path(ha_data)
    reg = ha_data / "registry"
    bg = home_map_loader()
    domains = defaultdict(blank)

    entries = json.loads((reg / "entries.json").read_text())
    for entry in entries.values():
        domains[entry["domain"]]["entries"] += 1
    entities = {e["entity_id"]: e for e in bg.load_registry(reg / "entities.json", "entities")}
    for ent in entities.values():
        if ent.get("disabled_by"):
            continue
        for domain in {ent.get("platform"), ent["entity_id"].split(".")[0]} - {None}:
            domains[domain]["entities"] += 1
    devices = {d["id"]: d for d in bg.load_registry(reg / "devices.json", "devices")}

    def device_domain(device_id):
        device = devices.get(device_id) or {}
        entry = device.get("primary_config_entry") or next(iter(device.get("config_entries") or []), None)
        return (entries.get(entry) or {}).get("domain")

    # YAML: every top-level key and every platform an integration key lists, packages included.
    cfg = ha_data.resolve()
    conf = bg.expand(bg.load_yaml(cfg / "configuration.yaml"), cfg) if (cfg / "configuration.yaml").is_file() else {}
    conf = conf if isinstance(conf, dict) else {}
    packages = (conf.get("homeassistant") or {}).get("packages") if isinstance(conf.get("homeassistant"), dict) else {}
    for section in [conf] + [p for p in (packages or {}).values() if isinstance(p, dict)]:
        for key, value in section.items():
            domain = str(key).split(" ")[0]
            domains[domain]["yaml"] = True
            if domain not in LOGIC_KEYS:
                for platform in platforms(value):
                    domains[platform]["yaml"] = True

    # Automations, scripts, and scenes: which domains each one reaches.
    automations, scripts, scenes = bg.load_logic(cfg)
    uid = {str(e.get("unique_id")): eid for eid, e in entities.items() if e.get("unique_id")}
    logic = {}
    for auto in automations:
        if isinstance(auto, dict):
            eid = uid.get(str(auto.get("id"))) or f"automation.{bg.slug(auto.get('alias') or auto.get('id'))}"
            logic[eid] = (auto.get("alias") or str(auto.get("id")), auto)
    for object_id, body in (scripts or {}).items():
        if isinstance(body, dict):
            logic[f"script.{object_id}"] = (body.get("alias") or object_id, body)
    for scene in scenes:
        if isinstance(scene, dict):
            eid = uid.get(str(scene.get("id"))) or f"scene.{bg.slug(scene.get('name'))}"
            logic[eid] = (scene.get("name") or eid, scene)

    for eid, (_, body) in logic.items():
        reached = set()
        walk(body, reached, entities, device_domain, in_triggers=False)
        if eid.startswith("scene."):
            reached |= {e.split(".")[0] for e in (body.get("entities") or {}) if isinstance(e, str)}
            for e in body.get("entities") or {}:
                platform = (entities.get(e) or {}).get("platform")
                if platform:
                    reached.add(platform)
        for domain in reached:
            domains[domain]["used_by"].add(eid)

    return {
        "source": "registries",
        "domains": {d: {**v, "used_by": sorted(v["used_by"])} for d, v in sorted(domains.items()) if d},
        "logic": {eid: str(label) for eid, (label, _) in sorted(logic.items())},
    }


def platforms(value):
    """platform: values under an integration key, such as sensor: [{platform: rest}]."""
    found = set()
    if isinstance(value, list):
        for item in value:
            found |= platforms(item)
    elif isinstance(value, dict):
        if isinstance(value.get("platform"), str):
            found.add(value["platform"])
        for item in value.values():
            if isinstance(item, (list, dict)):
                found |= platforms(item)
    return found


def walk(node, reached, entities, device_domain, in_triggers):
    if isinstance(node, list):
        for item in node:
            walk(item, reached, entities, device_domain, in_triggers)
        return
    if isinstance(node, str):
        for token in ENTITY_ID.findall(node):
            ent = entities.get(token)
            if ent and not ent.get("disabled_by"):
                reached.add(token.split(".")[0])
                if ent.get("platform"):
                    reached.add(ent["platform"])
        return
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if key in ("action", "service") and isinstance(value, str) and "." in value and "{" not in value:
            reached.add(value.split(".")[0])
        elif key == "domain" and isinstance(value, str):
            reached.add(value)
        elif key == "device_id":
            for device_id in value if isinstance(value, list) else [value]:
                if isinstance(device_id, str) and device_domain(device_id):
                    reached.add(device_domain(device_id))
        elif in_triggers and key in ("trigger", "platform") and isinstance(value, str) and "." not in value:
            reached.add(value)
        walk(value, reached, entities, device_domain, in_triggers or key in ("trigger", "triggers"))


def from_domains(domains):
    clean = sorted({d.strip().lower() for d in domains if re.fullmatch(r"\s*[a-z0-9_]+\s*", d)})
    return {"source": "live_context", "domains": {d: {**blank(), "used_by": []} for d in clean}, "logic": {}}
