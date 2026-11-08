"""Tests for the home map: the graph builder against a made-up home, and the rendered page.

Needs PyYAML. Run: python3 -m unittest discover -s .claude/skills/ha-home-map -p 'test_*.py'
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_graph  # noqa: E402


def run(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, check=True, timeout=120)


def make_home(out, *flags):
    run("demo_home.py", out, "--size", "medium", *flags)
    run("build_graph.py", "--registry", out / "registry", "--config", out / "config", "--out", out / "graph.json")
    return json.loads((out / "graph.json").read_text())


class DemoHomeGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = pathlib.Path(cls.tmp.name)
        cls.graph = make_home(cls.dir / "home", "--edge-cases")
        cls.by_id = {n["id"]: n for n in cls.graph["nodes"]}
        cls.by_label = {n["label"]: n for n in cls.graph["nodes"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def edges(self, kind=None, source=None, target=None):
        return [e for e in self.graph["edges"] if (kind is None or e["kind"] == kind)
                and (source is None or e["source"] == source) and (target is None or e["target"] == target)]

    def labels(self, ids):
        return sorted(self.by_id[i]["label"] for i in ids)

    def test_leaves_out_service_and_disabled_devices(self):
        for label in ("Sun", "Forecast", "Old Lamp"):
            self.assertNotIn(label, self.by_label)

    def test_every_edge_and_parent_points_at_a_node(self):
        for edge in self.graph["edges"]:
            self.assertIn(edge["source"], self.by_id)
            self.assertIn(edge["target"], self.by_id)
        for node in self.graph["nodes"]:
            if node["kind"] != "area":
                self.assertIn(node["parent"], self.by_id)

    def test_group_resolves_to_its_member_lights(self):
        auto = self.by_label["Living Room lights at sunset"]
        targets = [self.by_id[e["target"]] for e in self.edges("control", source=auto["id"])]
        self.assertGreaterEqual(len(targets), 2)
        self.assertTrue(all(t["kind"] == "device" and t["parent"] == "area:living_room" for t in targets))

    def test_switch_as_x_resolves_to_the_plug(self):
        auto = self.by_label["Fountain in the morning"]
        targets = [self.by_id[e["target"]] for e in self.edges("control", source=auto["id"])]
        self.assertEqual([t["dtype"] for t in targets], ["plug"])

    def test_mqtt_topic_trigger_finds_the_zigbee2mqtt_device(self):
        config = (self.dir / "home" / "config" / "automations.yaml").read_text()
        alias = re.search(r"alias: (.+)\n(?:.*\n){0,4}?\s+- trigger: mqtt", config).group(1).strip("'\"")
        sources = [self.by_id[e["source"]] for e in self.edges("trigger", target=self.by_label[alias]["id"])]
        self.assertTrue(sources)
        self.assertTrue(all(s["protocol"] == "zigbee" for s in sources))

    def test_calls_chain_automations_scripts_and_scenes(self):
        kinds = {(self.by_id[e["source"]]["kind"], self.by_id[e["target"]]["kind"]) for e in self.edges("call")}
        for pair in (("automation", "script"), ("script", "script"), ("automation", "automation")):
            self.assertIn(pair, kinds)
        good_night = self.by_label["Good night"]
        self.assertIn("Bedtime", self.labels(e["target"] for e in self.edges("call", source=good_night["id"])))

    def test_automation_touching_several_areas_sits_across_rooms(self):
        self.assertEqual(self.by_label["Good night"]["parent"], "area:__shared")

    def test_lists_automations_that_touch_no_device(self):
        off_map = self.graph["stats"]["not_on_map"]
        self.assertTrue(off_map)
        for label in off_map:
            self.assertNotIn(label, self.by_label)
        self.assertNotIn("Notify everyone", self.by_label)  # a script that touches no device

    def test_odd_names_survive_as_text(self):
        for label in ("</script><img src=x onerror=alert(1)>", "🎄 Christmas Tree", "Сауна", "和室"):
            self.assertIn(label, self.by_label)
        self.assertIn("Unnamed device", self.by_label)


class NoAreaTests(unittest.TestCase):
    def test_devices_without_an_area_go_to_no_area(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = make_home(pathlib.Path(tmp) / "home", "--no-areas")
        devices = [n for n in graph["nodes"] if n["kind"] == "device"]
        self.assertTrue(devices)
        self.assertEqual({d["parent"] for d in devices}, {"area:__none"})


class CollectTests(unittest.TestCase):
    def test_conditions_inside_actions_are_not_targets(self):
        refs = build_graph.new_refs()
        build_graph.collect([
            {"condition": "state", "entity_id": "binary_sensor.door", "state": "on"},
            {"if": [{"condition": "state", "entity_id": "input_boolean.guest", "state": "on"}],
             "then": [{"action": "light.turn_on", "target": {"entity_id": "light.hall"}}]},
            {"action": "tts.speak", "data": {"media_player_entity_id": "media_player.kitchen"}},
            {"action": "light.turn_on", "target": {"entity_id": "{{ states('input_text.lamp') }}"}},
            {"action": "script.bedtime"},
        ], refs, True)
        self.assertEqual(refs["entity"], {"light.hall", "media_player.kitchen", "script.bedtime"})


class IncludeTests(unittest.TestCase):
    def test_follows_includes_and_packages_inside_the_config_folder(self):
        files = {
            "configuration.yaml": """
                homeassistant:
                  packages: !include_dir_named packages
                automation: !include automations.yaml
                automation extra: !include_dir_merge_list more/
                automation outside: !include ../outside.yaml
                script: !include_dir_named scripts
                scene: !include scenes.yaml
            """,
            "automations.yaml": "- {id: '1', alias: UI automation}",
            "more/a.yaml": "- {alias: From a folder}",
            "more/.hidden/b.yaml": "- {alias: Hidden}",
            "more/secrets.yaml": "- {alias: Secret}",
            "scripts/bedtime.yaml": "sequence: []",
            "scenes.yaml": "- {name: Movie}",
            "packages/garden.yaml": """
                automation:
                  - alias: From a package
                script:
                  water: {sequence: []}
            """,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "config"
            for name, body in files.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(textwrap.dedent(body))
            (root.parent / "outside.yaml").write_text("- {alias: Outside}")
            automations, scripts, scenes = build_graph.load_logic(root)
        self.assertEqual(sorted(a["alias"] for a in automations), ["From a folder", "From a package", "UI automation"])
        self.assertEqual(sorted(scripts), ["bedtime", "water"])
        self.assertEqual([s["name"] for s in scenes], ["Movie"])


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        home = pathlib.Path(cls.tmp.name) / "home"
        make_home(home, "--edge-cases")
        out = home / "map.html"
        cls.log = run("render.py", home / "graph.json", out, "--title", "<Test & home>", "--offline").stdout
        cls.html = out.read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fills_every_placeholder(self):
        for marker in ("/*GRAPH_JSON*/", "<!--VENDOR_SCRIPTS-->", "/*FONT_FACES*/", "<!--TITLE-->"):
            self.assertNotIn(marker, self.html)

    def test_names_cannot_close_the_script(self):
        self.assertNotIn("</script><img", self.html)
        self.assertIn("<\\/script><img", self.html)
        self.assertIn("<title>&lt;Test &amp; home&gt;</title>", self.html)

    def test_loads_nothing_from_the_internet(self):
        self.assertIsNone(re.search(r"<(script|link|img)\b[^>]*\b(src|href)=[\"']?(https?:)?//", self.html))
        self.assertNotIn("url(http", self.html)
        self.assertNotIn("@import", self.html)

    def test_offline_falls_back_for_unknown_icons(self):
        self.assertIn("icon mdi:not-a-real-icon unavailable", self.log)
        self.assertNotIn('"mdi:not-a-real-icon"', self.html)


if __name__ == "__main__":
    unittest.main()
