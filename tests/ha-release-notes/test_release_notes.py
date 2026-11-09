"""Tests for the release notes pipeline: parsing release posts, picking the releases between the
installed version and the target, matching items to a home, merging judgments, and rendering.

The posts below are made up, in the same Markdown layout as the real ones on home-assistant.io,
so no network is needed and none of the real posts' text is copied here. The snapshot tests need
PyYAML; the rest run on the standard library.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".claude" / "skills" / "ha-release-notes" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import post_parser  # noqa: E402

HAS_YAML = importlib.util.find_spec("yaml") is not None


def post(month, highlights, patches, breaking):
    return textwrap.dedent(f"""\
        ---
        layout: post
        title: "2026.{month}: A made-up release"
        date: 2026-{month:02d}-01 00:00:00
        ---

        Intro text about the release.

        <!--more-->

        - [Integrations](#integrations)

        """) + highlights + textwrap.dedent("""\

        ## Integrations

        ### New integrations

        - **[Garden Hose]**, added by [@someone]
          Waters the plants from Home Assistant.

        ### Noteworthy improvements to existing integrations

        - **[Zigbee Home Automation]** pairs faster, and **[ESPHome]** devices share a port. Thanks, [@x]!
        - **[Philips Hue]** shows scenes. Thanks, [@y]!

        ### Integration quality scale achievements

        - [Some Integration](/integrations/some)

        ### Now available to set up from the UI

        - **[Rest Sensor](/integrations/sensor.rest/)**, done by [@z]

        ### Farewell to the following

        - **Old Bus Times (OBT)** has been removed. Use the [GTFS](/integrations/gtfs/) integration instead.

        ## Other noteworthy changes

        - The **[Map card](/dashboards/map/)** is faster. Thanks, [@m]!
        - **[MQTT](/integrations/mqtt/)** logs less. Thanks, [@n]!

        ### Quieter logs

        The {% term "logger" "logbook" %} trims itself, and {% term automations %} explain why they ran.

        ```yaml
        ## not a heading
        logger:
        ```

        ## Patch releases

        """) + patches + textwrap.dedent("""\

        ## Need help? Join the community

        Ask on the forums.

        ## Backward-incompatible changes

        """) + breaking + textwrap.dedent("""\

        ## All changes

        Read the [full changelog](/changelogs/core-2026.x).

        [@someone]: https://github.com/someone
        [@x]: https://github.com/x
        [Garden Hose]: /integrations/garden_hose
        [Zigbee Home Automation]: /integrations/zha
        [ESPHome]: /integrations/esphome
        [Philips Hue]: /integrations/hue
        """)


POST_9 = post(9, "## Smarter scenes\n\nScenes remember more.\n\n### Scene previews\n\nSee before you save.\n",
              "### 2026.9.1 - September 5\n\n- Fix ZHA groups ([@a] - [#101])\n\n### 2026.9.2 - September 12\n\n"
              "- Fix Hue scenes ([@b] - [#102])\n\n[#101]: https://github.com/home-assistant/core/pull/101\n"
              "[#102]: https://github.com/home-assistant/core/pull/102\n",
              '{% details "Philips Hue" %}\n\nHue scenes moved.\n\n([@c] - [#103]) ([Philips Hue documentation])\n\n'
              "[#103]: https://github.com/home-assistant/core/pull/103\n[Philips Hue documentation]: /integrations/hue/\n\n"
              "{% enddetails %}\n")
POST_10 = post(10, "## A brand new map\n\nThe map is new.\n",
               "### 2026.10.1 - October 10\n\n- Fix MQTT reconnects ([@d] - [#201])\n\n"
               "[#201]: https://github.com/home-assistant/core/pull/201\n",
               '{% details "Old Car" %}\n\nOld Car is replaced by [New Car](/integrations/new_car/).\n\n'
               "([@e] - [#202]) ([Old Car documentation])\n\n[#202]: https://github.com/home-assistant/core/pull/202\n"
               "[Old Car documentation]: /integrations/old_car/\n\n{% enddetails %}\n\n"
               '{% details "State conditions" %}\n\nSome state conditions now fail validation.\n\n'
               "([@f] - [#203])\n\n[#203]: https://github.com/home-assistant/core/pull/203\n\n{% enddetails %}\n\n"
               '{% details "Robot vacuums" %}\n\n[Roomba](/integrations/roomba/) and [Neato](/integrations/neato/) '
               "rename an action.\n\n{% enddetails %}\n")
ATOM = ('<feed><entry><link href="https://www.home-assistant.io/blog/2026/10/01/release-202610/"/></entry>'
        '<entry><link href="https://www.home-assistant.io/blog/2026/09/01/release-20269/"/></entry></feed>')
CHANGELOG = "These are all the changes.\n[Release notes blog for this release](/blog/2026/{mm}/01/release-2026{m}/).\n"


def sources(folder):
    folder = Path(folder)
    folder.mkdir(parents=True)
    (folder / "atom.xml").write_text(ATOM)
    for month, text in ((9, POST_9), (10, POST_10)):
        (folder / f"core-2026.{month}.markdown").write_text(CHANGELOG.format(mm=f"{month:02d}", m=month))
        (folder / f"2026-{month:02d}-01-release-2026{month}.markdown").write_text(text)


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.post = post_parser.parse_post(POST_10, "2026.10", "https://example.org/release-202610/")
        self.items = {i["id"]: i for i in self.post["items"]}

    def test_anchors_match_the_site(self):
        self.assertEqual(post_parser.slug("2026.10.1 - October 10"), "2026101---october-10")
        self.assertEqual(post_parser.slug("Need help? Join the community"), "need-help-join-the-community")

    def test_sections_are_recognized_by_name(self):
        kinds = sorted({i["kind"] for i in self.post["items"]})
        self.assertEqual(kinds, ["breaking", "highlight", "improvement", "new_integration", "noteworthy",
                                 "now_in_ui", "patch", "removed"])
        self.assertEqual(self.items["2026.10/highlight/a-brand-new-map"]["url"],
                         "https://example.org/release-202610/#a-brand-new-map")
        self.assertEqual(self.post["patches"], ["2026.10.1"])
        self.assertEqual(self.post["warnings"], [])

    def test_domains_come_from_integration_links(self):
        self.assertEqual(self.items["2026.10/new_integration/garden_hose"]["domains"], ["garden_hose"])
        self.assertEqual(self.items["2026.10/improvement/zha"]["domains"], ["zha", "esphome"])
        self.assertEqual(self.items["2026.10/now_in_ui/rest"]["domains"], ["rest"])
        self.assertEqual(self.items["2026.10/noteworthy/mqtt"]["domains"], ["mqtt"])

    def test_breaking_change_takes_its_documentation_domain_first(self):
        self.assertEqual(self.items["2026.10/breaking/old-car"]["domains"], ["old_car"])
        self.assertEqual(self.items["2026.10/breaking/old-car"]["prs"],
                         ["https://github.com/home-assistant/core/pull/202"])
        self.assertEqual(self.items["2026.10/breaking/robot-vacuums"]["domains"], ["roomba", "neato"])
        self.assertEqual(self.items["2026.10/breaking/state-conditions"]["domains"], [])

    def test_removed_integration_domain_is_guessed_from_its_name(self):
        self.assertEqual(self.items["2026.10/removed/old-bus-times-obt"]["domains"], ["old_bus_times", "obt"])

    def test_patch_fixes_carry_their_version_and_pull_request(self):
        fix = self.items["2026.10.1/patch/201"]
        self.assertEqual((fix["release"], fix["title"]), ("2026.10.1", "Fix MQTT reconnects"))
        self.assertTrue(fix["url"].endswith("#2026101---october-10"))

    def test_text_is_plain_and_code_fences_hide_headings(self):
        note = self.items["2026.10/noteworthy/quieter-logs"]["text"]
        self.assertIn("The logbook trims itself, and automations explain why they ran.", note)
        self.assertNotIn("{%", note)
        self.assertFalse(any(i["title"] == "not a heading" for i in self.post["items"]))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        sources(self.work / "posts")
        self.out = self.work / "out"

    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, "-I", str(SCRIPTS / "release_notes.py"), *args], input=stdin,
                              capture_output=True, text=True, cwd=self.work, timeout=60)

    def build(self, *args):
        result = self.run_cli("build", "--source-dir", str(self.work / "posts"), "--out-dir", str(self.out), *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def report(self, target="2026.10.1"):
        return json.loads((self.out / f"ha-release-{target}.json").read_text())

    def test_span_covers_every_release_after_the_installed_version(self):
        self.build("--domains", "light,hue", "--from", "2026.9.1")
        ids = {i["id"] for i in self.report()["items"]}
        self.assertIn("2026.9.2/patch/102", ids)
        self.assertNotIn("2026.9.1/patch/101", ids)
        self.assertNotIn("2026.9/highlight/smarter-scenes", ids)
        self.assertIn("2026.10/highlight/a-brand-new-map", ids)
        self.assertIn("2026.10.1/patch/201", ids)
        self.assertEqual([p["release"] for p in self.report()["posts"]], ["2026.9", "2026.10"])

    def test_a_beta_counts_as_before_its_release(self):
        self.build("--domains", "light", "--from", "2026.10.0b2")
        self.assertIn("2026.10/highlight/a-brand-new-map", {i["id"] for i in self.report()["items"]})

    def test_without_an_installed_version_only_the_target_is_covered(self):
        result = self.build("--domains", "hue", "--target", "2026.9.1")
        report = self.report("2026.9.1")
        self.assertEqual([p["release"] for p in report["posts"]], ["2026.9"])
        self.assertNotIn("2026.9.2/patch/102", {i["id"] for i in report["items"]})
        self.assertTrue(any("installed version is unknown" in n for n in report["meta"]["notes"]))
        self.assertTrue(any("without SSH snapshots" in n for n in report["meta"]["notes"]))
        self.assertIn("To-do:", result.stdout)

    def test_up_to_date_writes_nothing(self):
        result = self.build("--domains", "hue", "--from", "2026.10.1")
        self.assertIn("UP TO DATE", result.stdout)
        self.assertFalse(self.out.exists())

    def test_matched_and_general_items_need_judgments(self):
        self.build("--domains", "hue,mqtt", "--from", "2026.9.1")
        items = {i["id"]: i for i in self.report()["items"]}
        self.assertEqual(items["2026.10/improvement/hue"]["match"]["domains"], ["hue"])
        self.assertIsNone(items["2026.10/improvement/zha"]["match"])
        self.assertIsNone(items["2026.10.1/patch/201"]["match"])  # patch fixes are the agent's to pick
        self.assertTrue(items["2026.10/breaking/state-conditions"]["general"])
        todo = (self.work / ".temp" / "release-notes" / "todo-2026.10.1.md").read_text()
        self.assertIn("[2026.10/breaking/state-conditions]", todo)
        self.assertIn("[2026.10.1/patch/201] Fix MQTT reconnects", todo)

    def judgments(self, **overrides):
        base = {
            "author": "Tester", "model": "test-model", "summary": "One thing to do.",
            "verdict": {"level": "review", "reason": "Move the `hue` scenes first."},
            "items": {
                "2026.10/highlight/a-brand-new-map": {"summary": "The map is redrawn <script>alert(1)</script>."},
                "2026.10/improvement/hue": {"affects": "none", "summary": "Hue shows scenes."},
                "2026.10/noteworthy/mqtt": {"affects": "none", "summary": "MQTT logs less."},
                "2026.10/breaking/state-conditions": {"affects": "action", "summary": "Some conditions fail.",
                                                      "impact": "Two automations use them.",
                                                      "action": "Remove `for` from [the check](https://example.org/x)."},
                "2026.10/breaking/robot-vacuums": {"affects": "none", "summary": "Vacuums rename an action."},
            },
        }
        base.update(overrides)
        return json.dumps(base)

    def test_assess_reports_missing_judgments_then_renders(self):
        self.build("--domains", "hue,mqtt", "--target", "2026.10.1")
        path = str(self.out / "ha-release-2026.10.1.json")
        partial = json.loads(self.judgments())
        del partial["items"]["2026.10/improvement/hue"]
        result = self.run_cli("assess", path, stdin=json.dumps(partial))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("- 2026.10/improvement/hue", result.stdout)

        result = self.run_cli("assess", path, stdin=self.judgments(items={
            "2026.10/improvement/hue": {"affects": "none", "summary": "Hue shows scenes."}}))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Verdict: ⚠️ Review first", result.stdout)
        self.assertIn("- action: [State conditions]", result.stdout)

        page = (self.out / "ha-release-2026.10.1.html").read_text()
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn('<a href="https://example.org/x">the check</a>', page)
        self.assertIn("<code>for</code>", page)
        self.assertIn('data-section="unaffected"', page)  # Old Car, which this home doesn't use
        self.assertNotIn("Old Car is replaced", page)  # the posts' own text stays out

        markdown = (self.out / "ha-release-2026.10.1.md").read_text()
        self.assertTrue(markdown.startswith('---\ntitle: "🏠 Home Assistant 2026.10.1"\nauthor: "Tester"'))
        self.assertIn("  - ha-2026.10.1", markdown)
        self.assertNotIn("\n# ", markdown)
        self.assertIn("## ⚠️ Needs your action", markdown)
        self.assertIn("- [Old Car](https://www.home-assistant.io/blog/2026/10/01/release-202610/"
                      "#backward-incompatible-changes) · 2026.10 · Breaking change", markdown)
        self.assertNotIn("|", markdown.split("---", 2)[2])
        self.assertIn("The map is redrawn \\<script\\>alert(1)\\</script\\>.", markdown)
        self.assertIn("Remove `for` from [the check](https://example.org/x).", markdown)

    def test_only_web_addresses_become_links(self):
        sys.path.insert(0, str(SCRIPTS))
        import report
        item = {"title": "Trap", "url": "javascript:alert(1)"}
        self.assertEqual(report.link(item), "Trap")
        self.assertEqual(report.link(item, html=False), "Trap")
        self.assertEqual(report.link({"title": "Ok [1]", "url": "https://example.org/#a"}, html=False),
                         "[Ok \\[1\\]](https://example.org/#a)")
        self.assertEqual(report.link({"title": "Paren", "url": "https://example.org/a_(b) c"}, html=False),
                         "[Paren](https://example.org/a_%28b%29%20c)")
        self.assertEqual(report.md_text("Run [this](javascript:alert(1)), see [docs](https://example.org/x)\nor <vbscript:x>."),
                         "Run \\[this\\](javascript:alert(1)), see [docs](https://example.org/x) or \\<vbscript:x\\>.")
        self.assertEqual(report.md_text("Keep `[x](y)` as code; **not bold**, [a (b)](https://example.org/a_(b))."),
                         "Keep `[x](y)` as code; \\*\\*not bold\\*\\*, [a (b)](https://example.org/a_%28b%29).")

    def test_assess_rejects_bad_judgments_without_saving(self):
        self.build("--domains", "hue", "--target", "2026.10.1")
        path = self.out / "ha-release-2026.10.1.json"
        before = path.read_text()
        cases = [
            {"items": {"nope/id": {"affects": "none", "summary": "x"}}},
            {"items": {"2026.10/improvement/hue": {"affects": "action", "summary": "x", "impact": "y"}}},
            {"items": {"2026.10/improvement/hue": {"affects": "maybe", "summary": "x"}}},
            {"verdict": {"level": "panic", "reason": "x"}},
            {"items": {}, "extra": 1},
            {"items": []},
            {"items": {"2026.10/improvement/hue": {"summary": "x"}}},  # affects left out
        ]
        for case in cases:
            result = self.run_cli("assess", str(path), stdin=json.dumps(case))
            self.assertEqual(result.returncode, 2, (case, result.stdout, result.stderr))
            self.assertEqual(path.read_text(), before)

    def test_a_snapshot_missing_a_registry_is_refused(self):
        data = self.work / "ha-data"
        (data / "registry").mkdir(parents=True)
        (data / "registry" / "entries.json").write_text("{}")
        result = self.run_cli("build", "--source-dir", str(self.work / "posts"), "--ha-data", str(data))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Missing devices.json, entities.json", result.stderr)
        self.assertFalse(self.out.exists())

    @unittest.skipUnless(HAS_YAML, "needs PyYAML")
    def test_snapshot_inventory_finds_integrations_and_their_automations(self):
        data = self.work / "ha-data"
        (data / "registry").mkdir(parents=True)
        (data / ".HA_VERSION").write_text("2026.9.1\n")
        (data / "registry" / "entries.json").write_text(json.dumps({"E1": {"domain": "hue"}, "E2": {"domain": "zha"}}))
        (data / "registry" / "devices.json").write_text(json.dumps({"data": {"devices": [
            {"id": "D1", "name": "Button", "primary_config_entry": "E2", "config_entries": ["E2"]}]}}))
        (data / "registry" / "entities.json").write_text(json.dumps({"data": {"entities": [
            {"entity_id": "light.desk", "platform": "hue", "config_entry_id": "E1"},
            {"entity_id": "automation.desk_on", "platform": "automation", "unique_id": "1"}]}}))
        (data / "configuration.yaml").write_text("automation: !include automations.yaml\nsensor:\n  - platform: rest\n")
        (data / "automations.yaml").write_text(textwrap.dedent("""\
            - id: '1'
              alias: Desk on
              triggers:
                - trigger: device
                  device_id: D1
                  domain: zha
                  type: remote_button_short_press
              actions:
                - action: light.turn_on
                  target:
                    entity_id: light.desk
            """))
        self.build("--ha-data", str(data))
        report = self.report()
        domains = report["inventory"]["domains"]
        self.assertEqual(domains["hue"]["used_by"], ["automation.desk_on"])
        self.assertEqual(domains["zha"]["used_by"], ["automation.desk_on"])
        self.assertTrue(domains["rest"]["yaml"])
        self.assertEqual(report["meta"]["installed"], "2026.9.1")
        items = {i["id"]: i for i in report["items"]}
        self.assertEqual(items["2026.10/improvement/zha"]["match"],
                         {"domains": ["zha"], "used_by": ["automation.desk_on"]})
        self.assertIsNotNone(items["2026.10/now_in_ui/rest"]["match"])


if __name__ == "__main__":
    unittest.main()
