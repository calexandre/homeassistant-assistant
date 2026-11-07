import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / ".github" / "hooks" / "ssh-ha-readonly-guard.py"
REPOSITORY_HOOKS = ROOT / ".github" / "hooks" / "ssh-ha-readonly-guard.json"
PLUGIN_HOOKS = ROOT / "hooks" / "hooks.json"


class HookTests(unittest.TestCase):
    def run_hook(self, launcher, payload, env=None):
        result = subprocess.run(
            launcher,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=10,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        decision = json.loads(result.stdout) if result.stdout.strip() else {}
        if decision:
            # Copilot reads the top level; Claude Code reads hookSpecificOutput.
            nested = decision["hookSpecificOutput"]
            self.assertEqual(nested["hookEventName"], "PreToolUse")
            self.assertEqual(nested["permissionDecision"], decision["permissionDecision"])
            self.assertEqual(
                nested["permissionDecisionReason"], decision["permissionDecisionReason"]
            )
        return decision

    def denied(self, command, tool=None):
        payload = {"tool_input": {"command": command}}
        if tool is not None:
            payload["tool_name"] = tool
        decision = self.run_hook([sys.executable, str(GUARD)], payload)
        return decision.get("permissionDecision") == "deny"

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
                self.assertEqual(self.denied(command), denied)

    def test_agile_read_only_workflows(self):
        for command in (
            'ssh homeassistant "ha core logs"',
            'ssh homeassistant "ha supervisor info"',
            'ssh homeassistant "ha addons info example"',
            'ssh homeassistant "cat /config/configuration.yaml && uptime"',
            'ssh homeassistant "cat /config/configuration.yaml | head -n 5"',
            'ssh homeassistant "docker context ls"',
            'ssh homeassistant "docker buildx ls"',
            'ssh homeassistant "cat /config/configuration.yaml &>/dev/null"',
            # Silencing redirects may touch the next separator.
            "ssh -o BatchMode=yes homeassistant 'ls -ld /config/packages 2>&1; "
            "find /config/packages -maxdepth 1 -type f -name \"*.yaml\" "
            "! -name secrets.yaml -print 2>/dev/null'",
            'ssh homeassistant "cat /config/configuration.yaml 2>/dev/null|head -n 5"',
            'ssh homeassistant "ls /config 2>&1&&uptime"',
            'git status && ssh homeassistant "uptime" && git diff',
            # Local redirects write on this machine, not on Home Assistant.
            'ssh homeassistant "cat /config/configuration.yaml" > .temp/configuration.yaml',
            'ssh homeassistant "uptime" 2>&1',
            "ssh homeassistant 'cat $HOME/.profile'",
            "echo `ssh homeassistant uptime`",
            "x=\"$(ssh homeassistant 'uptime')\"; echo \"$x\"",
            # Mentioning an SSH command in an argument does not run it.
            "git commit -m \"fix(hooks): block ssh homeassistant 'touch' via PowerShell\"",
            "grep -rn ssh .claude/skills/homeassistant",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.denied(command))

    def test_writes_cannot_hide_behind_wrappers_or_read_binaries(self):
        for command in (
            'ssh.exe homeassistant "touch /tmp/example"',
            r'& "C:\Windows\System32\OpenSSH\ssh.exe" homeassistant "touch /tmp/example"',
            'echo ok && ssh homeassistant "touch /tmp/example"',
            'git status\nssh homeassistant "touch /tmp/example"',
            'env ssh homeassistant "touch /tmp/example"',
            'sudo -n ssh homeassistant "touch /tmp/example"',
            'ssh homeassistant "uptime"; ssh homeassistant "touch /tmp/example"',
            'ssh homeassistant "find /tmp/example -delete"',
            'ssh homeassistant "find /tmp -exec touch /tmp/example +"',
            'ssh homeassistant "sed --in-place=.bak s/a/b/ /tmp/example"',
            'ssh homeassistant "sed -n w/tmp/example /etc/hostname"',
            'ssh homeassistant "docker context rm example"',
            'ssh homeassistant "docker buildx create"',
            'ssh homeassistant "ha core restart"',
            'ssh homeassistant "journalctl --rotate"',
            'ssh homeassistant "ip link set eth0 down"',
            'ssh homeassistant "uptime && touch /tmp/example"',
            'ssh homeassistant "uptime || touch /tmp/example"',
            'ssh homeassistant "uptime; touch /tmp/example"',
            'ssh homeassistant "cat /etc/hostname |& touch /tmp/example"',
            'ssh homeassistant "cat /etc/hostname|&touch /tmp/example"',
            'echo ok |& ssh homeassistant "touch /tmp/example"',
            'ssh homeassistant "cat /etc/hostname >/tmp/example"',
            'ssh homeassistant "uptime 2>&1;touch /tmp/example"',
            'ssh homeassistant "uptime 2>/dev/null;cat /etc/hostname >/tmp/example"',
            'ssh homeassistant "uptime 2>&1&touch /tmp/example"',
            'ssh homeassistant "find /config -print 2>/dev/null; find /config -delete"',
            'ssh homeassistant "echo $(touch /tmp/example)"',
            'ssh homeassistant "parted /dev/example mklabel gpt"',
            'scp ./example homeassistant:/config/example',
        ):
            with self.subTest(command=command):
                self.assertTrue(self.denied(command))

    def test_posix_shell_tricks_are_denied(self):
        for command in (
            # ssh joins its arguments, so a quoted separator reaches the remote shell.
            "ssh homeassistant uptime ';' touch /tmp/example",
            'ssh \\\nhomeassistant "touch /tmp/example"',
            'ssh HOMEASSISTANT "touch /tmp/example"',
            'ssh ssh://root@homeassistant "touch /tmp/example"',
            'echo $(ssh homeassistant "touch /tmp/example")',
            'echo `ssh homeassistant "touch /tmp/example"`',
            "x=\"$(ssh homeassistant 'touch /tmp/example')\"",
            'diff <(ssh homeassistant "touch /tmp/example") /dev/null',
            "ssh homeassistant cat $(printf '; touch /tmp/example')",
            'ssh homeassistant "cat $HOME/example"',
            "bash -c \"ssh homeassistant 'touch /tmp/example'\"",
            'timeout 5 ssh homeassistant "touch /tmp/example"',
            "find . -exec ssh homeassistant 'touch /tmp/example' \\;",
            "echo /tmp/example | xargs ssh homeassistant",
            "if ssh homeassistant 'touch /tmp/example'; then echo ok; fi",
            'ssh homeassistant "uptime" # don\'t\nssh homeassistant "touch /tmp/example"',
            "$'\\x73sh' homeassistant \"touch /tmp/example\"",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.denied(command, tool="Bash"))

    def test_escaped_variables_reach_the_remote_shell(self):
        # Each shell has its own escape character for a literal `$`.
        self.assertFalse(self.denied('ssh homeassistant "cat \\$HOME/.profile"', tool="Bash"))
        self.assertFalse(
            self.denied('ssh homeassistant "cat `$HOME/.profile"', tool="PowerShell")
        )
        self.assertTrue(
            self.denied('ssh homeassistant "cat \\$HOME/.profile"', tool="PowerShell")
        )

    def test_powershell_writes_are_denied(self):
        for command in (
            r'C:\Windows\System32\OpenSSH\ssh.exe homeassistant "touch /tmp/example"',
            r".\ssh.exe homeassistant 'touch /tmp/example'",
            ". ssh homeassistant 'touch /tmp/example'",
            "s`sh homeassistant 'touch /tmp/example'",
            "ssh HomeAssistant 'touch /tmp/example'",
            "ssh `\n  homeassistant 'touch /tmp/example'",
            "$out = ssh homeassistant 'touch /tmp/example'",
            "Write-Output (ssh homeassistant 'touch /tmp/example')",
            "\"$(ssh homeassistant 'touch /tmp/example')\"",
            "& { ssh homeassistant 'touch /tmp/example' }",
            "Invoke-Expression \"ssh homeassistant 'touch /tmp/example'\"",
            "iex 'ssh homeassistant \"touch /tmp/example\"'",
            "pwsh -NoProfile -Command \"ssh homeassistant 'touch /tmp/example'\"",
            'cmd /c ssh homeassistant "touch /tmp/example"',
            "Start-Process ssh -ArgumentList 'homeassistant','touch /tmp/example' -Wait",
            "wsl ssh homeassistant 'touch /tmp/example'",
            'plink homeassistant "touch /tmp/example"',
            r"pscp .\example homeassistant:/config/example",
            "ssh homeassistant 'cat /config/example; touch /tmp/example'",
            "ssh homeassistant \u201ctouch /tmp/example\u201d",
            "ssh homeassistant cat $file",
            "$s = 'ssh'; & $s homeassistant 'uptime'",
            "ssh homeassistant 'uptime' <# note #>; ssh homeassistant 'touch /tmp/example'",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.denied(command, tool="PowerShell"))

    def test_powershell_reads_are_allowed(self):
        for command in (
            "ssh homeassistant 'cat /config/configuration.yaml' 2>$null",
            "ssh homeassistant 'ha core logs' | Select-String error",
            'ssh homeassistant "cat /config/configuration.yaml" > ha-data/configuration.yaml',
            "ssh homeassistant 'grep -c ''error'' /config/home-assistant.log'",
            "ssh homeassistant 'uptime'; git status",
            "Get-Content README.md | Select-String homeassistant",
            "git commit -m \"fix: ssh homeassistant 'touch' is blocked\"",
            "$env:GIT_TERMINAL_PROMPT = '0'; git fetch origin",
            r'& "C:\Program Files\Git\bin\git.exe" push origin HEAD:main',
        ):
            with self.subTest(command=command):
                self.assertFalse(self.denied(command, tool="PowerShell"))

    def test_shell_dialect_follows_the_tool_name(self):
        # Unquoted backslashes are path separators in PowerShell but escapes in bash.
        command = r'C:\Windows\System32\OpenSSH\ssh.exe homeassistant "touch /tmp/example"'
        payloads = (
            {"toolName": "powershell", "toolArgs": json.dumps({"command": command})},
            {"tool_name": "PowerShell", "tool_input": {"command": command}},
            # Copilot reports its PowerShell tool as `Bash` in PascalCase payloads,
            # and other clients may not name the tool at all.
            {"tool_input": {"command": command}},
            {"tool_name": "run_in_terminal", "tool_input": {"command": command}},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                decision = self.run_hook([sys.executable, str(GUARD)], payload)
                self.assertEqual(decision.get("permissionDecision"), "deny")

    def test_bad_payloads_report_explicit_denials(self):
        decision = self.run_hook(
            [sys.executable, str(GUARD)], {"toolArgs": "{invalid"}
        )
        self.assertEqual(decision.get("permissionDecision"), "deny")
        self.assertIn("invalid toolArgs JSON", decision["permissionDecisionReason"])
        result = subprocess.run(
            [sys.executable, str(GUARD)], input="{invalid", text=True,
            capture_output=True, cwd=ROOT, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["permissionDecision"], "deny")

    def test_non_utf8_locale_does_not_break_parsing(self):
        payload = json.dumps({"tool_input": {"command": "echo \u0150 \u2192 ok"}})
        result = subprocess.run(
            [sys.executable, str(GUARD)], input=payload.encode("utf-8"),
            capture_output=True, cwd=ROOT, timeout=10,
            env={**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_plugin_hook_matches_claude_code_shell_tools(self):
        group = json.loads(PLUGIN_HOOKS.read_text())["hooks"]["PreToolUse"][0]
        self.assertEqual(set(group["matcher"].split("|")), {"Bash", "PowerShell"})

    @unittest.skipUnless(shutil.which("python3"), "Claude Code launches python3")
    def test_claude_code_launcher_runs_in_bash_and_powershell(self):
        hook = json.loads(PLUGIN_HOOKS.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]
        env = {k: v for k, v in os.environ.items() if k not in {"PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"}}
        env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
        # Claude Code substitutes the placeholder before a POSIX shell runs the
        # command and rewrites it to `${env:...}` before PowerShell runs it.
        launchers = []
        if shutil.which("sh"):
            launchers.append(
                ["sh", "-c", hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))]
            )
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            launchers.append([
                powershell, "-NoProfile", "-NonInteractive", "-Command",
                hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", "${env:CLAUDE_PLUGIN_ROOT}"),
            ])
        self.assertTrue(launchers, "no shell available to run the launcher")
        for launcher in launchers:
            for command, denied in (
                ("git push origin HEAD:main", False),
                ('ssh homeassistant "touch /config/example"', True),
            ):
                with self.subTest(shell=launcher[0], command=command):
                    decision = self.run_hook(
                        launcher, {"tool_input": {"command": command}}, env=env
                    )
                    self.assertEqual(decision.get("permissionDecision") == "deny", denied)

    @unittest.skipIf(os.name == "nt", "Bash launcher regression")
    def test_copilot_plugin_bash_launcher(self):
        hook = json.loads(PLUGIN_HOOKS.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]
        env = {k: v for k, v in os.environ.items() if k not in {"PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"}}
        env["PLUGIN_ROOT"] = str(ROOT)
        decision = self.run_hook(
            ["bash", "-c", hook["bash"]],
            {"toolName": "bash", "toolArgs": json.dumps({"command": 'ssh homeassistant "touch /config/example"'})},
            env=env,
        )
        self.assertEqual(decision.get("permissionDecision"), "deny")

    @unittest.skipUnless(os.name == "nt", "Windows launcher regression")
    def test_repository_and_plugin_windows_launchers(self):
        repository = json.loads(REPOSITORY_HOOKS.read_text())["hooks"]["PreToolUse"][0]
        plugin = json.loads(PLUGIN_HOOKS.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]
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
