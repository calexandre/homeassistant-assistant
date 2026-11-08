"""Generate a made-up home in Home Assistant's own file formats, to test and demo the home map.

Nothing in it is real. Writes OUT/registry/ (areas, devices, entities, and config entries already
reduced to what the map reads) and OUT/config/ (automations, scripts, scenes, and Zigbee2MQTT
devices), the two folders build_graph.py takes.

Usage: demo_home.py OUT [--size small|medium|large] [--no-areas] [--no-automations] [--edge-cases]

--edge-cases  adds names that have broken pages before: markup, emoji, non-Latin and right-to-left
              text, very long names, unknown icons, and a device with no name
"""
import argparse
import json
import pathlib
import random
import re
from collections import defaultdict

import yaml

SIZES = {
    "small": {"areas": 4, "devices": 24, "automations": 8, "scripts": 2, "scenes": 3},
    "medium": {"areas": 12, "devices": 170, "automations": 60, "scripts": 10, "scenes": 14},
    "large": {"areas": 30, "devices": 1000, "automations": 300, "scripts": 40, "scenes": 60},
}

# (name, icon, room kind), in the order a home gains them.
AREAS = [
    ("Living Room", "mdi:sofa", "living"), ("Kitchen", "mdi:silverware-fork-knife", "kitchen"),
    ("Main Bedroom", "mdi:bed-king", "bedroom"), ("Hallway", "mdi:door", "hall"),
    ("Bathroom", "mdi:shower", "bath"), ("Office", "mdi:desk", "office"),
    ("Dining Room", "mdi:table-chair", "dining"), ("Kids Room", "mdi:human-child", "bedroom"),
    ("Garden", "mdi:flower", "outdoor"), ("Garage", "mdi:garage", "garage"),
    ("Laundry", "mdi:washing-machine", "utility"), ("Guest Room", "mdi:bed", "bedroom"),
    ("Entrance", "mdi:door-closed", "hall"), ("Balcony", "mdi:balcony", "outdoor"),
    ("Attic", "mdi:home-roof", "utility"), ("Basement", "mdi:stairs-down", "utility"),
    ("Gym", "mdi:dumbbell", "office"), ("Workshop", "mdi:hammer-wrench", "garage"),
    ("Second Bathroom", "mdi:bathtub", "bath"), ("Library", "mdi:bookshelf", "office"),
    ("Nursery", "mdi:baby-face-outline", "bedroom"), ("Pool", "mdi:pool", "outdoor"),
    ("Cinema", "mdi:movie-open", "living"), ("Wine Cellar", "mdi:glass-wine", "utility"),
    ("Stairs", "mdi:stairs", "hall"), ("Server Closet", "mdi:server", "utility"),
    ("Teen Room", "mdi:gamepad-variant", "bedroom"), ("Pantry", "mdi:food", "kitchen"),
    ("Terrace", "mdi:umbrella-beach", "outdoor"), ("Music Room", "mdi:piano", "living"),
]

ROOM_DEVICES = {
    "living": "light light light light motion climate tv speaker blind blind plug button contact thermostat",
    "kitchen": "light light light motion leak appliance appliance plug climate speaker",
    "bedroom": "light light light button blind climate thermostat speaker motion contact",
    "bath": "light motion leak climate fan switch",
    "office": "light light plug plug motion climate speaker button blind",
    "hall": "light light motion motion contact lock camera button switch",
    "outdoor": "light light camera motion plant plant valve switch",
    "garage": "light motion contact camera plug switch energy vacuum",
    "utility": "light leak appliance energy valve plug climate",
    "dining": "light light light motion speaker blind climate",
}

# kind: (names, [(integration, manufacturer, model)], [(entity domain, suffix, device class)])
# Integration "z2m" means Zigbee2MQTT: the mqtt integration plus a zigbee2mqtt identifier.
KINDS = {
    "light": (["Ceiling Light", "Spotlights", "Floor Lamp", "LED Strip", "Pendant Lamp", "Wall Lamp", "Bedside Lamp"],
              [("z2m", "IKEA", "TRADFRI bulb E27 WS opal 1000lm"), ("zha", "Signify", "Hue white ambiance E27"),
               ("matter", "Nanoleaf", "Essentials A19"), ("wled", "WLED", "ESP32")],
              [("light", "", None)]),
    "motion": (["Motion Sensor", "Presence Sensor"],
               [("z2m", "Aqara", "RTCGQ11LM"), ("zha", "Signify", "SML001"), ("esphome", "Espressif", "LD2410")],
               [("binary_sensor", "occupancy", "occupancy"), ("sensor", "illuminance", "illuminance"),
                ("sensor", "battery", "battery")]),
    "contact": (["Door Sensor", "Window Sensor"],
                [("z2m", "Aqara", "MCCGQ11LM"), ("zwave_js", "Aeotec", "Door/Window Sensor 7")],
                [("binary_sensor", "contact", "door"), ("sensor", "battery", "battery")]),
    "climate": (["Temperature Sensor", "Climate Sensor"],
                [("z2m", "Aqara", "WSDCGQ11LM"), ("xiaomi_ble", "Xiaomi", "LYWSD03MMC")],
                [("sensor", "temperature", "temperature"), ("sensor", "humidity", "humidity")]),
    "plug": (["Smart Plug", "Power Plug", "Outlet"],
             [("z2m", "Innr", "SP 234"), ("zwave_js", "Aeotec", "Smart Switch 7"), ("shelly", "Shelly", "Plug S")],
             [("switch", "", None), ("sensor", "power", "power")]),
    "switch": (["Wall Switch", "Light Switch", "Relay"],
               [("zwave_js", "Fibaro", "FGS-213"), ("shelly", "Shelly", "1PM"), ("esphome", "Sonoff", "Basic R4")],
               [("switch", "", None)]),
    "button": (["Button", "Remote", "Dimmer"],
               [("z2m", "IKEA", "E1743"), ("zha", "Signify", "RWL021")],
               [("sensor", "action", None), ("sensor", "battery", "battery")]),
    "blind": (["Blinds", "Roller Shutter", "Curtains"],
              [("zwave_js", "Fibaro", "Roller Shutter 3"), ("matter", "Eve", "MotionBlinds"), ("z2m", "Aqara", "ZNCLDJ12LM")],
              [("cover", "", "shade")]),
    "thermostat": (["Thermostat", "Radiator Valve"],
                   [("matter", "ecobee", "Smart Thermostat Premium"), ("zwave_js", "Danfoss", "LC-13")],
                   [("climate", "", None)]),
    "tv": (["TV"], [("webostv", "LG", "OLED55C1"), ("androidtv_remote", "Sony", "Bravia XR")],
           [("media_player", "", "tv")]),
    "speaker": (["Speaker", "Nest Mini", "Sonos One"], [("cast", "Google", "Nest Mini"), ("sonos", "Sonos", "One SL")],
                [("media_player", "", "speaker")]),
    "lock": (["Door Lock"], [("zwave_js", "Yale", "Assure Lock 2"), ("matter", "Nuki", "Smart Lock Pro")],
             [("lock", "", None)]),
    "camera": (["Camera", "Doorbell"], [("reolink", "Reolink", "RLC-810A"), ("unifiprotect", "Ubiquiti", "G4 Doorbell")],
               [("camera", "", None), ("binary_sensor", "person", "occupancy")]),
    "leak": (["Leak Sensor"], [("z2m", "Aqara", "SJCGQ11LM")], [("binary_sensor", "water_leak", "moisture")]),
    "vacuum": (["Robot Vacuum"], [("roborock", "Roborock", "S8 Pro Ultra")], [("vacuum", "", None)]),
    "plant": (["Plant Sensor"], [("xiaomi_ble", "Xiaomi", "Flower Care")],
              [("sensor", "moisture", "moisture"), ("sensor", "conductivity", "conductivity")]),
    "appliance": (["Dishwasher", "Washing Machine", "Dryer", "Fridge", "Oven"],
                  [("home_connect", "Bosch", "Serie 6"), ("lg_thinq", "LG", "ThinQ")],
                  [("sensor", "status", "enum")]),
    "energy": (["Energy Meter"], [("shelly", "Shelly", "Pro 3EM")], [("sensor", "power", "power"), ("sensor", "energy", "energy")]),
    "fan": (["Ceiling Fan", "Extractor Fan"], [("tuya", "Tuya", "Fan Controller")], [("fan", "", None)]),
    "valve": (["Water Valve"], [("zwave_js", "Zooz", "ZAC36")], [("switch", "", None)]),
}

PEOPLE = ["Alex", "Sam", "Robin", "Kai"]
MOODS = ["Relax", "Bright", "Reading", "Nightlight", "Dinner", "Focus"]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


class DemoHome:
    def __init__(self, rng):
        self.rng = rng
        self.areas, self.devices, self.entities = [], [], []
        self.entries, self.entry_by_domain, self.z2m = {}, {}, {}
        self.automations, self.scripts, self.scenes = [], {}, []
        self.entity_ids, self.names = set(), set()
        self.by_area = defaultdict(lambda: defaultdict(list))  # area id -> kind -> devices
        self.ents = defaultdict(dict)  # device id -> entity domain -> first entity ID
        self.phones = []
        self.auto_eid = {}  # automation id -> entity ID
        self.group_light = self.fountain = None

    # --- registries --------------------------------------------------------------------------
    def uid(self):
        return f"{self.rng.getrandbits(128):032x}"

    def entry(self, domain, title=None, **extra):
        if not extra and title is None and domain in self.entry_by_domain:
            return self.entry_by_domain[domain]
        entry_id = self.uid()[:26].upper()
        self.entries[entry_id] = {"domain": domain, "title": title or domain.replace("_", " ").title(), **extra}
        if not extra and title is None:
            self.entry_by_domain[domain] = entry_id
        return entry_id

    def unique(self, text, taken):
        name, n = text, 2
        while name in taken:
            name, n = f"{text} {n}", n + 1
        taken.add(name)
        return name

    def entity(self, domain, name, device=None, platform="demo", entry_id=None, device_class=None):
        eid = self.unique(f"{domain}.{slug(name) or 'unnamed'}", self.entity_ids).replace(" ", "_")
        self.entities.append({
            "entity_id": eid, "id": self.uid(), "unique_id": self.uid(), "device_id": device and device["id"],
            "area_id": None, "platform": platform, "config_entry_id": entry_id, "disabled_by": None,
            "device_class": None, "original_device_class": device_class,
        })
        if device:
            self.ents[device["id"]].setdefault(domain, eid)
        return eid

    def device(self, name, area_id, kind):
        _, variants, ent_specs = KINDS[kind]
        integration, manufacturer, model = self.rng.choice(variants)
        name = self.unique(name, self.names)
        if integration == "z2m":
            ieee = f"0x{self.rng.getrandbits(64):016x}"
            domain, identifiers = "mqtt", [["mqtt", f"zigbee2mqtt_{ieee}"]]
            self.z2m[ieee] = {"friendly_name": name}
            registry_name, user_name = name, None
        else:
            domain, identifiers = integration, [[integration, self.uid()[:12]]]
            registry_name, user_name = model, name  # most integrations name a device after its model
        entry_id = self.entry(domain)
        dev = {
            "id": self.uid(), "name": registry_name, "name_by_user": user_name, "area_id": area_id,
            "identifiers": identifiers, "connections": [], "manufacturer": manufacturer, "model": model,
            "entry_type": None, "disabled_by": None, "config_entries": [entry_id], "primary_config_entry": entry_id,
        }
        self.devices.append(dev)
        for ent_domain, suffix, device_class in ent_specs:
            self.entity(ent_domain, f"{name} {suffix}", dev, domain, entry_id, device_class)
        self.by_area[area_id][kind].append(dev)
        return dev

    def ent(self, device, domain):
        return self.ents[device["id"]].get(domain)

    def friendly(self, device):
        return device["name_by_user"] or device["name"]

    def build_house(self, size, no_areas):
        n_areas = size["areas"]
        for name, icon, kind in AREAS[:n_areas]:
            self.areas.append({"id": slug(name), "name": name, "icon": icon, "kind": kind})
        # Infrastructure and personal devices that usually have no area.
        bridge = self.device("Zigbee2MQTT Bridge", None, "switch")
        bridge["identifiers"] = [["mqtt", f"zigbee2mqtt_bridge_0x{self.rng.getrandbits(64):016x}"]]
        bridge.update(manufacturer="Zigbee2MQTT", model="Bridge", name="Zigbee2MQTT Bridge", name_by_user=None)
        for person in PEOPLE[:max(2, n_areas // 6)]:
            entry_id = self.entry("mobile_app", title=f"{person}'s Phone", unique=True)
            phone = {"id": self.uid(), "name": f"{person}'s Phone", "name_by_user": None, "area_id": None,
                     "identifiers": [["mobile_app", self.uid()[:16]]], "connections": [], "manufacturer": "Google",
                     "model": "Pixel 9", "entry_type": None, "disabled_by": None, "config_entries": [entry_id],
                     "primary_config_entry": entry_id}
            self.devices.append(phone)
            self.entity("device_tracker", phone["name"], phone, "mobile_app", entry_id)
            self.entity("sensor", f"{phone['name']} battery level", phone, "mobile_app", entry_id, "battery")
            self.phones.append(phone)
        for name, model, domain in (("Router", "RT-AX88U", "asuswrt"), ("Z-Wave Controller", "ZST39 LR", "zwave_js")):
            entry_id = self.entry(domain)
            self.devices.append({"id": self.uid(), "name": model, "name_by_user": name, "area_id": None,
                                 "identifiers": [[domain, self.uid()[:12]]], "connections": [], "manufacturer": "",
                                 "model": model, "entry_type": None, "disabled_by": None,
                                 "config_entries": [entry_id], "primary_config_entry": entry_id})
        # Not on the map: service entries and a disabled device.
        for name, domain in (("Sun", "sun"), ("Forecast", "met")):
            entry_id = self.entry(domain)
            self.devices.append({"id": self.uid(), "name": name, "name_by_user": None, "area_id": None,
                                 "identifiers": [[domain, entry_id]], "connections": [], "manufacturer": "",
                                 "model": "", "entry_type": "service", "disabled_by": None,
                                 "config_entries": [entry_id], "primary_config_entry": entry_id})
        self.device("Old Lamp", None, "light")["disabled_by"] = "user"

        # Room devices: each area gets a share of the rest, one larger room per big home.
        budget = size["devices"] - len(self.devices)
        unassigned = max(2, budget // 20)  # paired but never given an area, named by their address
        weights = [self.rng.uniform(0.6, 1.4) for _ in self.areas]
        if n_areas >= 20:
            weights[n_areas // 2] = 5
        total = sum(weights)
        for area, weight in zip(self.areas, weights):
            kinds = ROOM_DEVICES[area["kind"]].split()
            count = max(2, round((budget - unassigned) * weight / total))
            for i in range(count):
                kind = kinds[i] if i < len(kinds) else self.rng.choice(kinds)
                self.device(f"{area['name']} {self.rng.choice(KINDS[kind][0])}", area["id"], kind)
        for _ in range(unassigned):
            kind = self.rng.choice(["motion", "contact", "climate", "plug", "button"])
            dev = self.device(f"0x{self.rng.getrandbits(64):016x}", None, kind)
            dev["name"], dev["name_by_user"] = dev["name_by_user"] or dev["name"], None
        if no_areas:  # automations still pick devices by the room they were made for
            for dev in self.devices:
                dev["area_id"] = None

        # A light group and a switch shown as a light.
        living = self.by_area[self.areas[0]["id"]]
        lights = [self.ent(d, "light") for d in living["light"]][:3]
        if len(lights) >= 2:
            entry_id = self.entry("group", title=f"{self.areas[0]['name']} Lights", unique=True,
                                  group_type="light", entities=lights)
            self.group_light = self.entity("light", f"{self.areas[0]['name']} Lights", None, "group", entry_id)
        plugs = [d for a in self.areas for d in self.by_area[a["id"]]["plug"]]
        if plugs:
            switch = self.ent(plugs[-1], "switch")
            entry_id = self.entry("switch_as_x", title="Fountain", unique=True, entities=[switch])
            self.fountain = self.entity("light", "Fountain", None, "switch_as_x", entry_id)

    # --- logic -------------------------------------------------------------------------------
    def pick(self, area, kind, count=1):
        devs = self.by_area[area["id"]][kind]
        return self.rng.sample(devs, min(count, len(devs))) if devs else []

    def anywhere(self, kind):
        return [d for a in self.areas for d in self.by_area[a["id"]][kind]]

    def add_automation(self, alias, triggers, actions, mode="single", legacy=False, conditions=None):
        alias = self.unique(alias, {a["alias"] for a in self.automations})
        auto_id = str(1700000000000 + len(self.automations))
        if legacy:  # the pre-2024.10 keys, which many configs still use
            for t in triggers:
                t["platform"] = t.pop("trigger")
            for a in actions:
                if "action" in a:
                    a["service"] = a.pop("action")
            body = {"id": auto_id, "alias": alias, "description": "", "trigger": triggers,
                    "condition": conditions or [], "action": actions, "mode": mode}
        else:
            body = {"id": auto_id, "alias": alias, "description": "", "triggers": triggers,
                    "conditions": conditions or [], "actions": actions, "mode": mode}
        self.automations.append(body)
        eid = self.entity("automation", alias, platform="automation")
        self.entities[-1]["unique_id"] = auto_id
        self.auto_eid[auto_id] = eid
        return eid

    def build_scenes(self, count):
        rooms = [a for a in self.areas if self.by_area[a["id"]]["light"]]
        for i in range(count):
            if not rooms:
                return
            area = rooms[i % len(rooms)]
            mood = MOODS[(i // len(rooms)) % len(MOODS)]
            name = self.unique(f"{area['name']} {mood}", {s["name"] for s in self.scenes})
            entities = {self.ent(d, "light"): {"state": "on", "brightness": self.rng.choice([60, 128, 255])}
                        for d in self.pick(area, "light", 3)}
            scene_id = str(1600000000000 + i)
            self.scenes.append({"id": scene_id, "name": name, "entities": entities})
            self.entity("scene", name, platform="homeassistant")
            self.entities[-1]["unique_id"] = scene_id

    def scene_for(self, area):
        names = [s["name"] for s in self.scenes if s["name"].startswith(area["name"] + " ")]
        return f"scene.{slug(names[0])}" if names else None

    def build_scripts(self, count):
        bedrooms = [a["id"] for a in self.areas if a["kind"] == "bedroom"] or [self.areas[0]["id"]]
        off_scripts = []
        for area in self.areas[:max(1, count - 3)]:
            object_id = f"{area['id']}_lights_off"
            self.scripts[object_id] = {"alias": f"{area['name']} lights off", "mode": "single",
                                       "sequence": [{"action": "light.turn_off", "target": {"area_id": area["id"]}}]}
            off_scripts.append(object_id)
        if count > 1:
            sequence = [{"action": "light.turn_off", "target": {"area_id": bedrooms}}]
            night = next((s["name"] for s in self.scenes if "Nightlight" in s["name"]), None)
            if night:
                sequence.append({"action": "scene.turn_on", "target": {"entity_id": f"scene.{slug(night)}"}})
            self.scripts["bedtime"] = {"alias": "Bedtime", "mode": "restart", "sequence": sequence}
        if count > 2:
            locks = [self.ent(d, "lock") for d in self.anywhere("lock")]
            sequence = [{"action": f"script.{s}"} for s in off_scripts[:4]]
            sequence.append({"if": [{"condition": "state", "entity_id": "input_boolean.guests", "state": "off"}],
                             "then": [{"action": "lock.lock", "target": {"entity_id": locks}}] if locks else []})
            self.scripts["leave_home"] = {"alias": "Leave home", "mode": "single", "sequence": sequence}
        if count > 3:  # touches no device, so it stays off the map
            self.scripts["notify_everyone"] = {"alias": "Notify everyone", "mode": "queued",
                                               "fields": {"message": {"selector": {"text": None}}},
                                               "sequence": [{"action": "notify.notify",
                                                             "data": {"message": "{{ message }}"}}]}

    def build_automations(self, count):
        templates = [
            (self.a_motion_light, 6), (self.a_button, 4), (self.a_door, 2), (self.a_sunset_blinds, 2),
            (self.a_climate, 2), (self.a_tv_scene, 1), (self.a_leak, 1), (self.a_plant, 1),
            (self.a_appliance, 1), (self.a_arrive, 1), (self.a_vacuum, 1), (self.a_chain, 1), (self.a_offmap, 1),
        ]
        funcs, weights = zip(*templates)
        for once in (self.a_goodnight, self.a_leave, self.a_helpers):
            once()
        attempts = 0
        while len(self.automations) < count and attempts < count * 30:
            attempts += 1
            area = self.rng.choice(self.areas)
            self.rng.choices(funcs, weights)[0](area)

    def a_motion_light(self, area):
        motion, lights = self.pick(area, "motion"), self.pick(area, "light", self.rng.randint(1, 3))
        if motion and lights:
            self.add_automation(
                f"{area['name']} motion lights",
                [{"trigger": "state", "entity_id": self.ent(motion[0], "binary_sensor"), "to": "on"}],
                [{"action": "light.turn_on", "target": {"entity_id": [self.ent(d, "light") for d in lights]}},
                 {"wait_for_trigger": [{"trigger": "state", "entity_id": self.ent(motion[0], "binary_sensor"),
                                        "to": "off", "for": {"minutes": 2}}]},
                 {"action": "light.turn_off", "target": {"entity_id": [self.ent(d, "light") for d in lights]}}],
                mode="restart",
                conditions=[{"condition": "numeric_state", "entity_id": f"sensor.{slug(self.friendly(motion[0]))}_illuminance",
                             "below": 30}])

    def a_button(self, area):
        button = self.pick(area, "button")
        if not button:
            return
        button = button[0]
        if button["identifiers"][0][1].startswith("zigbee2mqtt_"):
            trigger = {"trigger": "mqtt", "topic": f"zigbee2mqtt/{button['name']}/action", "payload": "on"}
        else:
            trigger = {"trigger": "device", "device_id": button["id"], "domain": "zha",
                       "type": "remote_button_short_press", "subtype": "turn_on"}
        scene = self.scene_for(area)
        action = ({"action": "scene.turn_on", "target": {"entity_id": scene}} if scene and self.rng.random() < 0.5
                  else {"action": "light.toggle", "target": {"area_id": area["id"]}})
        self.add_automation(f"{area['name']} button", [trigger], [action])

    def a_door(self, area):
        contact = self.pick(area, "contact")
        if contact:
            lights = self.pick(area, "light")
            actions = [{"action": "notify.notify", "data": {"message": f"{self.friendly(contact[0])} opened"}}]
            if lights:
                actions.append({"action": "light.turn_on", "target": {"entity_id": self.ent(lights[0], "light")}})
            self.add_automation(f"{area['name']} door opened",
                                [{"trigger": "state", "entity_id": self.ent(contact[0], "binary_sensor"), "to": "on"}],
                                actions, legacy=self.rng.random() < 0.5)

    def a_sunset_blinds(self, area):
        if self.pick(area, "blind"):
            self.add_automation(f"Close {area['name']} blinds at sunset",
                                [{"trigger": "sun", "event": "sunset", "offset": "-00:15:00"}],
                                [{"action": "cover.close_cover", "target": {"area_id": area["id"]}}], legacy=True)

    def a_climate(self, area):
        sensor = self.pick(area, "climate")
        target = self.pick(area, "fan") or self.pick(area, "thermostat")
        if sensor and target:
            dev = target[0]
            action = ({"action": "fan.turn_on", "target": {"entity_id": self.ent(dev, "fan")}} if self.ent(dev, "fan")
                      else {"action": "climate.set_hvac_mode", "target": {"device_id": dev["id"]},
                            "data": {"hvac_mode": "cool"}})
            self.add_automation(f"{area['name']} too warm",
                                [{"trigger": "numeric_state", "entity_id": self.ent(sensor[0], "sensor"), "above": 25}],
                                [action])

    def a_tv_scene(self, area):
        tv = self.pick(area, "tv")
        scene = self.scene_for(area)
        if tv and scene:
            self.add_automation(f"Dim {area['name']} for TV",
                                [{"trigger": "state", "entity_id": self.ent(tv[0], "media_player"), "to": "playing"}],
                                [{"action": "scene.turn_on", "target": {"entity_id": scene}}])

    def a_leak(self, area):
        leak, valves = self.pick(area, "leak"), self.anywhere("valve")
        if leak:
            actions = [{"action": "notify.notify", "data": {"message": "Water leak!"}}]
            if valves:
                actions.insert(0, {"action": "switch.turn_off", "target": {"entity_id": self.ent(valves[0], "switch")}})
            self.add_automation(f"{area['name']} leak", [{"trigger": "state",
                                                          "entity_id": self.ent(leak[0], "binary_sensor"), "to": "on"}],
                                actions, mode="single")

    def a_plant(self, area):
        plant, valves = self.pick(area, "plant"), self.pick(area, "valve") or self.anywhere("valve")
        if plant and valves:
            self.add_automation(f"Water {area['name']} plants",
                                [{"trigger": "numeric_state", "entity_id": self.ent(plant[0], "sensor"), "below": 20}],
                                [{"action": "switch.turn_on", "target": {"entity_id": self.ent(valves[0], "switch")}},
                                 {"delay": {"minutes": 5}},
                                 {"action": "switch.turn_off", "target": {"entity_id": self.ent(valves[0], "switch")}}])

    def a_appliance(self, area):
        appliance, speakers = self.pick(area, "appliance"), self.anywhere("speaker")
        if appliance and speakers:
            speaker = self.rng.choice(speakers)
            self.add_automation(f"{self.friendly(appliance[0])} finished",
                                [{"trigger": "state", "entity_id": self.ent(appliance[0], "sensor"), "to": "finished"}],
                                [{"action": "tts.speak", "target": {"entity_id": "tts.google_translate_en_com"},
                                  "data": {"media_player_entity_id": self.ent(speaker, "media_player"),
                                           "message": "Done"}}])

    def a_arrive(self, area):
        if area["kind"] == "hall" and self.phones:
            phone = self.rng.choice(self.phones)
            self.add_automation(f"{phone['name'].split(chr(39))[0]} arrives home",
                                [{"trigger": "state", "entity_id": self.ent(phone, "device_tracker"), "to": "home"}],
                                [{"action": "light.turn_on", "target": {"area_id": area["id"]}}])

    def a_vacuum(self, area):
        vacuum = self.pick(area, "vacuum")
        if vacuum:
            self.add_automation("Vacuum when everyone leaves",
                                [{"trigger": "state", "entity_id": self.ent(p, "device_tracker"), "to": "not_home"}
                                 for p in self.phones],
                                [{"action": "vacuum.start", "target": {"entity_id": self.ent(vacuum[0], "vacuum")}}])

    def a_chain(self, area):
        if len(self.automations) > 3:
            target = self.rng.choice(self.automations[:len(self.automations) // 2])
            button = self.pick(area, "button")
            if button:
                self.add_automation(f"{area['name']} button runs {target['alias']}",
                                    [{"trigger": "device", "device_id": button[0]["id"], "domain": "zha",
                                      "type": "remote_button_long_press", "subtype": "turn_on"}],
                                    [{"action": "automation.trigger",
                                      "target": {"entity_id": self.auto_eid[target["id"]]}}])

    def a_offmap(self, area):
        # Touches no device or area, so the map lists it as "not on the map". About 1 in 20.
        if sum(1 for a in self.automations if "persistent_notification" in str(a)) * 20 > len(self.automations):
            return
        self.add_automation(self.rng.choice(["Weekly backup reminder", "Notify on update", "Restart notice"]),
                            [{"trigger": "homeassistant", "event": "start"}],
                            [{"action": "persistent_notification.create", "data": {"message": "{{ now() }}"}}])

    def a_goodnight(self):
        bedrooms = [a for a in self.areas if a["kind"] == "bedroom"]
        buttons = [d for a in bedrooms for d in self.by_area[a["id"]]["button"]]
        if buttons and "bedtime" in self.scripts:
            actions = [{"action": "script.bedtime"}]
            locks = self.anywhere("lock")
            if locks:
                actions.append({"action": "lock.lock", "target": {"entity_id": self.ent(locks[0], "lock")}})
            actions.append({"action": "light.turn_off",
                            "target": {"area_id": [a["id"] for a in self.areas if a["kind"] in ("living", "kitchen")]}})
            self.add_automation("Good night", [{"trigger": "device", "device_id": buttons[0]["id"], "domain": "zha",
                                                "type": "remote_button_double_press", "subtype": "turn_off"}],
                                actions)

    def a_helpers(self):
        # Targets a light group and a switch shown as a light: the map draws their member devices.
        if self.group_light:
            self.add_automation(f"{self.areas[0]['name']} lights at sunset",
                                [{"trigger": "sun", "event": "sunset"}],
                                [{"action": "light.turn_on", "target": {"entity_id": self.group_light}}])
        if self.fountain:
            self.add_automation("Fountain in the morning", [{"trigger": "time", "at": "08:00:00"}],
                                [{"action": "light.turn_on", "target": {"entity_id": self.fountain}}])

    def a_leave(self):
        if "leave_home" in self.scripts and self.phones:
            self.add_automation("Everyone left", [{"trigger": "state", "entity_id": "zone.home", "to": "0"}],
                                [{"action": "script.turn_on", "target": {"entity_id": "script.leave_home"}}])

    # --- edge cases ----------------------------------------------------------------------------
    def add_edge_cases(self):
        renames = [
            ("Сауна", None), ("和室", "mdi:not-a-real-icon"), ("غرفة المعيشة", "mdi:sofa-outline"),
            ("Upstairs landing between the kids' rooms and the main bedroom", "mdi:stairs-up"),
        ]
        for area, (name, icon) in zip(self.areas[-len(renames):], renames):
            area["name"], area["icon"] = name, icon
        odd = ["</script><img src=x onerror=alert(1)>", '<b>Bold</b> & "quoted" \'name\'', "🎄 Christmas Tree",
               "天井ライト", "مصباح السقف", "Spotlights over the kitchen island next to the window by the door"]
        room_devices = [d for d in self.devices if d["area_id"]]
        for dev, name in zip(self.rng.sample(room_devices, len(odd)), odd):
            dev["name_by_user"] = name
        nameless = self.rng.choice(room_devices)
        nameless["name"] = nameless["name_by_user"] = nameless["model"] = None
        if self.automations:
            self.automations[-1]["alias"] = ("When the front door opens after sunset and nobody is home, turn on "
                                             "every light in the hallway and send a notification to everyone")
            self.automations[-2 % len(self.automations)]["alias"] = "<script>alert('alias')</script>"
            self.automations[-3 % len(self.automations)]["description"] = "<img src=x onerror=alert('desc')>"

    # --- output ------------------------------------------------------------------------------
    def write(self, out):
        reg, cfg = out / "registry", out / "config"
        (cfg / "zigbee2mqtt").mkdir(parents=True, exist_ok=True)
        reg.mkdir(parents=True, exist_ok=True)
        areas = [{"id": a["id"], "name": a["name"], "icon": a["icon"], "floor_id": None, "aliases": [],
                  "labels": [], "picture": None} for a in self.areas]
        for key, plural, items in (("area", "areas", areas), ("device", "devices", self.devices),
                                   ("entity", "entities", self.entities)):
            body = {"version": 1, "minor_version": 1, "key": f"core.{key}_registry", "data": {plural: items}}
            (reg / f"{plural}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1))
        (reg / "entries.json").write_text(json.dumps(self.entries, ensure_ascii=False, indent=1))
        dump = lambda data: yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120)
        (cfg / "automations.yaml").write_text(dump(self.automations) if self.automations else "[]\n")
        (cfg / "scripts.yaml").write_text(dump(self.scripts) if self.scripts else "{}\n")
        (cfg / "scenes.yaml").write_text(dump(self.scenes) if self.scenes else "[]\n")
        (cfg / "zigbee2mqtt" / "devices.yaml").write_text(dump(self.z2m))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out")
    parser.add_argument("--size", choices=SIZES, default="medium")
    parser.add_argument("--no-areas", action="store_true", help="leave every device without an area")
    parser.add_argument("--no-automations", action="store_true", help="devices only")
    parser.add_argument("--edge-cases", action="store_true", help="add names that have broken pages before")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    size = SIZES[args.size]
    home = DemoHome(random.Random(args.seed))
    home.build_house(size, args.no_areas)
    if not args.no_automations:
        home.build_scenes(size["scenes"])
        home.build_scripts(size["scripts"])
        home.build_automations(size["automations"])
    if args.edge_cases:
        home.add_edge_cases()
    out = pathlib.Path(args.out)
    home.write(out)
    print(f"{len(home.areas)} areas, {len(home.devices)} devices, {len(home.automations)} automations, "
          f"{len(home.scripts)} scripts, {len(home.scenes)} scenes -> {out}")


if __name__ == "__main__":
    main()
