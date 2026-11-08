# Contributing

Thanks for helping make Home Assistant Assistant better.

## Where to start

- **Questions, setup help, and ideas** go to [Discussions](https://github.com/calexandre/homeassistant-assistant/discussions).
- **Bugs and concrete feature requests** go to [Issues](https://github.com/calexandre/homeassistant-assistant/issues). For a bug, include your client and its version, your Home Assistant version, and what you ran, with tokens and personal data removed.
- **Security problems** go through private reporting, never a public issue: see [SECURITY.md](SECURITY.md).

## Try your change locally

Fork and clone the repo, then load your working copy in the client you use:

- **Claude Code:** start it from the repo with the plugin loaded in place: `claude --plugin-dir .`
- **VS Code:** open the folder; skills and the hook load from the workspace.

Set up the Home Assistant MCP server as described in the [README](README.md#-set-up-the-home-assistant-mcp-server).

## Before you open a pull request

1. Run the tests for what you touched:

   ```bash
   # SSH read-only guard (.github/hooks/)
   python3 -m unittest discover -s .github/hooks -p 'test_*.py'

   # Fetch script (.claude/skills/ha-config-fetch/)
   python3 -m unittest discover -s tests/ha-config-fetch -p 'test_*.py'

   # Home map (.claude/skills/ha-home-map/), which needs PyYAML
   uv run --no-project --with pyyaml python3 -m unittest discover -s tests/ha-home-map -p 'test_*.py'
   ```

   The [Tests workflow](.github/workflows/tests.yml) runs every suite on every pull request.

   After a change in `.claude/skills/ha-home-map/` or `demo/`, also run `demo/build.sh` and commit the rebuilt `demo/assets/home-map.html`, which the skill ships already built: the workflow fails while the committed demo is stale. When the change alters how the map looks, retake `demo/assets/home-map.png` from it too.

2. Validate the plugin manifests:

   ```bash
   claude plugin validate .
   ```

3. Bump `version` in [.claude-plugin/plugin.json](.claude-plugin/plugin.json) when the change reaches plugin users (skills, hooks, scripts). Installed copies stay on their version until it changes.
4. Update the README when the change affects setup or behavior users see.
5. Write the commit subject in [Conventional Commits](https://www.conventionalcommits.org/) form, for example `feat(esphome): add LD2410 guidance` or `fix(hooks): allow ha core info`.

## Where things live

[AGENTS.md](AGENTS.md) holds the repo's working rules (and is what coding agents read), and the [README](README.md#-project-structure) maps the folders. A few conventions worth knowing up front:

- **Skills** live in `.claude/skills/<name>/SKILL.md` with `name` and `description` front matter, and their tests in `tests/<name>/`, so the skill folder holds only what the skill runs. A new skill also needs a row in the routing table of `.claude/skills/homeassistant/SKILL.md`; open an issue or discussion first, since that file routes every request.
- **The SSH guard** (`.github/hooks/ssh-ha-readonly-guard.py`) must always exit 0 and report decisions through stdout JSON, because Copilot treats a non-zero exit as a denial. Add a test case for every rule you change.
- **Demos** live in `demo/assets/`, the root of the [demo site](https://calexandre.github.io/homeassistant-assistant/): each one is a self-contained HTML file built from a made-up home, with a screenshot and a card in `demo/assets/index.html`. Pushes to `main` that touch the folder publish it.
- **Your Home Assistant data** stays out of commits: `ha-data/`, `ha-release-notes/`, and `.temp/` are gitignored.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
