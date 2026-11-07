"""Tests that fetch-ha-data.sh never lets input reach the remote shell.

A fake `ssh` on PATH records every remote command, so no network or Home
Assistant host is needed.
"""

import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parent / "fetch-ha-data.sh"

FAKE_SSH = """#!/bin/bash
cmd="${@: -1}"
echo "$cmd" >> "$SSH_LOG"
case "$cmd" in
  true) exit 0 ;;
  *"command -v sudo"*) exit 0 ;;
  *"ls -1"*) printf '%s\\n' /config/esphome/good.yaml '/config/esphome/bad;touch_pwned.yaml' ;;
  *"test -d"*) exit 1 ;;
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


if __name__ == "__main__":
  unittest.main()
