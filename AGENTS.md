# AGENTS.md

GitHub Copilot workspace for building Home Assistant automations, scripts, and configurations — not for HA core development.

## Landmines & Boundaries

✅ Always:

- Query live entities via the `homeassistant-cazita` MCP server (`GetLiveContext`)
- Write runnable or scratch output to `.temp/` (gitignored)
- Run `fetch-ha-data.sh` to refresh local config snapshots and logs (after approval, see below)

⚠️ Ask first:

- Any SSH interaction with the Home Assistant server (including `fetch-ha-data.sh`)
- Changes to `.github/agents/homeassistant.agent.md` — this is the core agent definition
- Changes to `.vscode/mcp.json` — MCP connection config

🚫 Never:

- Assume entity IDs — always call `GetLiveContext` first
- Query automations, scenes, scripts, `configuration.yaml`, or logs via MCP — **these are not exposed by the MCP server**.
  Run `scripts/fetch-ha-data.sh` instead, then read from `ha-data/`
- Modify or commit files inside gitignored directories (`ha-data/`, `ha-release-notes/`, `.temp/`)
- Read or analyze gitignored files for context without being asked — they contain local-only data
- Reference files under `.github/instructions/.disabled/` — those are archived, not active
- Bypass git hooks or use `--no-verify`

## Two Data Sources

| What you need | Where to get it |
|---|---|
| Live entity states, devices, areas | MCP server → `GetLiveContext` tool |
| Automations, scenes, scripts, configuration YAML | `scripts/fetch-ha-data.sh` → read `ha-data/*.yaml` |
| Home Assistant logs (for debugging) | `scripts/fetch-ha-data.sh` → read `ha-data/logs/{core,supervisor}.log` |

The fetch script uses SSH (host alias: `homeassistant`, passwordless login assumed).
Always get human approval before running it.

## Commands

```bash
# Refresh local HA config snapshots and logs (requires SSH + human approval)
scripts/fetch-ha-data.sh

# Optional: override config directory (default: /config)
scripts/fetch-ha-data.sh /custom/path
```

No build, test, lint, or format commands — this is a documentation-and-config workspace.

## Code Style

Commit messages follow Conventional Commits:

```text
✅ feat(ha-release-notes): add file output instructions
✅ fix: Rename thought logging instructions file
✅ docs: Update tools and description in Home Assistant agent

❌ updated stuff
❌ WIP
```

Prompt and agent files use YAML front matter with `description`, `tools`, and optional `agent` fields.
See `.github/agents/homeassistant.agent.md` for the canonical agent pattern.

## Documentation Standards

All documentation lives in the repo root or `.github/`.
ATX headers (`#`), one sentence per line, relative links.
When adding docs under `docs/`, update any navigation config to keep structure in sync.

## File Output Conventions

- Implementation output (scratch YAML, test configs): write to `.temp/`
- Release note summaries: write to `ha-release-notes/ha-release-[VERSION].md`
- Both directories are gitignored — never commit their contents
