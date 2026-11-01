import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / ".github" / "hooks" / "ssh-ha-readonly-guard.py"


class HookTests(unittest.TestCase):
    def run_hook(self, launcher, payload):
        result = subprocess.run(
            launcher,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def test_all_git_subcommands_and_payload_formats_are_allowed(self):
        commands = (
            "git status --short --branch",
            'git commit -m "Update metadata"',
            "git push origin HEAD:main",
            "git reset --soft HEAD~1",
            "git rebase origin/main",
            "git custom-alias",
            r'& "C:\Program Files\Git\bin\git.exe" push origin HEAD:main',
            "GIT_TERMINAL_PROMPT=0 git fetch origin",
            "env git push origin HEAD:main",
            "git status; git diff",
        )
        for command in commands:
            arguments = {"command": command}
            payloads = (
                arguments,
                {"tool_input": arguments},
                {"toolArgs": arguments},
                {"toolArgs": json.dumps(arguments)},
            )
            for payload in payloads:
                with self.subTest(command=command, payload=payload):
                    decision = self.run_hook([sys.executable, str(GUARD)], payload)
                    self.assertNotEqual(decision.get("permissionDecision"), "deny")

    def test_ssh_reads_are_allowed_and_writes_are_denied(self):
        cases = (
            ('ssh homeassistant "cat /config/configuration.yaml"', False),
            ('ssh other-host "touch /tmp/example"', False),
            ("ssh homeassistant", True),
            ('ssh homeassistant "touch /config/example"', True),
            ("scp example homeassistant:/config/example", True),
            ("ssh homeassistant 'touch /config/example; git status", True),
        )
        for command, denied in cases:
            with self.subTest(command=command):
                decision = self.run_hook(
                    [sys.executable, str(GUARD)], {"command": command}
                )
                self.assertEqual(decision.get("permissionDecision") == "deny", denied)

    @unittest.skipUnless(os.name == "nt", "Windows launcher regression")
    def test_repository_and_plugin_windows_launchers(self):
        repository = json.loads(
            (ROOT / ".github" / "hooks" / "ssh-ha-readonly-guard.json").read_text()
        )["hooks"]["PreToolUse"][0]
        plugin = json.loads((ROOT / "hooks" / "hooks.json").read_text())[
            "hooks"
        ]["PreToolUse"][0]["hooks"][0]
        powershell = shutil.which("pwsh")
        self.assertIsNotNone(powershell, "PowerShell 7 is required to run the hook")
        for config in (repository, plugin):
            for command, denied in (
                ('git commit -m "Update metadata"', False),
                ("git push origin HEAD:main", False),
                ('ssh homeassistant "touch /config/example"', True),
            ):
                with self.subTest(config=config, command=command):
                    decision = self.run_hook(
                        [powershell, "-NoProfile", "-NonInteractive", "-Command",
                         config["powershell"]],
                        {"toolArgs": json.dumps({"command": command})},
                    )
                    self.assertEqual(
                        decision.get("permissionDecision") == "deny", denied
                    )


if __name__ == "__main__":
    unittest.main()
