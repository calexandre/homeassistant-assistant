# 🏠 Home Assistant Assistant

<p align="center">
  <img src="images/haassistant-logo.png" alt="Pixel-art robot next to the Home Assistant house logo, wired to lights, sensors, and locks" width="50%" />
</p>

<p align="center">
  <a href="https://github.com/calexandre/homeassistant-assistant/actions/workflows/tests.yml"><img src="https://github.com/calexandre/homeassistant-assistant/actions/workflows/tests.yml/badge.svg" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/calexandre/homeassistant-assistant" alt="License: MIT" /></a>
  <a href=".claude-plugin/plugin.json"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcalexandre%2Fhomeassistant-assistant%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=plugin" alt="Plugin version" /></a>
  <a href="https://www.home-assistant.io/integrations/mcp_server/"><img src="https://img.shields.io/badge/Home%20Assistant-2026.11%2B-18BCF2?logo=homeassistant&logoColor=white" alt="Home Assistant 2026.11 or later" /></a>
</p>

> Your Home Assistant setup, understood by AI — grounded in your **live entities** and the **official docs**, not guesses.

Skills and a safety hook for **Claude Code**, **GitHub Copilot CLI**, and **VS Code with GitHub Copilot** that help you build automations, scripts, scenes, and ESPHome configs for your existing Home Assistant installation. It is not for Home Assistant core development.

Before answering, the agent checks what you actually have (via MCP) and how Home Assistant says to do it (via the official docs). That combination keeps it from inventing entity IDs or suggesting deprecated YAML.

## 📚 Contents

- [✨ Features](#-features)
- [🧭 How it works](#-how-it-works)
- [🧰 Prerequisites](#-prerequisites)
- [🔗 Set up the Home Assistant MCP server](#-set-up-the-home-assistant-mcp-server)
- [📦 Installation](#-installation)
- [✅ Check that it works](#-check-that-it-works)
- [📂 Optional: SSH snapshots](#-optional-ssh-snapshots)
- [💡 Usage examples](#-usage-examples)
- [🏡 Home map](#-home-map)
- [🔒 Safety and privacy](#-safety-and-privacy)
- [🧱 Project structure](#-project-structure)
- [🧯 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## ✨ Features

- 🔌 **Live entity context** — pulls your real devices, entities, and areas via `GetLiveContext` before suggesting anything.
- 📚 **Docs-grounded answers** — looks up the official Home Assistant and ESPHome docs and cites the exact section used.
- 🩺 **Troubleshooting playbook** — a guided flow through config checks, logs, traces, and Developer Tools when something misbehaves.
- 🔧 **ESPHome support** — device YAML authoring backed by an esphome.io sitemap.
- 📰 **Personalized release notes** — `/ha-release-notes` checks a Home Assistant release against your devices and configs and flags the breaking changes that affect you.
- 🏡 **Home map** — `/ha-home-map` draws an interactive map of your areas, devices, and the automations, scripts, and scenes that link them, as one HTML file that works offline. [See the demo](#-home-map).
- 📂 **Config snapshots** — optional read-only SSH snapshots of automations, scripts, scenes, ESPHome YAMLs, Zigbee2MQTT data, and logs.
- 🔐 **Read-only SSH guard** — a hook that blocks destructive SSH commands against your Home Assistant host, whether they run in Bash or PowerShell.
- 🧩 **Cross-tool plugin** — the same skills and hook work in Claude Code, GitHub Copilot CLI, and VS Code.

## 🧭 How it works

```mermaid
flowchart LR
  user([You]) --> agent["Your AI agent + skills<br/>Claude Code · Copilot CLI · VS Code"]
  agent -->|"MCP · GetLiveContext"| ha[("Home Assistant")]
  agent -->|"looks up"| docs["Official docs<br/>home-assistant.io · esphome.io"]
  agent -->|"reads"| snap["ha-data/ snapshots"]
  ha -->|"SSH, read-only · optional"| snap
  guard{{"SSH read-only guard"}} -.->|"checks every shell command"| agent
```

Every request starts at the `homeassistant` skill, which calls `GetLiveContext` and then routes to the skill that fits:

| Skill | What it does |
|---|---|
| `homeassistant` | Entry point: grounds the request in live entities and picks the skills below |
| `ha-implementation-format` | Answers automation, script, scene, and blueprint requests as YAML, an explanation, and customization ideas |
| `ha-troubleshooting` | Walks config validation, logs, traces, Developer Tools, and debug logging |
| `ha-state-presentation` | Summarizes live states grouped by area or function |
| `ha-config-fetch` | Refreshes `ha-data/` snapshots over SSH when they are older than 24 hours, and always before debugging |
| `ha-docs-sitemap` | Maps a topic to the right home-assistant.io page instead of crawling the docs |
| `ha-release-notes` | On demand only (`/ha-release-notes`): summarizes a release against your setup and flags breaking changes that affect you |
| `ha-home-map` | On demand only (`/ha-home-map`): draws your areas, devices, automations, scripts, and scenes as an offline, interactive map |
| `esphome` | Authors ESPHome device YAML with an esphome.io sitemap |

## 🧰 Prerequisites

| You need | For |
|---|---|
| Home Assistant 2026.11 or later with the [Model Context Protocol Server](https://www.home-assistant.io/integrations/mcp_server/) integration (the first release with the complete OAuth support browser sign-in relies on: Client ID Metadata Documents, PKCE, and discovery for public clients) | Everything |
| One client: [Claude Code](https://claude.com/product/claude-code), [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-plugins), or VS Code with GitHub Copilot | Everything |
| Python 3 | The SSH read-only guard hook, which every client runs |
| SSH access to the Home Assistant host through a passwordless host alias named exactly `homeassistant` in `~/.ssh/config` | Optional: [snapshots](#-optional-ssh-snapshots) of automations, scripts, scenes, config files, and logs, and the home map |
| [PyYAML](https://pypi.org/project/PyYAML/) or [uv](https://docs.astral.sh/uv/) | Optional: the home map |

Claude Code runs the hook as `python3` on every platform, including Windows. The Copilot clients run it as `python3` on Linux/macOS and as `python` on Windows.

## 🔗 Set up the Home Assistant MCP server

1. In Home Assistant, go to **Settings → Devices & services → Add Integration**, search for **Model Context Protocol Server**, and finish the setup flow.
2. Go to **Settings → Voice assistants → Expose** and expose the entities you want the agent to see. The default **Device control** tools only see exposed entities, so anything you leave out is invisible to the agent.
3. Note your MCP URL: your Home Assistant URL followed by `/api/mcp`, for example `https://example.ui.nabu.casa/api/mcp`.

All three clients sign in through Home Assistant's own login page in your browser (OAuth), so there is no token to create or copy. Use an HTTPS URL that matches the **Internal URL** or **External URL** configured in Home Assistant (Home Assistant Cloud, a reverse proxy, or Home Assistant's own TLS): the Home Assistant docs note that Claude Code only connects to MCP servers over HTTPS.

The integration's options control which tools it exposes and whether it requires an administrator account (on by default). See the [integration docs](https://www.home-assistant.io/integrations/mcp_server/) for the details.

## 📦 Installation

Pick your client. All three load the same skills and hook.

### 🤖 Claude Code

```bash
claude plugin marketplace add calexandre/homeassistant-assistant
claude plugin install homeassistant-assistant@homeassistant
claude mcp add --scope user --transport http homeassistant https://YOUR-HOME-ASSISTANT/api/mcp
claude mcp login homeassistant
```

`claude mcp login` opens your browser to sign in to Home Assistant.

### 🐙 GitHub Copilot CLI

```bash
copilot plugin marketplace add calexandre/homeassistant-assistant
copilot plugin install homeassistant-assistant@homeassistant
copilot mcp add --transport http homeassistant https://YOUR-HOME-ASSISTANT/api/mcp
```

Copilot CLI signs in to Home Assistant through your browser, like Claude Code.

### 🖥️ VS Code

```bash
git clone https://github.com/calexandre/homeassistant-assistant.git
code homeassistant-assistant
```

Skills load automatically from [.claude/skills/](.claude/skills/) and the SSH guard hook from [.github/hooks/](.github/hooks/). Run **MCP: Add Server**, choose **HTTP**, enter `https://YOUR-HOME-ASSISTANT/api/mcp`, use the ID `homeassistant`, and sign in to Home Assistant when VS Code opens your browser.

## ✅ Check that it works

Ask a question only your house can answer:

```text
> Which lights are on right now?
```

The answer should name your real entities. If the agent says it cannot reach Home Assistant, list your MCP servers with `claude mcp list`, `copilot mcp list`, or the **MCP: List Servers** command in VS Code, then see [Troubleshooting](#-troubleshooting).

## 📂 Optional: SSH snapshots

The MCP server exposes live entity state, but not your automation, script, or scene definitions, config files, or logs. With SSH access, the agent pulls read-only snapshots of those into `ha-data/` in your working directory (gitignored in this repo).

> [!IMPORTANT]
> SSH access requires a host alias named exactly `homeassistant` in `~/.ssh/config`. The fetch script connects to that name, and the read-only guard only protects commands that target it: under any other alias, snapshots fail and the guard can't block writes to your host.

| Snapshot | Path on the host | Needs |
|---|---|---|
| `automations`, `scenes`, `scripts`, `configuration`, `customize` YAML | `/config` | Any SSH add-on |
| Every file `configuration.yaml` includes, such as packages and automation folders (`secrets.yaml` is always skipped) | `/config` | Any SSH add-on |
| Area, device, entity, and integration registries, trimmed as they download: no credentials, integration titles, MAC addresses, or serial numbers | `/config/.storage` | Any SSH add-on |
| ESPHome device YAMLs (`secrets.yaml` is always skipped) | `/config/esphome` | Any SSH add-on |
| Zigbee2MQTT `configuration`, `devices`, `groups`, `state.json` | `/share/zigbee2mqtt` | Root, or a user with `sudo` |
| Core and Supervisor logs, last 12 hours | Docker container logs | **Advanced SSH & Web Terminal** add-on with **Protection mode** off |

1. Install an SSH add-on in Home Assistant and add your public key to it. The official **Terminal & SSH** add-on covers config files and ESPHome YAMLs; the community **Advanced SSH & Web Terminal** add-on with protection mode off covers everything.
2. Add the `homeassistant` host alias to `~/.ssh/config`, with `HostName`, `User`, and `Port` set to your Home Assistant host and what your add-on uses:

   ```text
   Host homeassistant
     HostName homeassistant.local
     User root
     Port 22
     IdentityFile ~/.ssh/id_ed25519
   ```

3. Check that it logs in without a password prompt:

   ```bash
   ssh homeassistant ls /config
   ```

4. Ask the agent to "refresh my Home Assistant data", or run the script yourself from a clone of this repo:

   ```bash
   .claude/skills/ha-config-fetch/fetch-ha-data.sh
   ```

The script reads `/config` by default. If your add-on mounts the config elsewhere, pass the path: `.claude/skills/ha-config-fetch/fetch-ha-data.sh /homeassistant`.

## 💡 Usage examples

Just ask, in any client: the `homeassistant` skill picks up any Home Assistant request. In VS Code, use Chat in Agent mode.

### 🤖 Creating automations

```text
> Create an automation that turns on the living room lights at sunset,
  but only if someone is home.

> Turn my kitchen ceiling switch into a scene that also dims the hall lights.
```

Answers come as ready-to-paste YAML, a short "How This Works" with links to the docs used, and customization ideas.

### 🩺 Debugging

```text
> My motion sensor automation isn't triggering — help me debug it.

> Why does this template return unknown? {{ states('sensor.temperature') | float }}
```

The troubleshooting skill walks through config checks, automation traces, and logs before proposing a fix.

### 📊 Checking your home

```text
> Which battery sensors are below 20%?

> Are any of my automations using deprecated syntax?
```

### 🔧 ESPHome devices

```text
> Add a BME280 sensor to the hall corridor wall switch over I2C.
```

### 📰 Release notes

```text
/ha-release-notes
/ha-release-notes 2026.11.0
```

Runs only when you call it (in Claude Code, as `/ha-release-notes`). Pass a version like `2026.11.0` (patch versions work too) or a release notes URL; with neither, it uses the latest release on the Home Assistant blog. It checks highlights, new integrations, and breaking changes against your live entities and config snapshots, and saves the summary to `ha-release-notes/ha-release-[VERSION].md` (gitignored).

## 🏡 Home map

`/ha-home-map` draws your home as one interactive page: each area is a card holding its devices, linked to the automations, scripts, and scenes that trigger or control them. The page is a single HTML file that opens straight from disk, with no server or internet connection.

[![Home map of a made-up home: each room a card holding colored device icons and dark automation squares, linked by dashed trigger lines and solid control arrows, with display options, a legend, and filters in the sidebar](demo/assets/home-map.png)](demo/assets/home-map.html)

**Try it first:** [demo/assets/home-map.html](demo/assets/home-map.html) maps a made-up home with 12 rooms, 166 devices, and 57 automations. GitHub shows the file as source, so use **Download raw file** and open the download in your browser.

### Build your map

The map reads your registries and automation YAML from [SSH snapshots](#-optional-ssh-snapshots), and its graph builder needs [PyYAML](https://pypi.org/project/PyYAML/) or [uv](https://docs.astral.sh/uv/). Run it in Claude Code, with an optional page title:

```text
/ha-home-map
/ha-home-map Beach house
```

It runs only when you call it, and then:

1. Refreshes `ha-data/` over SSH when the snapshot is more than a day old, including every file `configuration.yaml` includes.
2. Saves the map to `.temp/home-map/home-map.html` (gitignored).
3. Replies with a link to the file (on WSL, also a `file://wsl.localhost/…` address for your Windows browser), counts of what's on the map, and the automations it left off because they touch no device.

Without SSH access, it hands you the demo instead: the plugin ships it already built, so it needs no build and no PyYAML. Once your map exists, ask follow-up questions such as "what turns on the hallway light?": the agent answers from the map's data in `.temp/home-map/graph.json`.

The map lists your rooms, devices, and routines, so it stays on your machine and the agent shares only its local path. [Safety and privacy](#-safety-and-privacy) covers the one network request a build makes.

### Read the map

| You see | It means |
|---|---|
| Card | An area. **Across rooms** holds the automations, scripts, and scenes that touch several areas, and **No area** holds devices without one |
| Round icon | A device, colored by how it connects: Zigbee, Wi-Fi, Z-Wave, and so on |
| Dark square | An automation, script, or scene |
| Dashed line | Triggers: the device starts the automation |
| Solid arrow | Controls: the automation, script, or scene acts on the device |
| Dotted arrow | Runs: an automation or script starts another automation, script, or scene |

### Find your way around

- **Search** by name or entity ID, or press `/` to jump to the search box.
- **Click** an item to highlight everything linked to it and open its details: what triggers it, what it controls, and what it runs. `Esc` clears the selection.
- **Filter** by area, connection, device type, or integration in the sidebar: click a chip to show or hide it, or double-click it to show only that one. **Automated only** hides devices that no automation touches.
- **Zoom** with the scroll wheel, a pinch, a double-click, or `+` and `-`; drag or use the arrow keys to pan, and press `0` to fit the whole home.
- **Switch to Table** for a sortable list, **download** the current view as a PNG, or switch between light and dark.

## 🔒 Safety and privacy

- **Read-only SSH guard.** A `PreToolUse` hook inspects every Bash and PowerShell command. Commands that reach the `homeassistant` host must match a read-only allowlist; interactive SSH, uploads (`scp`, `sftp`, `rsync`), and everything else are denied. It guards against mistakes; it is not a sandbox.
- **Device control stays with you.** The skills only need `GetLiveContext` to read your home, and your client asks before each MCP tool call. For a hard guarantee, turn on the integration's **Read-only** option.
- **What leaves your machine.** Entity names and states from `GetLiveContext`, and any snapshot the agent reads (automations, logs, Zigbee2MQTT state), are sent to your AI provider as part of the conversation. `secrets.yaml` is never fetched, and the registries are trimmed before they are saved, so integration credentials never reach the disk. The home map stays on your machine; building it fetches only area icons it doesn't bundle, by icon name, from the jsdelivr CDN.
- **No tokens to handle.** Every client signs in through Home Assistant's own login page, so there is no access token to copy, paste, or leak.

## 🧱 Project structure

```text
.claude-plugin/
├── plugin.json                  # Plugin manifest (Claude Code + Copilot CLI): version, skills path
├── marketplace.json             # Marketplace entry used by `plugin marketplace add`
└── icon.png                     # Plugin icon
.claude/skills/                  # Every skill, in the one folder all three clients read
├── homeassistant/               # Entry point: live-context gate and skill routing
├── ha-config-fetch/             # fetch-ha-data.sh (SSH snapshots) and its helpers
├── ha-home-map/                 # /ha-home-map, on demand only: graph builder and page template
├── ha-docs-sitemap/             # SITEMAP.md of home-assistant.io
├── ha-implementation-format/    # YAML / How This Works / Customization Ideas output
├── ha-release-notes/            # /ha-release-notes, on demand only
├── ha-state-presentation/       # Live states grouped by area or function
├── ha-troubleshooting/          # Config, logs, traces, Developer Tools
└── esphome/                     # ESPHome YAML guidance and SITEMAP.md of esphome.io
hooks/hooks.json                 # SSH read-only guard config for plugin installs
.github/
├── hooks/                       # SSH read-only guard script, its tests, and its config for clones
├── instructions/                # Markdown rules for docs and generated reports
├── workflows/tests.yml          # CI: runs every test suite on pushes to main and on pull requests
└── dependabot.yml               # Weekly updates for the GitHub Actions in workflows/
tests/                           # Test suites for the skills, one folder per skill, kept out of the skill folders
demo/
├── demo_home.py                 # Generates made-up homes for the demo and the tests
├── build.sh                     # Rebuilds the demo home map; CI fails while the committed copy is stale
└── assets/                      # Demo home map (home-map.html), shipped already built, and its screenshot
images/                          # README logo
AGENTS.md                        # Instructions for coding agents working on this repo
CONTRIBUTING.md                  # Tests, version bumps, and commit style for contributors
SECURITY.md                      # How to report a vulnerability privately
LICENSE                          # MIT
ha-data/                         # Fetched HA snapshots and logs (gitignored)
ha-release-notes/                # Generated release reports (gitignored)
.temp/                           # Scratch output (gitignored)
```

## 🧯 Troubleshooting

**The agent can't reach Home Assistant:**

1. Check the server's status with `claude mcp list`, `copilot mcp list`, or **MCP: List Servers** in VS Code.
2. Check that the URL ends in `/api/mcp`, uses the right scheme (`https://` for Claude Code), and opens from this machine.
3. If sign-in fails or you get `401 Unauthorized`, check that the URL matches the **Internal URL** or **External URL** configured in Home Assistant, then sign in again (`claude mcp login homeassistant` in Claude Code). The integration docs' [troubleshooting section](https://www.home-assistant.io/integrations/mcp_server/#troubleshooting) covers the remaining OAuth cases.
4. The integration requires an administrator account by default, so signing in as a non-admin user fails. Sign in as an administrator or change that option in the integration.

**The agent says a device doesn't exist:** expose it under **Settings → Voice assistants → Expose**. The **Device control** tools only see exposed entities.

**The plugin doesn't load in Claude Code or Copilot CLI:**

```bash
claude plugin marketplace update homeassistant
claude plugin list
copilot plugin marketplace update homeassistant
copilot plugin list
```

From a local clone, validate the manifests with `claude plugin validate .`.

**SSH snapshots fail:** run `ssh homeassistant ls /config` first. If that works but Zigbee2MQTT data or logs are skipped, check the [snapshot table](#-optional-ssh-snapshots) for the access each one needs.

**Shell commands fail with an SSH guard hook startup error:**

Confirm Python is available: run `python3 --version` for Claude Code on any platform and for Copilot on Linux/macOS, or `python --version` for Copilot on Windows. On Windows, a `python3` or `python` command that only opens the Microsoft Store is an app execution alias, not an interpreter; install Python or turn the alias off in **Settings → Apps → Advanced app settings → App execution aliases**. The hook uses separate PowerShell and Bash launchers and inspects both the Bash and PowerShell tools; restart the client after changing hook configuration so it reloads. All Git subcommands, including `commit` and `push`, are allowed by this hook; the read-only restrictions apply only to direct SSH/file-transfer commands targeting `homeassistant`.

## 🤝 Contributing

Questions and ideas are welcome in [Discussions](https://github.com/calexandre/homeassistant-assistant/discussions); bugs go to [Issues](https://github.com/calexandre/homeassistant-assistant/issues). See [CONTRIBUTING.md](CONTRIBUTING.md) for how to test changes, and [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## 📄 License

[MIT](LICENSE)

## 📖 Resources

- [Home Assistant docs](https://www.home-assistant.io/docs/)
- [Model Context Protocol Server integration](https://www.home-assistant.io/integrations/mcp_server/)
- [ESPHome docs](https://esphome.io/)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins-reference)
- [GitHub Copilot](https://docs.github.com/en/copilot)
- [Model Context Protocol](https://modelcontextprotocol.io/)
