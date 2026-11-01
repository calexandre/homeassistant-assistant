#!/usr/bin/env python3
"""SSH read-only guard for the `homeassistant` host.

`PreToolUse` hook for Claude Code (matcher: Bash|PowerShell) and the GitHub
Copilot hook harness (Copilot CLI, Copilot app, VS Code). Denies any
write/destructive SSH command targeting the `homeassistant` host; allows only
an explicit read allowlist. All other/local commands pass through untouched.

Design notes
------------
- Copilot `preToolUse` command hooks are **fail-closed** on non-zero exit, so
  this script MUST always exit 0 and express its decision via stdout JSON only.
- A denial is one JSON object that both clients read: Copilot reads the
  top-level `permissionDecision`; Claude Code ignores that field and reads
  `hookSpecificOutput` instead.
- Commands are tokenized as POSIX shell, PowerShell, or both. The tool name
  picks the dialect when it is unambiguous; Copilot reports its PowerShell
  tool as `Bash`, so on Windows both readings are checked and either denies.
- Separators, groups, command substitutions, call operators, wrappers such as
  `sudo`/`timeout`, and shell launchers such as `bash -c`, `pwsh -Command`,
  `cmd /c`, and `Invoke-Expression` are all inspected.
- Allowlist, deny-by-default: anything not explicitly allowed is denied.
- Interactive `ssh homeassistant` (no remote command) is denied.
- `scp`/`sftp`/`rsync` (and PuTTY's `pscp`/`psftp`) to `homeassistant` are
  denied (uploads = writes).
- This guards against mistakes; it is not a sandbox. Variables, aliases,
  functions, and encoded commands can still hide the host or the binary.
"""

from __future__ import annotations

import json
import os
import re
import sys

GUARDED_HOST = "homeassistant"
# Binaries whose arguments after the host form a remote command.
SSH_BINARIES = {"ssh", "plink"}
# File transfer binaries: any use against the guarded host is denied.
TRANSFER_BINARIES = {"scp", "sftp", "rsync", "pscp", "psftp"}
REMOTE_BINARIES = SSH_BINARIES | TRANSFER_BINARIES

POSIX = "posix"
POWERSHELL = "powershell"
BOTH_DIALECTS = (POSIX, POWERSHELL)

# Words that run the rest of their arguments as a command. The guard looks
# for an SSH binary anywhere in their arguments.
WRAPPERS = {
    "env", "sudo", "doas", "command", "builtin", "exec", "nohup", "time",
    "nice", "ionice", "timeout", "stdbuf", "setsid", "chrt", "taskset",
    "xargs", "find", "watch", "sshpass", "unbuffer", "caffeinate", "flock",
    "strace", "ltrace", "proxychains", "proxychains4", "torsocks", "tsocks",
    "nsenter", "chroot", "runas", "parallel", "script", "su", "runuser",
    "wsl", "cmd", "eval", "call", "invoke-command", "icm", "start-job",
    "start-threadjob",
}
# Launchers whose string arguments are themselves shell code, mapped to the
# dialects used to read that code.
SHELL_LAUNCHERS = {
    **dict.fromkeys(
        ("bash", "sh", "zsh", "dash", "ksh", "ash", "fish", "busybox", "eval",
         "su", "runuser", "script", "watch", "wsl"),
        (POSIX,),
    ),
    **dict.fromkeys(
        ("pwsh", "powershell", "iex", "invoke-expression", "invoke-command",
         "icm", "start-job", "start-threadjob"),
        (POWERSHELL,),
    ),
    "cmd": BOTH_DIALECTS,
}
# PowerShell cmdlets that start a process from a file name plus an argument
# list. Their arguments are not reconstructed, so SSH through them is denied.
START_PROCESS = {"start-process", "saps", "start"}
# Shell keywords and operators that precede the real command name.
PREFIX_WORDS = {
    "if", "then", "else", "elif", "do", "while", "until", "!", "{", "}",
    "coproc", ".",
}
MAX_NESTING = 4

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
    "dmidecode",
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
SAFE_REDIRECTS = re.compile(r"(?:&>/dev/null|2>&1|[12]?>/dev/null)(?=\s|$)")

# Chaining is validated command by command; writes and substitutions are denied.
DANGEROUS_TOKENS = re.compile(
    r"(?:[<>]|`|\$\(|\$\{|(?<!&)&(?!&))"
)

ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
URI_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")
UNPARSEABLE_REMOTE_CALL = re.compile(
    r"\b(?:ssh|plink|scp|sftp|rsync|pscp|psftp)(?:\.exe)?\b.*\b"
    + re.escape(GUARDED_HOST) + r"\b",
    re.I | re.S,
)
# A `$` followed by one of these starts a variable expansion in either dialect.
EXPANSION_START = re.compile(r"[A-Za-z0-9_{@*#?$!^]")
# Characters dropped before looking for the host name in free text.
HOST_NOISE = str.maketrans("", "", "\"'`\\^ \t\r\n")
# PowerShell also treats typographic quotes as quotes.
PS_SINGLE_QUOTES = "'‘’‚‛"
PS_DOUBLE_QUOTES = '"“”„'
# Markers left in a word whose value comes from a local command substitution or
# variable, so the remote check denies instead of trusting unknown text. The
# NUL prefix cannot come from a real command line.
SUBSTITUTION_MARKER = "\0$("
EXPANSION_MARKER = "\0${"
ANSI_C_ESCAPE = re.compile(
    r"\\(x[0-9A-Fa-f]{1,2}|u[0-9A-Fa-f]{1,4}|U[0-9A-Fa-f]{1,8}|[0-7]{1,3}|c.|.)",
    re.S,
)
ANSI_C_SIMPLE = {
    "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "n": "\n",
    "r": "\r", "t": "\t", "v": "\v",
}


class ParseError(ValueError):
    """Raised when shell text has unterminated quotes or substitutions."""


def emit_allow() -> None:
    """Allow the tool call (fall through to normal permission flow)."""
    # Empty stdout = default behavior. Explicit allow is also fine.
    sys.stdout.write("")
    sys.exit(0)


def emit_deny(reason: str) -> None:
    """Deny the tool call with a reason shown to the agent."""
    message = (
        f"SSH read-only guard: {reason}. Only read commands are allowed "
        f"on the {GUARDED_HOST!r} host."
    )
    payload = {
        # GitHub Copilot (CLI, app, VS Code)
        "permissionDecision": "deny",
        "permissionDecisionReason": message,
        # Claude Code
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
    }
    sys.stdout.write(json.dumps(payload))
    sys.exit(0)


def parse_payload() -> dict | None:
    """Read the PreToolUse payload from stdin. Returns None on failure."""
    # Decode explicitly: on Windows the default stdin encoding is the ANSI
    # code page, which cannot decode every UTF-8 byte sequence.
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        emit_deny(f"invalid hook JSON: {error.msg}")


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
        except json.JSONDecodeError as error:
            emit_deny(f"invalid toolArgs JSON: {error.msg}")
    # Flat fields
    if isinstance(payload.get("command"), str):
        return payload["command"]
    return None


def dialects_for(payload: dict) -> tuple[str, ...]:
    """Pick the shell dialects to read the command with.

    Claude Code names its tools `Bash` and `PowerShell`; Copilot's camelCase
    payloads name them `bash` and `powershell`. Copilot's PascalCase payloads
    report both as `Bash`, so `Bash` is only trusted off Windows.
    """
    name = payload.get("tool_name") or payload.get("toolName")
    if not isinstance(name, str):
        return BOTH_DIALECTS
    if name.lower() == "powershell":
        return (POWERSHELL,)
    if name == "bash" or (name == "Bash" and os.name != "nt"):
        return (POSIX,)
    return BOTH_DIALECTS


def decode_ansi_c(body: str) -> str:
    """Decode the body of a bash `$'...'` string."""

    def replace(match: re.Match[str]) -> str:
        escape = match.group(1)
        if escape[0] in "xuU" and len(escape) > 1:
            return chr(min(int(escape[1:], 16), sys.maxunicode))
        if escape[0] in "01234567":
            return chr(int(escape, 8) & 0xFF)
        if escape[0] == "c":
            return chr(ord(escape[1]) & 0x1F)
        return ANSI_C_SIMPLE.get(escape, escape)

    return ANSI_C_ESCAPE.sub(replace, body)


def split_commands(text: str, dialect: str) -> list[list[str]]:
    """Split shell text into simple commands, each a list of unquoted words.

    Every separator, group, and command substitution starts a new command, so
    nested invocations are inspected too. A word fed by a local substitution
    or variable keeps a `$(` or `${` marker. Redirection operators and their
    targets are dropped because they act on the local machine.
    """
    powershell = dialect == POWERSHELL
    escape = "`" if powershell else "\\"
    single_quotes = PS_SINGLE_QUOTES if powershell else "'"
    double_quotes = PS_DOUBLE_QUOTES if powershell else '"'
    separators = ";&|\n(){}" if powershell else ";&|\n()`"
    openers = "({" if powershell else "(`"

    commands: list[list[str]] = []
    words: list[str] = []
    word: list[str] = []
    started = False  # an empty quoted string still forms a word
    skip_target = False  # the next word is a redirection target
    in_double = False
    tick_open = False  # inside an unquoted POSIX `...` substitution
    # Substitutions opened inside "...": [kind, paren depth]. Closing one
    # returns to the double-quoted string.
    reopen: list[list] = []
    i, n = 0, len(text)

    def end_word() -> None:
        nonlocal word, started, skip_target
        if started:
            if skip_target:
                skip_target = False
            else:
                words.append("".join(word))
        word, started = [], False

    def end_command() -> None:
        nonlocal words, skip_target
        end_word()
        if words:
            commands.append(words)
        words, skip_target = [], False

    while i < n:
        char = text[i]
        following = text[i + 1] if i + 1 < n else ""

        if in_double:
            if char in double_quotes:
                if powershell and following and following in double_quotes:
                    word.append('"')
                    i += 2
                    continue
                in_double = False
                i += 1
                continue
            if char == escape:
                if not following:
                    raise ParseError("dangling escape")
                if following == "\n":
                    i += 2
                elif powershell or following in '$`"\\':
                    word.append(following)
                    i += 2
                else:
                    word.append(char)
                    i += 1
                continue
            if (char == "$" and following == "(") or (not powershell and char == "`"):
                word.append(SUBSTITUTION_MARKER)
                end_command()
                if char == "$":
                    reopen.append(["paren", 1])
                    i += 2
                else:
                    reopen.append(["tick", 0])
                    i += 1
                in_double = False
                continue
            if char == "$" and following and EXPANSION_START.match(following):
                word.append(EXPANSION_MARKER)
                i += 1
                continue
            word.append(char)
            i += 1
            continue

        if char in " \t\r":
            end_word()
            i += 1
            continue
        if char == escape:
            if following == "\n":
                i += 2  # line continuation
            elif following == "\r" and text[i + 2:i + 3] == "\n":
                i += 3
            elif following:
                word.append(following)
                started = True
                i += 2
            else:
                i += 1
            continue
        if char == "#" and not started:
            end = text.find("\n", i)
            i = n if end < 0 else end
            continue
        if powershell and char == "<" and following == "#":
            end_word()
            end = text.find("#>", i + 2)
            if end < 0:
                raise ParseError("unterminated block comment")
            i = end + 2
            continue
        if char in single_quotes:
            j = i + 1
            while True:
                if j >= n:
                    raise ParseError("unterminated quote")
                if text[j] in single_quotes:
                    if powershell and j + 1 < n and text[j + 1] in single_quotes:
                        word.append("'")
                        j += 2
                        continue
                    break
                word.append(text[j])
                j += 1
            started = True
            i = j + 1
            continue
        if not powershell and char == "$" and following == "'":
            j = i + 2
            while j < n and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise ParseError("unterminated quote")
            word.append(decode_ansi_c(text[i + 2:j]))
            started = True
            i = j + 1
            continue
        if char in double_quotes:
            in_double = True
            started = True
            i += 1
            continue
        if char in "<>":
            # A file descriptor prefix (`2>`, `*>`) was read into the word.
            if word and all(c.isdigit() or c == "*" for c in word):
                word, started = [], False
            else:
                end_word()
            j = i + 1
            while j < n and text[j] in "<>&|":
                j += 1
            k = j
            while k < n and text[k] in " \t":
                k += 1
            # `<(...)` and `>(...)` are process substitutions, not targets.
            skip_target = k < n and text[k] not in separators
            i = j
            continue
        if char in separators:
            closing = False
            if char == "`":
                if reopen and reopen[-1][0] == "tick":
                    closing = True
                elif tick_open:
                    closing, tick_open = True, False
                else:
                    tick_open = True
            if char in openers and not closing and (words or started):
                # The nested command's output becomes part of this command.
                word.append(SUBSTITUTION_MARKER)
                started = True
            end_command()
            if reopen:
                kind, depth = reopen[-1]
                if kind == "paren" and char == "(":
                    reopen[-1][1] = depth + 1
                elif kind == "paren" and char == ")":
                    reopen[-1][1] = depth - 1
                    if depth == 1:
                        reopen.pop()
                        in_double = started = True
                elif kind == "tick" and char == "`":
                    reopen.pop()
                    in_double = started = True
            i += 1
            continue
        if char == "$" and following == "(":
            i += 1  # the `(` is handled as a separator
            continue
        if char == "$" and following and EXPANSION_START.match(following):
            word.append(EXPANSION_MARKER)
            started = True
            i += 1
            continue
        word.append(char)
        started = True
        i += 1

    if in_double or reopen:
        raise ParseError("unterminated quote or substitution")
    end_command()
    return commands


def command_name(word: str) -> str:
    """Normalize a command word: basename, lower case, no Windows extension."""
    name = word.replace("\\", "/").rsplit("/", 1)[-1].lower()
    for extension in (".exe", ".com", ".cmd", ".bat", ".ps1"):
        if name.endswith(extension):
            return name[: -len(extension)]
    return name


def mentions_host(text: str) -> bool:
    """Cheap check: could this text name the guarded host?"""
    return GUARDED_HOST in text.lower().translate(HOST_NOISE)


def targets_guarded_host(token: str) -> bool:
    """True for `homeassistant`, `user@homeassistant`, `homeassistant:path`,
    `user@homeassistant:path`, and `ssh://user@homeassistant:22`.

    OpenSSH lower-cases host names before matching `Host` aliases, so the
    match ignores case.
    """
    target = token.lower()
    scheme = URI_SCHEME.match(target)
    if scheme:
        target = target[scheme.end():].split("/", 1)[0]
    target = target.rpartition("@")[2].split(":", 1)[0]
    return target == GUARDED_HOST


def find_host_token(tokens: list[str]) -> int | None:
    """Return the index of the `homeassistant` host token, or None."""
    for i, token in enumerate(tokens):
        if targets_guarded_host(token):
            return i
    return None


def inspect_text(text: str, dialects: tuple[str, ...], depth: int = 0) -> None:
    """Deny if any reading of `text` runs a write against the guarded host."""
    if depth > MAX_NESTING:
        emit_deny("command nesting is too deep to inspect")
    for dialect in dialects:
        try:
            commands = split_commands(text, dialect)
        except ParseError:
            # The shell would reject it too; deny only if it looks like SSH.
            if UNPARSEABLE_REMOTE_CALL.search(text):
                emit_deny("unparseable ssh command to guarded host")
            continue
        for words in commands:
            inspect_command(words, depth)


def inspect_command(words: list[str], depth: int) -> None:
    """Inspect one simple command (already split into unquoted words)."""
    start = 0
    while start < len(words) and (
        ASSIGNMENT.match(words[start]) or command_name(words[start]) in PREFIX_WORDS
    ):
        start += 1
    words = words[start:]
    if not words:
        return
    name = command_name(words[0])

    if name in REMOTE_BINARIES:
        host_idx = find_host_token(words[1:])
        if host_idx is None:
            return  # Not targeting the guarded host — not our problem.
        if name in TRANSFER_BINARIES:
            emit_deny(f"{name} to {GUARDED_HOST!r} is forbidden (file transfer = write)")
        guard_ssh(extract_remote_command(words[1:], host_idx))
        return

    arguments = words[1:]
    if name in START_PROCESS:
        if any(command_name(a) in REMOTE_BINARIES for a in arguments) and any(
            mentions_host(a) for a in arguments
        ):
            emit_deny(f"{words[0]} hides the remote command; call ssh directly")
        return

    dynamic = words[0].startswith(EXPANSION_MARKER)
    if name in WRAPPERS or name in SHELL_LAUNCHERS or dynamic:
        for k, argument in enumerate(arguments, start=1):
            if command_name(argument) in REMOTE_BINARIES:
                inspect_command(words[k:], depth)
                break
        else:
            if dynamic and find_host_token(arguments) is not None:
                shown = words[0].replace(EXPANSION_MARKER, "$")
                emit_deny(f"command name {shown!r} is a variable; call ssh directly")

    if name in SHELL_LAUNCHERS:
        candidates = [a for a in arguments if mentions_host(a)]
        joined = " ".join(arguments)
        if len(arguments) > 1 and mentions_host(joined):
            candidates.append(joined)
        for candidate in candidates:
            inspect_text(candidate, SHELL_LAUNCHERS[name], depth + 1)


def extract_remote_command(tokens: list[str], host_idx: int) -> str:
    """Return the remote command portion of an ssh invocation.

    Everything after the host token is the remote command, joined with spaces
    exactly as ssh does. ssh options before the host (-o, -i, -p, -L, -R, -N,
    -f, -v, etc.) are skipped implicitly because we start at host_idx + 1.
    """
    return " ".join(tokens[host_idx + 1:])


def check_segment_head(segment_tokens: list[str]) -> str | None:
    """Validate one pipeline segment's head binary. Returns None if OK, else reason."""
    # Normalize: strip leading ENV=val assignments and sudo, then basename the head
    # so `/usr/local/bin/docker` and `docker` are treated the same.
    idx = 0
    while idx < len(segment_tokens) and ASSIGNMENT.match(segment_tokens[idx]):
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
    head = segment_tokens[idx].rsplit("/", 1)[-1].replace("\0", "")

    # sed: allow only without -i/--in-place
    if head == "sed":
        if any(arg.startswith(("-i", "--in-place")) for arg in segment_tokens[idx + 1:]):
            return "sed with in-place edit is forbidden"
        return "sed scripts can write or execute; use head, tail, or grep instead"

    if head == "find":
        if any(arg in {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"} for arg in segment_tokens[idx + 1:]):
            return "find actions that write or execute commands are forbidden"
        return None

    # docker: allow only read subcommands
    if head == "docker":
        sub = next((a for a in segment_tokens[idx + 1:] if not a.startswith("-")), None)
        nested_reads = {
            "context": {"ls", "list", "inspect", "show"},
            "buildx": {"ls", "inspect", "version"},
            "manifest": {"inspect"},
        }
        if sub in nested_reads:
            args = segment_tokens[idx + 1:]
            position = args.index(sub)
            if position + 1 < len(args) and args[position + 1] in nested_reads[sub]:
                return None
            return f"docker {sub} only allows read subcommands"
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
        args = segment_tokens[idx + 1:]
        resources = {
            "core", "supervisor", "host", "hardware", "dns", "multicast",
            "observer", "store", "addons", "backups", "backup", "jobs", "os",
        }
        if len(args) >= 2 and args[0] in resources and args[1] in {"info", "logs", "stats", "list"}:
            return None
        if sub is None or sub not in HA_READ_SUBCMDS:
            return f"ha {sub!r} is forbidden (only read subcommands allowed)"
        return None

    # journalctl: always read
    if head == "journalctl":
        if any(arg.split("=")[0] in {"--rotate", "--vacuum-size", "--vacuum-time", "--vacuum-files", "--flush", "--relinquish-var", "--sync", "--setup-keys", "--update-catalog"} for arg in segment_tokens[idx + 1:]):
            return "journalctl maintenance operations are forbidden"
        return None

    if head == "ip":
        args = segment_tokens[idx + 1:]
        safe_flags = {"-j", "-json", "-s", "-statistics", "-d", "-details", "-4", "-6", "-br", "-brief"}
        words = [arg for arg in args if not arg.startswith("-")]
        if all(not arg.startswith("-") or arg in safe_flags for arg in args):
            if words and words[0] in {"address", "addr", "link", "route", "neigh", "neighbor", "rule", "netns"}:
                if len(words) == 1 or words[1] in {"show", "list", "ls"}:
                    return None
        return "ip only allows display operations"

    # awk/gawk: deny (can write via print >"/path" or system())
    if head in ("awk", "gawk", "mawk"):
        return "awk is forbidden (can write/exec via system())"

    # Generic read allowlist
    if head in READ_BINARIES:
        return None

    return f"{head!r} is not in the read allowlist"


def guard_ssh(remote_command: str) -> None:
    """Validate the remote command of an ssh call to the guarded host.

    The remote side is Home Assistant OS, so the command is always read as
    POSIX shell, whatever shell ran ssh locally.
    """
    # Empty remote command = interactive shell -> deny
    if not remote_command.strip():
        emit_deny(f"interactive ssh to {GUARDED_HOST!r} is forbidden (no remote command)")

    if "\0" in remote_command:
        emit_deny(
            "remote command uses a local variable or command substitution, "
            "which expands before ssh runs; put the remote command in single "
            "quotes"
        )

    # Strip only safe output-silencing redirects before looking for writes.
    stripped = SAFE_REDIRECTS.sub(" ", remote_command)

    # Any remaining write/chain/substitution token -> deny.
    dangerous = DANGEROUS_TOKENS.search(stripped)
    if dangerous:
        emit_deny(
            "remote command contains a write, chain, or substitution token "
            f"({dangerous.group()!r})"
        )

    # Validate each pipeline segment's head against the allowlist.
    try:
        segments = split_commands(stripped, POSIX)
    except ParseError:
        emit_deny("unparseable remote command")
    for segment in segments:
        reason = check_segment_head(segment)
        if reason is not None:
            emit_deny(reason)


def main() -> None:
    payload = parse_payload()
    if payload is None:
        # Can't parse — don't block unrelated tool calls.
        emit_allow()

    command = extract_command(payload)  # type: ignore[arg-type]
    if not command:
        emit_allow()

    inspect_text(command, dialects_for(payload))  # type: ignore[arg-type]
    emit_allow()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"ssh-ha-readonly-guard: unexpected error: {e}\n")
        emit_deny("unexpected inspection failure; review the hook error")
