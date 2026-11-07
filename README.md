# 🏠 Home Assistant Assistant

<p align="center">
  <img src="images/haassistant-logo.png" alt="Pixel-art robot next to the Home Assistant house logo, wired to lights, sensors, and locks" width="50%" />
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/calexandre/homeassistant-assistant" alt="License: MIT" /></a>
  <a href=".claude-plugin/plugin.json"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcalexandre%2Fhomeassistant-assistant%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=plugin" alt="Plugin version" /></a>
  <a href="https://www.home-assistant.io/integrations/mcp_server/"><img src="https://img.shields.io/badge/Home%20Assistant-2025.2%2B-18BCF2?logo=homeassistant&logoColor=white" alt="Home Assistant 2025.2 or later" /></a>
</p>

> Your Home Assistant setup, understood by AI — grounded in your **live entities** and the **official docs**, not guesses.

Skills, an agent, and a safety hook for **Claude Code**, **GitHub Copilot CLI**, and **VS Code with GitHub Copilot** that help you build automations, scripts, scenes, and ESPHome configs for your existing Home Assistant installation. It is not for Home Assistant core development.

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
- 📂 **Config snapshots** — optional read-only SSH snapshots of automations, scripts, scenes, ESPHome YAMLs, Zigbee2MQTT data, and logs.
- 🔐 **Read-only SSH guard** — a hook that blocks destructive SSH commands against your Home Assistant host, whether they run in Bash or PowerShell.
- 🧩 **Cross-tool plugin** — the same skills, agent, and hook work in Claude Code, GitHub Copilot CLI, and VS Code.

## 🧭 How it works

```mermaid
flowchart LR
  user([You]) --> agent["Home Assistant agent<br/>Claude Code · Copilot CLI · VS Code"]
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
| `esphome` | Authors ESPHome device YAML with an esphome.io sitemap |

## 🧰 Prerequisites

| You need | For |
|---|---|
| Home Assistant 2025.2 or later with the [Model Context Protocol Server](https://www.home-assistant.io/integrations/mcp_server/) integration | Everything |
| One client: [Claude Code](https://claude.com/product/claude-code), [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-plugins), or VS Code with GitHub Copilot | Everything |
| Python 3 | The SSH read-only guard hook, which every client runs |
| SSH access to the Home Assistant host | Optional: [snapshots](#-optional-ssh-snapshots) of automations, scripts, scenes, config files, and logs |

Claude Code runs the hook as `python3` on every platform, including Windows. The Copilot clients run it as `python3` on Linux/macOS and as `python` on Windows.

## 🔗 Set up the Home Assistant MCP server

1. In Home Assistant, go to **Settings → Devices & services → Add Integration**, search for **Model Context Protocol Server**, and finish the setup flow.
2. Go to **Settings → Voice assistants → Expose** and expose the entities you want the agent to see. The default **Device control** tools only see exposed entities, so anything you leave out is invisible to the agent.
3. Note your MCP URL: your Home Assistant URL followed by `/api/mcp`, for example `https://example.ui.nabu.casa/api/mcp`.
4. For VS Code and Copilot CLI, create a token under **Profile → Security → Long-lived access tokens**. Claude Code can sign in through your browser instead.

Use an HTTPS URL when you can (Home Assistant Cloud, a reverse proxy, or Home Assistant's own TLS): the Home Assistant docs note that Claude Code only connects to MCP servers over HTTPS. VS Code also accepts a plain `http://homeassistant.local:8123` URL on your local network.

The integration's options control which tools it exposes and whether it requires an administrator account (on by default). See the [integration docs](https://www.home-assistant.io/integrations/mcp_server/) for the details.

## 📦 Installation

Pick your client. All three load the same skills, agent, and hook. Name the MCP server `homeassistant`: the agent's tool list uses that name.

### 🤖 Claude Code

```bash
claude plugin marketplace add calexandre/homeassistant-assistant
claude plugin install homeassistant-assistant@homeassistant
claude mcp add --scope user --transport http homeassistant https://YOUR-HOME-ASSISTANT/api/mcp
claude mcp login homeassistant
```

`claude mcp login` opens your browser to sign in to Home Assistant, so there is no token to copy. To use a long-lived token instead, skip the login and add the server with a header, as shown for Copilot CLI below (`claude mcp add` takes the same `--header` flag).

### 🐙 GitHub Copilot CLI

```bash
copilot plugin marketplace add calexandre/homeassistant-assistant
copilot plugin install homeassistant-assistant@homeassistant
read -rs HA_TOKEN
copilot mcp add --transport http homeassistant https://YOUR-HOME-ASSISTANT/api/mcp --header "Authorization: Bearer $HA_TOKEN"
```

`read -rs` waits silently: paste the long-lived token and press Enter, which keeps it out of your shell history. In PowerShell, run `$HA_TOKEN = Read-Host -MaskInput` instead; the `copilot mcp add` line works as is. Copilot CLI saves the server in `~/.copilot/mcp-config.json`.

### 🖥️ VS Code

```bash
git clone https://github.com/calexandre/homeassistant-assistant.git
code homeassistant-assistant
```

Skills, the agent, and the SSH guard hook load automatically from [.github/](.github/). VS Code keeps MCP servers in the Copilot Global configuration, `~/.copilot/mcp-config.json`, the same file Copilot CLI writes, so a server you added with `copilot mcp add` above is already there.

Otherwise, run **MCP: Add Server**, choose **HTTP**, enter `https://YOUR-HOME-ASSISTANT/api/mcp`, use the ID `homeassistant`, and save it to **Global → Copilot Global**. Then add your long-lived token to that server's entry in `~/.copilot/mcp-config.json`:

```json
"headers": {
  "Authorization": "Bearer YOUR_LONG_LIVED_TOKEN"
}
```

## ✅ Check that it works

Ask a question only your house can answer:

```text
> Which lights are on right now?
```

The answer should name your real entities. If the agent says it cannot reach Home Assistant, list your MCP servers with `claude mcp list`, `copilot mcp list`, or the **MCP: List Servers** command in VS Code, then see [Troubleshooting](#-troubleshooting).

## 📂 Optional: SSH snapshots

The MCP server exposes live entity state, but not your automation, script, or scene definitions, config files, or logs. With SSH access, the agent pulls read-only snapshots of those into `ha-data/` in your working directory (gitignored in this repo).

| Snapshot | Path on the host | Needs |
|---|---|---|
| `automations`, `scenes`, `scripts`, `configuration`, `customize` YAML | `/config` | Any SSH add-on |
| ESPHome device YAMLs (`secrets.yaml` is always skipped) | `/config/esphome` | Any SSH add-on |
| Zigbee2MQTT `configuration`, `devices`, `groups`, `state.json` | `/share/zigbee2mqtt` | Root, or a user with `sudo` |
| Core and Supervisor logs, last 12 hours | Docker container logs | **Advanced SSH & Web Terminal** add-on with **Protection mode** off |

1. Install an SSH add-on in Home Assistant and add your public key to it. The official **Terminal & SSH** add-on covers config files and ESPHome YAMLs; the community **Advanced SSH & Web Terminal** add-on with protection mode off covers everything.
2. Add a host alias named exactly `homeassistant` to `~/.ssh/config` (the fetch script and the read-only guard both use that name), with `User` and `Port` set to what your add-on uses:

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
   .github/skills/ha-config-fetch/fetch-ha-data.sh
   ```

The script reads `/config` by default. If your add-on mounts the config elsewhere, pass the path: `.github/skills/ha-config-fetch/fetch-ha-data.sh /homeassistant`.

## 💡 Usage examples

In Claude Code and Copilot CLI, just ask: the `homeassistant` skill picks up any Home Assistant request. In VS Code, open Chat and choose **Home Assistant Agent 🏠** from the agent picker.

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

## 🔒 Safety and privacy

- **Read-only SSH guard.** A `PreToolUse` hook inspects every Bash and PowerShell command. Commands that reach the `homeassistant` host must match a read-only allowlist; interactive SSH, uploads (`scp`, `sftp`, `rsync`), and everything else are denied. It guards against mistakes; it is not a sandbox.
- **Read-only MCP tools in the agent.** From the Home Assistant MCP server, the Home Assistant Agent lists only the `GetLiveContext` and `GetDateTime` tools, so it can read your home but not control devices. Outside the agent, your client asks before each MCP tool call.
- **What leaves your machine.** Entity names and states from `GetLiveContext`, and any snapshot the agent reads (automations, logs, Zigbee2MQTT state), are sent to your AI provider as part of the conversation. `secrets.yaml` is never fetched.
- **Tokens.** Claude Code's browser sign-in avoids handling a token at all. Otherwise use `read -rs` as shown above so the token stays out of your shell history. Copilot CLI and VS Code store the token in `~/.copilot/mcp-config.json`, so keep that file private and out of any dotfiles repo.

## 🧱 Project structure

```text
.claude-plugin/
├── plugin.json            # Plugin manifest (Claude Code + Copilot CLI)
├── marketplace.json       # Marketplace entry used by `plugin marketplace add`
└── icon.png               # Plugin icon
hooks/hooks.json           # SSH read-only guard, Claude Code / Copilot CLI hook format
.github/
├── agents/                # Home Assistant Agent (*.agent.md)
├── skills/                # Domain skills (SKILL.md), auto-discovered by every client
├── hooks/                 # SSH read-only guard script, its tests, VS Code hook format
└── instructions/          # Markdown style rules for VS Code
AGENTS.md                  # Instructions for coding agents working on this repo
ha-data/                   # Fetched HA snapshots and logs (gitignored)
.temp/                     # Scratch output (gitignored)
```

## 🧯 Troubleshooting

**The agent can't reach Home Assistant:**

1. Check the server's status with `claude mcp list`, `copilot mcp list`, or **MCP: List Servers** in VS Code.
2. Check that the URL ends in `/api/mcp`, uses the right scheme (`https://` for Claude Code), and opens from this machine.
3. On `401 Unauthorized`, the token is wrong or revoked: create a new one, or run `claude mcp login homeassistant` again.
4. The integration requires an administrator account by default, so a token from a non-admin user fails. Use an admin token or change that option in the integration.

**The agent says a device doesn't exist:** expose it under **Settings → Voice assistants → Expose**. The **Device control** tools only see exposed entities.

**The Home Assistant Agent can't call `GetLiveContext`:** name the MCP server `homeassistant`, the name in the agent's tool list. Remove the server and add it again under that name if needed.

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
