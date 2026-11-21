# AGENTS.md

Skills and a safety hook for working on an existing Home Assistant installation with Claude Code, GitHub Copilot CLI, and VS Code with GitHub Copilot — not for HA core development. They complement two projects: [ha-mcp](https://github.com/homeassistant-ai/ha-mcp), whose tools read and change the home, and the [`home-assistant-best-practices`](https://github.com/homeassistant-ai/skills) skill, which governs how automations, scripts, scenes, helpers, and dashboards get written. This repo adds what they leave out: ESPHome authoring, troubleshooting, read-only SSH snapshots of config files, the home map, personalized release notes, and the SSH guard. The same files ship as a plugin through `.claude-plugin/`.

## Layout

| Path | Holds | Read by |
|---|---|---|
| `.claude/skills/` | Every skill | Claude Code, Copilot CLI, and VS Code in a clone; the plugin through `plugin.json` |
| `.github/hooks/ssh-ha-readonly-guard.py` | SSH read-only guard script and its tests | The two hook configs below, by path |
| `hooks/hooks.json` | Guard hook config, plugin format | Plugin installs (Claude Code, Copilot CLI) |
| `.github/hooks/ssh-ha-readonly-guard.json` | Guard hook config, Copilot format | VS Code and Copilot CLI in a clone |
| `.claude-plugin/` | Plugin and marketplace manifests, icon | Plugin installs |
| `.github/workflows/tests.yml` | CI running every test suite | GitHub Actions; `.github/dependabot.yml` keeps its actions current |
| `tests/<skill>/` | Test suites for the skills | Contributors and CI |
| `demo/` | `demo_home.py` (made-up homes), `release-notes.json` (a made-up home's judged release notes report, trimmed by `trim_release_report.py`), and `build.sh`, which renders both into `assets/` | The README; the `ha-home-map` skill, which hands the built home map to users without SSH snapshots; the tests |
| `demo/assets/` | GitHub Pages root: the showcase `index.html` with a card per demo and install steps that mirror the README's, each demo as one self-contained HTML file, and its screenshot | `.github/workflows/pages.yml`, which publishes it on pushes to `main` and stamps the plugin version into its `__PLUGIN_VERSION__` placeholders |

Claude Code in a plain clone loads the skills but not the guard; `claude --plugin-dir .` loads both.

## Landmines & Boundaries

✅ Always:

- Take entity IDs from a live lookup: `ha_search` or `ha_get_state` see every entity, `GetLiveContext` only the ones exposed to Assist
- Read the `home-assistant-best-practices` skill before writing an automation, script, scene, helper, or dashboard — installed, or through `ha_get_skill_guide`
- Write local output to the folders listed under [File Output Conventions](#file-output-conventions), even though git ignores them
- Keep skills only in `.claude/skills/` — the one folder Claude Code, Copilot CLI, and VS Code all read, so each skill is listed once; VS Code lists a second copy in `.github/skills/` or `.agents/skills/` twice
- Run `fetch-ha-data.sh` (in `.claude/skills/ha-config-fetch/`) to refresh local config snapshots
- Treat the `homeassistant` SSH host as read-only, whether or not the guard hook is loaded in this session
- Change the guard's launch command in both hook configs (`hooks/hooks.json` and `.github/hooks/ssh-ha-readonly-guard.json`)
- Put a skill's tests in `tests/<skill>/`, outside the skill folder, so plugin users get only what the skill runs; add every new test suite to `.github/workflows/tests.yml`
- Rebuild the demos with `demo/build.sh` after any change in `.claude/skills/ha-home-map/`, `.claude/skills/ha-release-notes/`, or `demo/`, and commit the pages it changes in `demo/assets/` — the home map skill ships its demo already built, and CI fails while a committed page is stale
- Bump `version` in `.claude-plugin/plugin.json` in any change that ships to plugin users — the version pins installed copies, so an unbumped change never reaches them

⚠️ Ask first:

- Adding hooks to `.claude/settings.json` — VS Code's Copilot mode reads it alongside `.github/hooks/`, so the guard may run twice
- Calling an MCP tool that changes Home Assistant or a device, directly or through `ha_call_tool`. In ha-mcp that is every tool except the readers: `ha_get_*`, `ha_search`, `ha_search_tools`, `ha_list_*`, `ha_config_get_*`, `ha_config_list_*`, and the `list`, `get`, and `details` actions of the `ha_manage_*` tools. In the MCP Server's own sets it is `homeassistant__call_action`, `config__reload_config_entry`, and the ESPHome Device Builder's `update_config`, `add_component`, `upsert_automation`, `delete_automation`, `create_device`, `set_secret`, `compile`, and `install` — a flash has no undo

🚫 Never:

- Pass `secrets.yaml` to the ESPHome Device Builder's `get_config` — its values would enter the conversation; pass only filenames from `list_devices`
- Commit anything in `ha-data/`, `ha-release-notes/`, or `.temp/`
- Hand-edit files in `ha-data/` — `fetch-ha-data.sh` owns those snapshots
- Read local output (`ha-data/`, `ha-release-notes/`, `.temp/`) that the task or the running skill doesn't need — it holds personal data
- Bypass git hooks or use `--no-verify`

## Data Sources

| What you need | Where to get it |
|---|---|
| Entities, states, devices, areas, floors, and labels | ha-mcp → `ha_search`, `ha_get_state`, `ha_get_device`, `ha_get_entity`, `ha_list_floors_areas` |
| Automations, scripts, scenes, helpers, dashboards, and blueprints | ha-mcp → `ha_config_get_automation`, `ha_config_get_script`, `ha_config_get_scene`, `ha_config_list_helpers`, `ha_config_get_dashboard`, `ha_manage_blueprints` (`list`, `get`) |
| Logs and automation traces | ha-mcp → `ha_get_logs`, `ha_get_automation_traces`; the Home Assistant set's `hassio__get_logs` merges Core, Supervisor, and app logs for a time window |
| History and long-term statistics | ha-mcp → `ha_get_history`, or the Home Assistant set's `history__get_history` |
| Integration status and diagnostics | ha-mcp → `ha_get_integration` |
| ESPHome device YAMLs | ESPHome Device Builder set → `list_devices`, `get_config`, `validate_config`; without it, `fetch-ha-data.sh` → read `ha-data/esphome/*.yaml` (`secrets.yaml` is never fetched) |
| `configuration.yaml`, the files it includes (packages, automation and script folders), and `customize.yaml` | `fetch-ha-data.sh` → read them under `ha-data/` at their path on the host; no MCP tool reads config files |
| Zigbee2MQTT config, devices, groups, and state | `fetch-ha-data.sh` → read `ha-data/zigbee2mqtt/{configuration,devices,groups}.yaml` + `state.json` |
| Registries and YAML as files, for `ha-home-map` and `ha-release-notes` | `fetch-ha-data.sh` → `ha-data/registry/*.json`, trimmed by `trim_registry.py` so no credentials reach the disk, and `ha-data/*.yaml` |

ha-mcp lists its most-used tools directly; find the rest with `ha_search_tools` and run them through `ha_call_tool`. Rows that name the **Home Assistant** or **ESPHome Device Builder** set apply only when the client has those tools; the README's [Optional: extra tool sets](README.md#optional-extra-tool-sets) lists what Home Assistant needs to expose them. The fetch script uses SSH (host alias: `homeassistant`, passwordless login assumed).

## Commands

```bash
# Refresh local HA config snapshots (requires SSH)
.claude/skills/ha-config-fetch/fetch-ha-data.sh

# Optional: override config directory (default: /config)
.claude/skills/ha-config-fetch/fetch-ha-data.sh /custom/path

# Test the SSH read-only guard — run after any change under .github/hooks/
python3 -m unittest discover -s .github/hooks -p 'test_*.py'

# Test that the fetch script keeps input out of the remote shell and credentials off the disk — run after any change in ha-config-fetch/
python3 -m unittest discover -s tests/ha-config-fetch -p 'test_*.py'

# Test the home map builder and page against made-up homes (needs PyYAML) — run after any change in ha-home-map/
uv run --no-project --with pyyaml python3 -m unittest discover -s tests/ha-home-map -p 'test_*.py'

# Test the release notes parser, matcher, and report against made-up posts (the snapshot test needs PyYAML) — run after any change in ha-release-notes/
uv run --no-project --with pyyaml python3 -m unittest discover -s tests/ha-release-notes -p 'test_*.py'

# Rebuild the demo pages in demo/assets/ — run after any change in ha-home-map/, ha-release-notes/, or demo/
demo/build.sh

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
- Home maps from the `ha-home-map` skill: write to `.temp/home-map/`
- Release notes from the `ha-release-notes` skill: `ha-release-notes/ha-release-[VERSION].json`, `.html`, and `.md`, with the agent's to-do in `.temp/release-notes/`

Git ignores both folders on purpose: what goes there describes the user's home, so it stays on this machine. Write there (create the folder when it is missing) and leave it uncommitted; the gitignore is no reason to save the output anywhere else.
