# AGENTS.md

Skills and a safety hook for building Home Assistant automations, scripts, and configurations with Claude Code, GitHub Copilot CLI, and VS Code with GitHub Copilot — not for HA core development. The same files ship as a plugin through `.claude-plugin/`.

## Layout

| Path | Holds | Read by |
|---|---|---|
| `.claude/skills/` | Every skill | Claude Code, Copilot CLI, and VS Code in a clone; the plugin through `plugin.json` |
| `.github/hooks/ssh-ha-readonly-guard.py` | SSH read-only guard script and its tests | The two hook configs below, by path |
| `hooks/hooks.json` | Guard hook config, plugin format | Plugin installs (Claude Code, Copilot CLI) |
| `.github/hooks/ssh-ha-readonly-guard.json` | Guard hook config, Copilot format | VS Code and Copilot CLI in a clone |
| `.claude-plugin/` | Plugin and marketplace manifests, icon | Plugin installs |
| `.github/workflows/tests.yml` | CI running both test suites | GitHub Actions; `.github/dependabot.yml` keeps its actions current |

Claude Code in a plain clone loads the skills but not the guard; `claude --plugin-dir .` loads both.

## Landmines & Boundaries

✅ Always:

- Query live entities via the Home Assistant MCP server (`GetLiveContext`)
- Write local output to the folders listed under [File Output Conventions](#file-output-conventions), even though git ignores them
- Keep skills only in `.claude/skills/` — the one folder Claude Code, Copilot CLI, and VS Code all read, so each skill is listed once; VS Code lists a second copy in `.github/skills/` or `.agents/skills/` twice
- Run `fetch-ha-data.sh` (in `.claude/skills/ha-config-fetch/`) to refresh local config snapshots and logs
- Treat the `homeassistant` SSH host as read-only, whether or not the guard hook is loaded in this session
- Change the guard's launch command in both hook configs (`hooks/hooks.json` and `.github/hooks/ssh-ha-readonly-guard.json`)
- Add every new test suite to `.github/workflows/tests.yml`
- Bump `version` in `.claude-plugin/plugin.json` in any change that ships to plugin users — the version pins installed copies, so an unbumped change never reaches them

⚠️ Ask first:

- Changes to `.claude/skills/homeassistant/SKILL.md` — this is the core Home Assistant definition (live-context gate and skill routing table)
- Adding hooks to `.claude/settings.json` — VS Code's Copilot mode reads it alongside `.github/hooks/`, so the guard may run twice

🚫 Never:

- Assume entity IDs — always call `GetLiveContext` first
- Query automations, scenes, scripts, `configuration.yaml`, or logs via MCP — **these are not exposed by the MCP server**.
  Run `.claude/skills/ha-config-fetch/fetch-ha-data.sh` instead, then read from `ha-data/`
- Commit anything in `ha-data/`, `ha-release-notes/`, or `.temp/`
- Hand-edit files in `ha-data/` — `fetch-ha-data.sh` owns those snapshots
- Read local output (`ha-data/`, `ha-release-notes/`, `.temp/`) that the task or the running skill doesn't need — it holds personal data
- Bypass git hooks or use `--no-verify`

## Two Data Sources

| What you need | Where to get it |
|---|---|
| Live entity states, devices, areas | MCP server → `GetLiveContext` tool |
| Automations, scenes, scripts, configuration YAML | `.claude/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/*.yaml` |
| Entity customizations (`customize.yaml`) | `.claude/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/customize.yaml` |
| ESPHome device YAMLs | `.claude/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/esphome/*.yaml` (`secrets.yaml` is never fetched) |
| Zigbee2MQTT config / devices / groups / state | `.claude/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/zigbee2mqtt/{configuration,devices,groups}.yaml` + `state.json` |
| Home Assistant logs (for debugging) | `.claude/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/logs/{core,supervisor}.log` |

The fetch script uses SSH (host alias: `homeassistant`, passwordless login assumed).

## Commands

```bash
# Refresh local HA config snapshots and logs (requires SSH)
.claude/skills/ha-config-fetch/fetch-ha-data.sh

# Optional: override config directory (default: /config)
.claude/skills/ha-config-fetch/fetch-ha-data.sh /custom/path

# Test the SSH read-only guard — run after any change under .github/hooks/
python3 -m unittest discover -s .github/hooks -p 'test_*.py'

# Test that the fetch script keeps input out of the remote shell — run after any change to fetch-ha-data.sh
python3 -m unittest discover -s .claude/skills/ha-config-fetch -p 'test_*.py'

# Validate the plugin and marketplace manifests
claude plugin validate .
```

## Code Style

Commit messages follow Conventional Commits:

```text
✅ feat(ha-release-notes): add file output instructions
✅ fix(ha-config-fetch): keep script input out of the remote shell
✅ docs: use OAuth sign-in for every client

❌ updated stuff
❌ WIP
```

Skills use YAML front matter with `name` and `description`. Add `disable-model-invocation: true` to a skill that should run only when the user calls it, as `ha-release-notes` does.

## Documentation Standards

All documentation lives in the repo root or `.github/`.
ATX headers (`#`), relative links.
For every Markdown edit or generated report, including gitignored output, read and follow [the Markdown instructions](.github/instructions/markdown.instructions.md).

## File Output Conventions

- Implementation output (scratch YAML, test configs): write to `.temp/`
- Release summaries from the `ha-release-notes` skill: write to `ha-release-notes/ha-release-[VERSION].md`

Git ignores both folders on purpose: what goes there describes the user's home, so it stays on this machine. Write there (create the folder when it is missing) and leave it uncommitted; the gitignore is no reason to save the output anywhere else.
