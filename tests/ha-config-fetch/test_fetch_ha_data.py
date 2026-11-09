"""Tests that fetch-ha-data.sh never lets input reach the remote shell, and that
the registries it saves hold no credentials.

A fake `ssh` on PATH records every remote command, so no network or Home
Assistant host is needed.
"""

import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "ha-config-fetch"
SCRIPT = SKILL / "fetch-ha-data.sh"

FAKE_SSH = """#!/bin/bash
cmd="${@: -1}"
echo "$cmd" >> "$SSH_LOG"
case "$cmd" in
  true) exit 0 ;;
  *"command -v sudo"*) exit 0 ;;
  *"ls -1"*) printf '%s\\n' /config/esphome/good.yaml '/config/esphome/bad;touch_pwned.yaml' ;;
  *"test -d"*) exit 1 ;;
  *"cat '/config/configuration.yaml'"*)
    printf '%s\n' 'automation old: !include_dir_merge_list custom/automations/' \
      'script x: !include "../escape.yaml"' 'pkg: !include sub/pkg.yaml' '# off: !include nope.yaml' ;;
  *"cat '/config/sub/pkg.yaml'"*) echo 'automation: !include deeper.yaml' ;;
  *"find '/config/custom/automations'"*)
    printf '%s\n' /config/custom/automations/a.yaml '/config/custom/automations/b;touch pwned.yaml' \
      /config/custom/automations/.hidden/c.yaml /config/custom/automations/secrets.yaml ;;
  *"core.config_entries'"*)
    echo '{"data":{"entries":[{"entry_id":"E1","domain":"cloud","title":"me@example.com","data":{"password":"hunter2"},"options":{}}]}}' ;;
  *) echo data ;;
esac
"""


class FetchHaDataTests(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.work = Path(self.tmp.name)
    bin_dir = self.work / "bin"
    bin_dir.mkdir()
    fake_ssh = bin_dir / "ssh"
    fake_ssh.write_text(FAKE_SSH)
    fake_ssh.chmod(fake_ssh.stat().st_mode | stat.S_IEXEC)
    self.log = self.work / "ssh.log"
    self.env = {
      **os.environ,
      "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
      "SSH_LOG": str(self.log),
    }

  def run_script(self, *args):
    return subprocess.run(
      ["bash", str(SCRIPT), *args],
      cwd=self.work,
      env=self.env,
      capture_output=True,
      text=True,
      timeout=30,
    )

  def remote_commands(self):
    return self.log.read_text().splitlines() if self.log.exists() else []

  def test_rejects_config_dir_with_shell_syntax_before_any_ssh(self):
    result = self.run_script("/config; touch /tmp/pwned")
    self.assertEqual(result.returncode, 2, result.stdout)
    self.assertIn("Invalid config directory", result.stdout)
    self.assertEqual(self.remote_commands(), [])
    self.assertFalse((self.work / "ha-data").exists())

  def test_skips_esphome_file_with_unsafe_name(self):
    result = self.run_script()
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn("skipped: unsafe file name", result.stdout)
    self.assertTrue((self.work / "ha-data" / "esphome" / "good.yaml").exists())
    for command in self.remote_commands():
      self.assertNotIn("touch", command)

  def test_quotes_plain_config_dir(self):
    result = self.run_script("/homeassistant")
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn("cat '/homeassistant/automations.yaml'", self.remote_commands())

  def test_saves_the_installed_version(self):
    result = self.run_script()
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn("cat '/config/.HA_VERSION'", self.remote_commands())
    self.assertTrue((self.work / "ha-data" / ".HA_VERSION").exists())


  def test_follows_includes_inside_the_config_dir_only(self):
    result = self.run_script()
    self.assertEqual(result.returncode, 0, result.stdout)
    data = self.work / "ha-data"
    for rel in ("custom/automations/a.yaml", "sub/pkg.yaml", "sub/deeper.yaml"):
      self.assertTrue((data / rel).exists(), rel)
    commands = "\n".join(self.remote_commands())
    for name in ("escape", "nope", ".hidden", "secrets.yaml", "touch"):
      self.assertNotIn(name, commands)
    self.assertFalse((self.work / "escape.yaml").exists())

  def test_saves_config_entries_without_credentials(self):
    self.run_script()
    saved = (self.work / "ha-data" / "registry" / "entries.json").read_text()
    self.assertEqual(json.loads(saved), {"E1": {"domain": "cloud"}})
    self.assertFalse((self.work / "ha-data" / "registry" / "areas.json").exists())  # not JSON: dropped


def run_helper(name, *args, stdin=""):
  return subprocess.run(["python3", "-I", str(SKILL / name), *args], input=stdin,
                        capture_output=True, text=True, timeout=30)


class TrimRegistryTests(unittest.TestCase):
  def trim(self, kind, data):
    result = run_helper("trim_registry.py", kind, stdin=json.dumps({"data": data}))
    self.assertEqual(result.returncode, 0, result.stderr)
    return json.loads(result.stdout)

  def test_entries_keep_domain_and_helper_members_only(self):
    out = self.trim("entries", {"entries": [
      {"entry_id": "A", "domain": "hue", "title": "me@example.com", "data": {"api_key": "k"}, "options": {"x": 1}},
      {"entry_id": "B", "domain": "group", "title": "Lights", "options": {"group_type": "light", "entities": ["light.a"]}},
      {"entry_id": "C", "domain": "switch_as_x", "options": {"entity_id": "switch.fountain"}},
    ]})
    self.assertEqual(out, {"A": {"domain": "hue"},
                           "B": {"domain": "group", "group_type": "light", "entities": ["light.a"]},
                           "C": {"domain": "switch_as_x", "entities": ["switch.fountain"]}})

  def test_devices_lose_hardware_ids_and_service_names(self):
    out = self.trim("devices", {"devices": [
      {"id": "d1", "name": "Plug", "connections": [["mac", "aa:bb:cc:dd:ee:ff"]], "serial_number": "SN1",
       "configuration_url": "http://192.168.1.9", "identifiers": [["shelly", "SN1"], ["mqtt", "zigbee2mqtt_0x1"]]},
      {"id": "d2", "name": "me@example.com", "entry_type": "service", "identifiers": [["google_drive", "me"]]},
    ]})["data"]["devices"]
    text = json.dumps(out)
    for secret in ("aa:bb", "SN1", "192.168", "me@example.com"):
      self.assertNotIn(secret, text)
    self.assertEqual(out[0]["identifiers"], [["shelly"], ["mqtt", "zigbee2mqtt_0x1"]])

  def test_entities_keep_unique_ids_of_automations_and_scenes_only(self):
    out = self.trim("entities", {"entities": [
      {"entity_id": "automation.a", "unique_id": "123", "options": {"x": 1}},
      {"entity_id": "sensor.t", "unique_id": "aa:bb:cc_temperature"},
    ]})["data"]["entities"]
    self.assertEqual(out[0]["unique_id"], "123")
    self.assertNotIn("unique_id", out[1])
    self.assertNotIn("options", out[0])

  def test_rejects_input_that_is_not_a_registry(self):
    self.assertNotEqual(run_helper("trim_registry.py", "areas", stdin="data").returncode, 0)


class IncludePathsTests(unittest.TestCase):
  def test_names_safe_targets_relative_to_the_including_file(self):
    with tempfile.TemporaryDirectory() as tmp:
      pkg = Path(tmp) / "packages"
      pkg.mkdir()
      (pkg / "lights.yaml").write_text("\n".join([
        "automation: !include_dir_merge_list ../automations/",
        "script: !include 'scripts.yaml'",
        "# scene: !include scenes.yaml",
        "a: !include /etc/passwd.yaml",
        "b: !include ../../outside.yaml",
        "c: !include ../.storage/core.yaml",
        "d: !include ../secrets.yaml",
        "e: !include notes.txt",
        "f: !include_dir_named ../with space",
      ]))
      result = run_helper("include_paths.py", tmp, "packages/lights.yaml")
    self.assertEqual(result.stdout.splitlines(), ["dir automations", "file packages/scripts.yaml"])


if __name__ == "__main__":
  unittest.main()
