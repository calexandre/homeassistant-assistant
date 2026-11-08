"""Build the home map graph: areas, devices, automations, scripts, scenes, and how they connect.

Reads Home Assistant's area, device, entity, and config-entry registries plus the automation,
script, scene, and Zigbee2MQTT YAML, and writes the graph JSON that render.py turns into HTML.

Usage:
  build_graph.py --registry DIR --config DIR --out graph.json

--registry  holds areas.json, devices.json, entities.json, and entries.json, as fetch-ha-data.sh
            writes them to ha-data/registry/ (trimmed by ha-config-fetch/trim_registry.py)
--config    a copy of the config folder, such as ha-data/: configuration.yaml with the files it
            includes in the same layout, and zigbee2mqtt/devices.yaml. Automations, scripts, and
            scenes come from every automation, script, and scene key, packages included. Without
            configuration.yaml, automations.yaml, scripts.yaml, and scenes.yaml are read instead.
"""
import argparse
import json
import pathlib
import re
from collections import Counter, defaultdict

import yaml


class Include:
    """An !include or !include_dir_* tag, resolved later against the folder of the file it is in."""

    def __init__(self, tag, path, base):
        self.tag, self.path, self.base = tag, path, base


def load_yaml(path):
    """Read Home Assistant YAML. !include tags become Include; !secret, !input, and others keep their value."""
    path = pathlib.Path(path)
    if not path.is_file():
        return None

    class Loader(yaml.SafeLoader):
        pass

    def construct(loader, suffix, node):
        value = (loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode)
                 else loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode)
                 else loader.construct_mapping(node))
        return Include(suffix, value, path.parent) if suffix.startswith("include") and isinstance(value, str) else value

    Loader.add_multi_constructor("!", construct)
    return yaml.load(path.read_text(), Loader=Loader)


def expand(value, root, depth=0):
    """Replace Include values with what they name, the way Home Assistant does, inside root only."""
    if isinstance(value, dict):
        return {k: expand(v, root, depth) for k, v in value.items()}
    if isinstance(value, list):
        return [expand(v, root, depth) for v in value]
    if not isinstance(value, Include) or depth > 8:
        return None if isinstance(value, Include) else value
    target = (value.base / value.path).resolve()
    if not target.is_relative_to(root):
        return None
    if value.tag == "include":
        return expand(load_yaml(target), root, depth + 1)
    files = sorted(f for f in target.rglob("*.yaml") if f.name != "secrets.yaml"
                   and not any(part.startswith(".") for part in f.relative_to(target).parts)) if target.is_dir() else []
    loaded = [expand(load_yaml(f), root, depth + 1) for f in files]
    if value.tag == "include_dir_list":
        return [x for x in loaded if x is not None]
    if value.tag == "include_dir_named":
        return {f.stem: x for f, x in zip(files, loaded)}
    if value.tag == "include_dir_merge_list":
        return [item for x in loaded if isinstance(x, list) for item in x]
    if value.tag == "include_dir_merge_named":
        return {k: v for x in loaded if isinstance(x, dict) for k, v in x.items()}
    return None


def load_logic(cfg):
    """Every automation, script, and scene in the config, packages included."""
    cfg = pathlib.Path(cfg).resolve()
    if not (cfg / "configuration.yaml").is_file():
        return (list(load_yaml(cfg / "automations.yaml") or []), load_yaml(cfg / "scripts.yaml") or {},
                list(load_yaml(cfg / "scenes.yaml") or []))
    conf = expand(load_yaml(cfg / "configuration.yaml"), cfg) or {}
    packages = (conf.get("homeassistant") or {}).get("packages") if isinstance(conf.get("homeassistant"), dict) else None
    sections = [conf] + [p for p in (packages or {}).values() if isinstance(p, dict)] if isinstance(packages, dict) else [conf]
    automations, scripts, scenes = [], {}, []
    as_items = lambda v: v if isinstance(v, list) else [v] if isinstance(v, dict) else []
    for section in sections:
        for key, value in section.items():
            domain = str(key).split(" ")[0]
            if domain == "automation":
                automations += as_items(value)
            elif domain == "script" and isinstance(value, dict):
                scripts.update(value)
            elif domain == "scene":
                scenes += as_items(value)
    return automations, scripts, scenes


def load_registry(path, key):
    return json.loads(pathlib.Path(path).read_text())["data"][key]


# Device types: (MDI icon, label). The first matching rule in device_type() wins.
TYPES = {
    "phone": ("mdi:cellphone", "Phone"), "adaptive": ("mdi:theme-light-dark", "Adaptive lighting"),
    "tv": ("mdi:television", "TV"), "speaker": ("mdi:speaker", "Speaker"), "printer": ("mdi:printer", "Printer"),
    "dishwasher": ("mdi:dishwasher", "Dishwasher"), "laundry": ("mdi:washing-machine", "Laundry"),
    "fridge": ("mdi:fridge", "Fridge"), "cooking": ("mdi:stove", "Cooking"),
    "water_heater": ("mdi:water-boiler", "Water heater"), "heater": ("mdi:radiator", "Heater"),
    "ac": ("mdi:air-conditioner", "Air conditioning"), "fan": ("mdi:fan", "Fan"), "hub": ("mdi:hub", "Hub / bridge"),
    "coffee": ("mdi:coffee-maker", "Coffee machine"), "camera": ("mdi:cctv", "Camera"),
    "network": ("mdi:router-wireless", "Network"), "remote": ("mdi:remote", "Remote / button"),
    "plant": ("mdi:flower", "Plant sensor"), "vacuum": ("mdi:robot-vacuum", "Vacuum"),
    "cover": ("mdi:blinds", "Blind / cover"), "lock": ("mdi:lock", "Lock"), "light": ("mdi:lightbulb", "Light"),
    "motion": ("mdi:motion-sensor", "Motion / presence"), "contact": ("mdi:door-open", "Door / window"),
    "leak": ("mdi:water-alert", "Leak sensor"), "plug": ("mdi:power-plug", "Plug"),
    "switch": ("mdi:light-switch", "Switch / relay"), "climate_sensor": ("mdi:thermometer", "Temperature / humidity"),
    "energy": ("mdi:flash", "Energy meter"), "media": ("mdi:play-box", "Media client"), "other": ("mdi:devices", "Other"),
}

NAME_RULES = [
    (r"leak|flood", "leak"), (r"bridge|coordinator|gateway|\bhub\b", "hub"),
    (r"wall switch|ceiling switch|light switch|corridor switch", "switch"), (r"plug|socket|outlet", "plug"),
    (r"spotlight|\bled\b|lamp|bulb|strip", "light"), (r"speaker|sonos|home mini|nest mini|soundbar|display", "speaker"),
    (r"\b(tv|television)\b", "tv"), (r"camera|doorbell", "camera"), (r"printer|filament|prusa|octoprint|octopi", "printer"),
    (r"dishwasher", "dishwasher"), (r"washing|washer|dryer", "laundry"), (r"fridge|refrigerator|freezer", "fridge"),
    (r"\bhob\b|oven|cooktop", "cooking"), (r"coffee", "coffee"), (r"water heater|boiler", "water_heater"),
    (r"heater|radiator", "heater"), (r"\bac\b|air ?con", "ac"), (r"\bfan\b", "fan"),
    (r"router|modem|\bmesh\b|access point", "network"), (r"\bphone\b", "phone"),
    (r"remote|button|dimmer", "remote"), (r"plant|flora", "plant"), (r"shelly ?em|energy|power meter", "energy"),
]
DOMAIN_TYPES = {
    "mobile_app": "phone", "adaptive_lighting": "adaptive", "webostv": "tv", "androidtv_remote": "tv",
    "ipp": "printer", "octoprint": "printer", "asuswrt": "network", "ping": "network", "upnp": "network",
    "plex": "media", "cast": "speaker",
}
ENTITY_TYPES = (("camera", "camera"), ("vacuum", "vacuum"), ("climate", "ac"), ("fan", "fan"),
                ("media_player", "speaker"), ("light", "light"), ("cover", "cover"), ("lock", "lock"))

ZIGBEE = {"zha", "deconz"}
ZWAVE = {"zwave_js", "zwave_me"}
MATTER = {"matter", "thread"}
BLUETOOTH = {
    "bluetooth", "ble_monitor", "xiaomi_ble", "ibeacon", "bthome", "govee_ble", "inkbird", "sensorpush", "oralb",
    "switchbot", "led_ble", "yalexs_ble", "qingping", "thermobeacon", "thermopro", "ruuvitag_ble", "airthings_ble",
    "sensirion_ble", "mopeka", "aranet", "bluemaestro", "bluetooth_le_tracker", "eufylife_ble", "snooz",
}
CLOUD_AND_VIRTUAL = {
    "lg_thinq", "connectlife", "home_connect", "google_drive", "adaptive_lighting", "template", "group", "switch_as_x",
    "generic_thermostat", "utility_meter", "sun", "rpi_power", "systemmonitor", "ping", "tuya", "smartthings",
    "nest", "ecobee", "ring", "tado", "netatmo", "spotify", "met", "openweathermap", "accuweather", "?",
}

SKIP_IN_ACTIONS = {"conditions", "if", "while", "until", "wait_for_trigger", "variables", "wait_template", "condition"}
LOGIC = ("automation", "script", "scene")


class Home:
    def __init__(self, registry, config):
        reg = pathlib.Path(registry)
        cfg = pathlib.Path(config)
        self.areas = {a["id"]: a for a in load_registry(reg / "areas.json", "areas")}
        self.devices = {d["id"]: d for d in load_registry(reg / "devices.json", "devices")}
        self.entities = {e["entity_id"]: e for e in load_registry(reg / "entities.json", "entities")}
        self.entries = json.loads((reg / "entries.json").read_text())
        self.entity_by_reg_id = {e["id"]: e for e in self.entities.values() if e.get("id")}

        automations, self.scripts, scenes = load_logic(cfg)
        self.automations = [a for a in automations if isinstance(a, dict)]
        self.scenes = [s for s in scenes if isinstance(s, dict)]
        z2m = load_yaml(cfg / "zigbee2mqtt" / "devices.yaml") or {}
        self.z2m_ieee_by_name = {str(v.get("friendly_name")): str(k) for k, v in z2m.items() if isinstance(v, dict)}

        self.device_by_ident = {}
        self.device_by_norm_name = {}
        for d in self.devices.values():
            for ident in d.get("identifiers") or []:
                if len(ident) >= 2:
                    self.device_by_ident[str(ident[1])] = d["id"]
            for name in (d.get("name"), d.get("name_by_user")):
                if name:
                    self.device_by_norm_name.setdefault(norm(name), d["id"])
        self.ents_by_device = defaultdict(list)
        for e in self.entities.values():
            if e.get("device_id") and not e.get("disabled_by"):
                self.ents_by_device[e["device_id"]].append(e)
        self.unresolved = Counter()

    # --- devices -----------------------------------------------------------------------------
    def integration(self, device):
        entry = device.get("primary_config_entry") or device.get("config_entry_id")
        return (self.entries.get(entry) or {}).get("domain", "?")

    def protocol(self, device):
        dom = self.integration(device)
        idents = [str(i[1]) for i in device.get("identifiers") or [] if len(i) >= 2]
        if dom in ZIGBEE or any(i.startswith("zigbee2mqtt") for i in idents):
            return "zigbee"
        if dom in ZWAVE:
            return "zwave"
        if dom in MATTER:
            return "matter"
        if dom in BLUETOOTH:
            return "bluetooth"
        if dom in CLOUD_AND_VIRTUAL:
            return "other"
        return "network"

    def device_type(self, device):
        dom = self.integration(device)
        clean = lambda t: re.sub(r"[-_]+", " ", str(t or "")).lower()
        name = f"{clean(device.get('name_by_user'))} {clean(device.get('name'))}"
        model = clean(device.get("model"))
        ents = self.ents_by_device.get(device["id"], [])
        domains = {e["entity_id"].split(".")[0] for e in ents}
        classes = {e.get("device_class") or e.get("original_device_class") or "" for e in ents}
        if dom in ("mobile_app", "adaptive_lighting"):
            return DOMAIN_TYPES[dom]
        for pattern, key in NAME_RULES:
            if re.search(pattern, name):
                return key
        if dom in DOMAIN_TYPES:
            return DOMAIN_TYPES[dom]
        for pattern, key in NAME_RULES:
            if re.search(pattern, model):
                return key
        for domain, key in ENTITY_TYPES:
            if domain in domains:
                return key
        for wanted, key in (({"motion", "occupancy", "presence"}, "motion"),
                            ({"door", "window", "opening", "garage_door"}, "contact"),
                            ({"moisture"}, "leak"), ({"outlet"}, "plug")):
            if classes & wanted:
                return key
        if "switch" in domains:
            return "switch"
        if "event" in domains:
            return "remote"
        if classes & {"temperature", "humidity"}:
            return "climate_sensor"
        if classes & {"power", "energy"}:
            return "energy"
        return "other"

    # --- references ------------------------------------------------------------------------
    def resolve(self, refs, seen=None):
        """Turn entity, device, area, and MQTT topic references into what the map draws.

        Returns (device ids, area ids, logic entity ids). Groups and switch_as_x helpers
        resolve to their members; scripts, scenes, and automations stay as they are, so
        the map can draw the call.
        """
        seen = seen if seen is not None else set()
        devs = {d for d in refs["device"] if d in self.devices}
        area_ids = {a for a in refs["area"] if a in self.areas}
        logic = set()
        for topic in refs["topic"]:
            parts = topic.split("/")
            dev = None
            if len(parts) >= 2 and parts[0] == "zigbee2mqtt":
                ieee = self.z2m_ieee_by_name.get(parts[1])
                dev = self.device_by_ident.get(f"zigbee2mqtt_{ieee}") if ieee else None
            else:
                dev = next((self.device_by_norm_name[norm(p)] for p in parts if norm(p) in self.device_by_norm_name), None)
            if dev:
                devs.add(dev)
        for eid in refs["entity"]:
            if eid in seen:
                continue
            seen.add(eid)
            ent = self.entities.get(eid) or self.entity_by_reg_id.get(eid)
            eid = ent["entity_id"] if ent else eid
            domain = eid.split(".")[0]
            if domain in LOGIC:
                logic.add(eid)
            elif ent and ent.get("device_id") in self.devices:
                devs.add(ent["device_id"])
            elif ent and ent.get("platform") in ("group", "switch_as_x"):
                members = (self.entries.get(ent.get("config_entry_id")) or {}).get("entities") or []
                d, a, lg = self.resolve(new_refs(entity=members), seen)
                devs |= d
                area_ids |= a
                logic |= lg
            else:
                self.unresolved[domain] += 1
        return devs, area_ids, logic

    def entity_area(self, entity_id):
        ent = self.entities.get(entity_id) or {}
        return ent.get("area_id") if ent.get("area_id") in self.areas else None


def norm(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def slug(text):
    """The object ID Home Assistant gives a YAML automation or scene with no ID (ASCII only)."""
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def new_refs(entity=()):
    return {"entity": set(entity), "device": set(), "area": set(), "topic": set()}


def as_list(value):
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def collect(node, refs, in_actions):
    """Gather every entity, device, area, and MQTT topic a trigger or action block names."""
    if isinstance(node, list):
        for item in node:
            collect(item, refs, in_actions)
        return
    if not isinstance(node, dict):
        return
    if in_actions and "condition" in node and not ("action" in node or "service" in node):
        return  # a condition step inside an action sequence
    for key, value in node.items():
        if in_actions and key in SKIP_IN_ACTIONS:
            continue
        if key in ("entity_id", "device_id", "area_id") or key.endswith("_entity_id"):
            refs[key.split("_")[-2]].update(v for v in as_list(value) if "{" not in v)
        elif key == "topic" and isinstance(value, str):
            refs["topic"].add(value)
        elif key in ("action", "service") and isinstance(value, str) and value.startswith("script.") \
                and value not in ("script.turn_on", "script.turn_off", "script.toggle", "script.reload"):
            refs["entity"].add(value)
        collect(value, refs, in_actions)


def build(home):
    # Logic nodes: every automation, script, and scene, keyed by its entity ID.
    auto_entity_by_uid = {str(e.get("unique_id")): e["entity_id"] for e in home.entities.values()
                          if e["entity_id"].startswith("automation.")}
    scene_entity_by_uid = {str(e.get("unique_id")): e["entity_id"] for e in home.entities.values()
                           if e["entity_id"].startswith("scene.")}
    logic = {}
    for auto in home.automations:
        trig, act = new_refs(), new_refs()
        collect(auto.get("triggers") or auto.get("trigger"), trig, False)
        collect(auto.get("actions") or auto.get("action"), act, True)
        eid = auto_entity_by_uid.get(str(auto.get("id"))) or f"automation.{slug(auto.get('alias') or auto.get('id'))}"
        logic[eid] = {"kind": "automation", "label": auto.get("alias") or str(auto.get("id")),
                      "description": auto.get("description") or "", "mode": auto.get("mode", "single"),
                      "trig": home.resolve(trig), "act": home.resolve(act)}
    for object_id, body in home.scripts.items():
        if not isinstance(body, dict):
            continue
        act = new_refs()
        collect(body.get("sequence"), act, True)
        logic[f"script.{object_id}"] = {"kind": "script", "label": body.get("alias") or object_id,
                                        "description": body.get("description") or "", "mode": body.get("mode", "single"),
                                        "trig": (set(), set(), set()), "act": home.resolve(act)}
    for scene in home.scenes:
        if not isinstance(scene, dict):
            continue
        eid = scene_entity_by_uid.get(str(scene.get("id"))) or f"scene.{slug(scene.get('name'))}"
        act = new_refs(entity=(scene.get("entities") or {}).keys())
        logic[eid] = {"kind": "scene", "label": scene.get("name") or eid, "description": "", "mode": "",
                      "trig": (set(), set(), set()), "act": home.resolve(act)}

    # Only real devices count: service entries and disabled devices are not on the map.
    real = [d for d in home.devices.values() if d.get("entry_type") != "service" and not d.get("disabled_by")]
    real_ids = {d["id"] for d in real}
    for item in logic.values():
        for side in ("trig", "act"):
            devs, area_ids, calls = item[side]
            item[side] = (devs & real_ids, area_ids, calls)

    # Keep what reaches the house: logic that touches a device or area, directly or through calls.
    def direct(item):
        return any(item["trig"][:2]) or any(item["act"][:2])
    shown = {eid for eid, item in logic.items() if direct(item)}
    changed = True
    while changed:
        changed = False
        for eid, item in logic.items():
            if eid not in shown and any(c in shown for c in item["act"][2]):
                shown.add(eid)
                changed = True

    nid = {}  # entity or device id -> node id
    for eid in shown:
        nid[eid] = f"{logic[eid]['kind']}:{eid.split('.', 1)[1]}"
    for d in real:
        nid[d["id"]] = f"dev:{d['id']}"

    edges = []
    for eid in sorted(shown):
        item, me = logic[eid], nid[eid]
        t_devs, t_areas, _ = item["trig"]
        a_devs, a_areas, calls = item["act"]
        edges += [{"source": nid[d], "target": me, "kind": "trigger"} for d in sorted(t_devs) if d in nid]
        edges += [{"source": f"area:{a}", "target": me, "kind": "trigger"} for a in sorted(t_areas)]
        edges += [{"source": me, "target": nid[d], "kind": "control"} for d in sorted(a_devs) if d in nid]
        edges += [{"source": me, "target": f"area:{a}", "kind": "control"} for a in sorted(a_areas)]
        edges += [{"source": me, "target": nid[c], "kind": "call"} for c in sorted(calls) if c in shown and c != eid]

    # Each logic node lives in its own area, the one area it touches, or "Across rooms".
    dev_area = {d["id"]: d.get("area_id") if d.get("area_id") in home.areas else None for d in real}
    nodes = []
    for d in real:
        dtype = home.device_type(d)
        nodes.append({
            "id": nid[d["id"]], "kind": "device",
            "label": d.get("name_by_user") or d.get("name") or d.get("model") or "Unnamed device",
            "parent": f"area:{dev_area[d['id']] or '__none'}", "protocol": home.protocol(d), "dtype": dtype,
            "icon": TYPES[dtype][0], "type_label": TYPES[dtype][1], "integration": home.integration(d),
            "manufacturer": d.get("manufacturer") or "", "model": d.get("model") or "",
            "entities": sorted(e["entity_id"] for e in home.ents_by_device.get(d["id"], [])),
        })
    for eid in sorted(shown):
        item = logic[eid]
        touched = {dev_area[d] or "__none" for d in item["trig"][0] | item["act"][0] if d in dev_area}
        touched |= item["trig"][1] | item["act"][1]
        home_area = home.entity_area(eid) or (next(iter(touched)) if len(touched) == 1 else "__shared")
        nodes.append({"id": nid[eid], "kind": item["kind"], "label": item["label"], "parent": f"area:{home_area}",
                      "entity_id": eid, "description": item["description"], "mode": item["mode"]})

    used = {n["parent"] for n in nodes} | {e["source"] for e in edges} | {e["target"] for e in edges}
    areas = []
    for area_id, area in sorted(home.areas.items(), key=lambda kv: kv[1]["name"].lower()):
        if f"area:{area_id}" in used:
            areas.append({"id": f"area:{area_id}", "kind": "area", "label": area["name"],
                          "icon": area.get("icon") or "mdi:texture-box"})
    if "area:__shared" in used:
        areas.append({"id": "area:__shared", "kind": "area", "label": "Across rooms", "icon": "mdi:home-outline",
                      "virtual": True})
    if "area:__none" in used:
        areas.append({"id": "area:__none", "kind": "area", "label": "No area", "icon": "mdi:help-circle-outline",
                      "virtual": True})

    kinds = Counter(n["kind"] for n in nodes)
    stats = {
        "areas": sum(1 for a in areas if not a.get("virtual")),
        "devices": kinds["device"], "automations": kinds["automation"], "scripts": kinds["script"],
        "scenes": kinds["scene"], "edges": len(edges),
        "automations_total": sum(1 for v in logic.values() if v["kind"] == "automation"),
        "not_on_map": sorted(v["label"] for k, v in logic.items() if k not in shown and v["kind"] == "automation"),
        "unresolved_refs_by_domain": dict(home.unresolved.most_common()),
    }
    return {"nodes": areas + nodes, "edges": edges, "stats": stats}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--registry", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    graph = build(Home(args.registry, args.config))
    pathlib.Path(args.out).write_text(json.dumps(graph, ensure_ascii=False, indent=1))
    print(json.dumps(graph["stats"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
