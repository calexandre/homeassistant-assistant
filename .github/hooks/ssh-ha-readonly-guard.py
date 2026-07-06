#!/usr/bin/env python3
"""SSH read-only guard for the `homeassistant` host.

Copilot `PreToolUse` hook (matcher: Bash). Denies any write/destructive SSH
command targeting the `homeassistant` host; allows only an explicit read
allowlist. All other/local commands pass through untouched.

Design notes
------------
- `PreToolUse` command hooks are **fail-closed** on non-zero exit, so this
  script MUST always exit 0 and express its decision via stdout JSON only.
- The hook fires for every Bash tool call; we do the cheap check first and
  bail out (allow) the moment we see the command is not an ssh/scp/sftp/rsync
  call to `homeassistant`.
- Allowlist, deny-by-default: anything not explicitly allowed is denied.
- Interactive `ssh homeassistant` (no remote command) is denied.
- `scp`/`sftp`/`rsync` to `homeassistant` are denied (uploads = writes).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

GUARDED_HOST = "homeassistant"
SSH_BINARIES = {"ssh", "scp", "sftp", "rsync"}

# Read-only binaries allowed as the head of a pipeline segment on the remote.
# Anything not here -> deny.
READ_BINARIES = {
    "cat", "ls", "find", "head", "tail", "grep", "egrep", "fgrep", "rg",
    "zcat", "zgrep", "zless", "stat", "wc", "readlink", "realpath", "file",
    "cut", "sort", "uniq", "tr", "df", "du", "free", "uname", "hostname",
    "hostnamectl", "uptime", "date", "pwd", "whoami", "id", "printenv",
    "ps", "ip", "ss", "netstat", "dmesg", "nl", "tac", "column", "basename",
    "dirname", "test", "[", "echo", "printf", "nproc", "lscpu", "lsblk",
    "lspci", "lsusb", "vmstat", "iostat", "mpstat", "timedatectl",
    "localectl", "systemd-analyze", "loginctl", "lsns", "lsmod", "modinfo",
    "getent", "groups", "last", "lastlog", "w", "who", "lsof", "findmnt",
    "mount", "fdisk", "parted", "blockdev", "udevadm", "dmidecode",
    "sensors", "vcgencmd",
}

# docker subcommands that are read-only.
DOCKER_READ_SUBCMDS = {
    "logs", "ps", "inspect", "images", "version", "info", "top", "port",
    "stats", "events", "diff", "ls", "history", "search", "manifest",
    "wait", "name", "context", "buildx",
}

# systemctl subcommands that are read-only.
SYSTEMCTL_READ_SUBCMDS = {
    "status", "is-active", "is-enabled", "is-failed", "is-system-running",
    "show", "list-units", "list-unit-files", "list-sockets", "list-jobs",
    "list-dependencies", "list-machines", "cat", "help", "get-default",
}

# ha (Home Assistant Supervisor CLI) subcommands that are read-only.
HA_READ_SUBCMDS = {
    "core-info", "core-logs", "supervisor-info", "supervisor-logs",
    "host-info", "host-logs", "hardware-info", "hardware-audio",
    "dns-info", "dns-logs", "multicast-info", "multicast-logs",
    "observer-info", "observer-logs", "store-info", "store-logs",
    "addons", "addon-info", "addon-logs", "addon-stats",
    "backup-list", "backup-info", "jobs-info", "jobs-logs",
    "os-info", "os-logs", "panel-info", "panel-logs",
}

# Redirects we consider safe to strip (they only silence output, not write).
SAFE_REDIRECTS = re.compile(r"(?:2>&1|2>/dev/null|>/dev/null|&>/dev/null)")

# Anything that writes, chains, or substitutes -> deny.
DANGEROUS_TOKENS = re.compile(
    r"(?:>>?|`|\$\(|;|&&|\|\||&|\n|\r)"
)


def emit_allow() -> None:
    """Allow the tool call (fall through to normal permission flow)."""
    # Empty stdout = default behavior. Explicit allow is also fine.
    sys.stdout.write("")
    sys.exit(0)


def emit_deny(reason: str) -> None:
    """Deny the tool call with a reason shown to the agent."""
    payload = {
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"SSH read-only guard: {reason}. Only read commands are allowed "
            f"on the {GUARDED_HOST!r} host."
        ),
    }
    sys.stdout.write(json.dumps(payload))
    sys.exit(0)


def parse_payload() -> dict | None:
    """Read the PreToolUse payload from stdin. Returns None on failure."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except Exception:
        return None


def extract_command(payload: dict) -> str | None:
    """Pull the shell command out of either payload flavor."""
    if not isinstance(payload, dict):
        return None
    # VS Code compatible (snake_case)
    ti = payload.get("tool_input")
    if isinstance(ti, dict) and isinstance(ti.get("command"), str):
        return ti["command"]
    # camelCase
    ta = payload.get("toolArgs")
    if isinstance(ta, dict) and isinstance(ta.get("command"), str):
        return ta["command"]
    # Some payloads pass toolArgs as a JSON string
    if isinstance(ta, str):
        try:
            ta_obj = json.loads(ta)
            if isinstance(ta_obj, dict) and isinstance(ta_obj.get("command"), str):
                return ta_obj["command"]
        except Exception:
            pass
    # Flat fields
    if isinstance(payload.get("command"), str):
        return payload["command"]
    return None


def find_host_token(tokens: list[str]) -> int | None:
    """Return the index of the `homeassistant` host token, or None.

    Matches the host in any of these forms:
    - `homeassistant` (bare, ssh)
    - `user@homeassistant` (ssh)
    - `homeassistant:path` (scp/rsync)
    - `user@homeassistant:path` (scp/rsync)
    """
    for i, tok in enumerate(tokens):
        if tok == GUARDED_HOST:
            return i
        if tok.endswith(f"@{GUARDED_HOST}"):
            return i
        if tok.startswith(f"{GUARDED_HOST}:"):
            return i
        if re.match(rf"^[\w.-]+@{re.escape(GUARDED_HOST)}:", tok):
            return i
    return None


def is_guarded_ssh_call(command: str) -> tuple[str | None, list[str] | None, int | None]:
    """Decide if this is an ssh/scp/sftp/rsync call to the guarded host.

    Returns (binary, tokens, host_index) or (None, None, None) if not guarded.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unparseable (e.g. unbalanced quotes) — be conservative: if it looks
        # like it mentions the guarded host over ssh, deny; else allow.
        if re.search(r"\bssh\b.*\b" + re.escape(GUARDED_HOST) + r"\b", command):
            emit_deny("unparseable ssh command to guarded host")
        return (None, None, None)

    if not tokens:
        return (None, None, None)

    binary = os.path.basename(tokens[0])
    if binary not in SSH_BINARIES:
        return (None, None, None)

    host_idx = find_host_token(tokens)
    if host_idx is None:
        # Not targeting the guarded host — not our problem.
        return (None, None, None)

    return (binary, tokens, host_idx)


def guard_scp_sftp_rsync(binary: str) -> None:
    """scp/sftp/rsync to the guarded host are always denied (writes)."""
    emit_deny(f"{binary} to {GUARDED_HOST!r} is forbidden (file transfer = write)")


def extract_remote_command(tokens: list[str], host_idx: int) -> str:
    """Return the remote command portion of an ssh invocation.

    Everything after the host token is the remote command. ssh options before
    the host (-o, -i, -p, -L, -R, -N, -f, -v, etc.) are skipped implicitly
    because we start at host_idx + 1.
    """
    remote = tokens[host_idx + 1:]
    return " ".join(remote)


def check_segment_head(head: str, segment_tokens: list[str]) -> str | None:
    """Validate one pipeline segment's head binary. Returns None if OK, else reason."""
    # Normalize: strip leading ENV=val assignments and sudo, then basename the head
    # so `/usr/local/bin/docker` and `docker` are treated the same.
    idx = 0
    while idx < len(segment_tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", segment_tokens[idx]):
        idx += 1
    if idx < len(segment_tokens) and segment_tokens[idx] == "sudo":
        idx += 1
        # sudo can take flags like -n / -u user; skip them
        while idx < len(segment_tokens) and segment_tokens[idx].startswith("-"):
            flag = segment_tokens[idx]
            idx += 1
            if flag in ("-u", "-g", "-C", "-D", "-r", "-R", "-T"):
                idx += 1  # skip the argument to these flags
    if idx >= len(segment_tokens):
        return "empty command after sudo/env"
    head = os.path.basename(segment_tokens[idx])

    # sed: allow only without -i/--in-place
    if head == "sed":
        if any(arg in ("-i", "--in-place") or arg.startswith("-i") for arg in segment_tokens[idx + 1:]):
            return "sed with in-place edit is forbidden"
        return None

    # docker: allow only read subcommands
    if head == "docker":
        sub = next((a for a in segment_tokens[idx + 1:] if not a.startswith("-")), None)
        if sub is None or sub not in DOCKER_READ_SUBCMDS:
            return f"docker {sub!r} is forbidden (only read subcommands allowed)"
        return None

    # systemctl: allow only read subcommands
    if head == "systemctl":
        sub = next((a for a in segment_tokens[idx + 1:] if not a.startswith("-")), None)
        if sub is None or sub not in SYSTEMCTL_READ_SUBCMDS:
            return f"systemctl {sub!r} is forbidden (only read subcommands allowed)"
        return None

    # ha (Supervisor CLI): allow only read subcommands
    if head == "ha":
        sub = next((a for a in segment_tokens[idx + 1:] if not a.startswith("-")), None)
        if sub is None or sub not in HA_READ_SUBCMDS:
            return f"ha {sub!r} is forbidden (only read subcommands allowed)"
        return None

    # journalctl: always read
    if head == "journalctl":
        return None

    # awk/gawk: deny (can write via print >"/path" or system())
    if head in ("awk", "gawk", "mawk"):
        return "awk is forbidden (can write/exec via system())"

    # Generic read allowlist
    if head in READ_BINARIES:
        return None

    return f"{head!r} is not in the read allowlist"


def guard_ssh(remote_command: str) -> None:
    """Validate the remote command of an ssh call to the guarded host."""
    # Empty remote command = interactive shell -> deny
    if not remote_command.strip():
        emit_deny(f"interactive ssh to {GUARDED_HOST!r} is forbidden (no remote command)")

    # Strip only safe output-silencing redirects before looking for writes.
    stripped = SAFE_REDIRECTS.sub(" ", remote_command)

    # Any remaining write/chain/substitution token -> deny.
    if DANGEROUS_TOKENS.search(stripped):
        emit_deny(
            "remote command contains a write, chain, or substitution token "
            f"({DANGEROUS_TOKENS.search(stripped).group()!r})"
        )

    # Validate each pipeline segment's head against the allowlist.
    for segment in stripped.split("|"):
        seg = segment.strip()
        if not seg:
            continue
        try:
            seg_tokens = shlex.split(seg, posix=True)
        except ValueError:
            emit_deny(f"unparseable pipeline segment {seg!r}")
        if not seg_tokens:
            continue
        reason = check_segment_head(seg_tokens[0], seg_tokens)
        if reason is not None:
            emit_deny(reason)

    # All segments passed.
    emit_allow()


def main() -> None:
    payload = parse_payload()
    if payload is None:
        # Can't parse — don't block unrelated tool calls.
        emit_allow()

    command = extract_command(payload)  # type: ignore[arg-type]
    if not command:
        emit_allow()

    binary, tokens, host_idx = is_guarded_ssh_call(command)  # type: ignore[arg-type]
    if binary is None:
        # Not an ssh/scp/sftp/rsync call to the guarded host.
        emit_allow()

    if binary in ("scp", "sftp", "rsync"):
        guard_scp_sftp_rsync(binary)
        return  # unreachable

    # ssh
    assert tokens is not None and host_idx is not None
    remote_command = extract_remote_command(tokens, host_idx)
    guard_ssh(remote_command)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Never crash the hook with a non-zero exit (fail-closed would deny
        # unrelated commands). On unexpected error, allow and let the normal
        # permission flow decide.
        sys.stderr.write(f"ssh-ha-readonly-guard: unexpected error: {e}\n")
        emit_allow()
