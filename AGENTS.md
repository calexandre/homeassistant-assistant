# AGENTS.md

Skills and a safety hook for building Home Assistant automations, scripts, and configurations with Claude Code, GitHub Copilot CLI, and VS Code with GitHub Copilot — not for HA core development. The same files ship as a plugin through `.claude-plugin/`.

## Landmines & Boundaries

✅ Always:

- Query live entities via the Home Assistant MCP server (`GetLiveContext`)
- Write runnable or scratch output to `.temp/` (gitignored)
- Run `fetch-ha-data.sh` (in `.github/skills/ha-config-fetch/`) to refresh local config snapshots and logs
- Bump `version` in `.claude-plugin/plugin.json` in any change that ships to plugin users — the version pins installed copies, so an unbumped change never reaches them

⚠️ Ask first:

- Changes to `.github/skills/homeassistant/SKILL.md` — this is the core Home Assistant definition (live-context gate and skill routing table)

🚫 Never:

- Assume entity IDs — always call `GetLiveContext` first
- Query automations, scenes, scripts, `configuration.yaml`, or logs via MCP — **these are not exposed by the MCP server**.
  Run `.github/skills/ha-config-fetch/fetch-ha-data.sh` instead, then read from `ha-data/`
- Modify or commit files inside gitignored directories (`ha-data/`, `.temp/`)
- Read or analyze gitignored files for context without being asked — they contain local-only data
- Bypass git hooks or use `--no-verify`

## Two Data Sources

| What you need | Where to get it |
|---|---|
| Live entity states, devices, areas | MCP server → `GetLiveContext` tool |
| Automations, scenes, scripts, configuration YAML | `.github/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/*.yaml` |
| Entity customizations (`customize.yaml`) | `.github/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/customize.yaml` |
| ESPHome device YAMLs | `.github/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/esphome/*.yaml` (`secrets.yaml` is never fetched) |
| Zigbee2MQTT config / devices / groups / state | `.github/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/zigbee2mqtt/{configuration,devices,groups}.yaml` + `state.json` |
| Home Assistant logs (for debugging) | `.github/skills/ha-config-fetch/fetch-ha-data.sh` → read `ha-data/logs/{core,supervisor}.log` |

The fetch script uses SSH (host alias: `homeassistant`, passwordless login assumed).

## Commands

```bash
# Refresh local HA config snapshots and logs (requires SSH)
.github/skills/ha-config-fetch/fetch-ha-data.sh

# Optional: override config directory (default: /config)
.github/skills/ha-config-fetch/fetch-ha-data.sh /custom/path

# Test the SSH read-only guard — run after any change under .github/hooks/
python3 -m unittest discover -s .github/hooks -p 'test_*.py'

# Validate the plugin and marketplace manifests
claude plugin validate .
```

## Code Style

Commit messages follow Conventional Commits:

```text
✅ feat(ha-release-notes): add file output instructions
✅ fix: Rename thought logging instructions file
✅ docs: Update tools and description in Home Assistant agent

❌ updated stuff
❌ WIP
```

Skills use YAML front matter with `name` and `description`.

## Documentation Standards

All documentation lives in the repo root or `.github/`.
ATX headers (`#`), relative links.
For every Markdown edit or generated report, including gitignored output, read and follow [the Markdown instructions](.github/instructions/markdown.instructions.md).

## File Output Conventions

- Implementation output (scratch YAML, test configs): write to `.temp/`
- `.temp/` is gitignored — never commit its contents
