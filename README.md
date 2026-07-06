# 🏠 Home Assistant Assistant

<p align="center">
  <img src="images/haassistant-logo.png" alt="Home Assistant Assistant" width="50%" />
</p>

> Your Home Assistant setup, understood by AI — grounded in your **live entities** and the **official docs**, not guesses.

A GitHub Copilot / Claude Code / GitHub Copilot CLI workspace for building automations, scripts, and configurations on your existing Home Assistant installation.
It is not for Home Assistant core development.

Before answering, the agent checks what you actually have (via MCP) and how Home Assistant says to do it (via the official docs).
That combination is what keeps it from hallucinating entity IDs or deprecated YAML syntax.

## 📚 Contents

- [✨ Features](#-features)
- [🧰 Prerequisites](#-prerequisites)
- [📦 Installation](#-installation)
- [🗂️ Fetching your Home Assistant configs](#️-fetching-your-home-assistant-configs)
- [💡 Usage examples](#-usage-examples)
- [🗺️ Project structure](#️-project-structure)
- [📖 Resources](#-resources)
- [🧯 Troubleshooting](#-troubleshooting)

## ✨ Features

- 🔌 **Live entity context** — pulls real devices, entities, and areas via `GetLiveContext` before suggesting anything.
- 📚 **Docs-grounded answers** — fetches the official Home Assistant docs and cites the exact section used.
- 🩺 **Troubleshooting playbook** — a guided flow through config checks, traces, and logs when something misbehaves.
- 🔧 **ESPHome support** — device YAML authoring backed by the esphome.io sitemap.
- 📰 **Release notes analyzer** — personalized summaries of new HA releases based on your actual setup.
- 🧪 **Multi-model benchmarking** — compares release-note summaries across models against your live setup.
- 🔐 **Read-only SSH guard** — a hook that blocks destructive SSH commands against your Home Assistant host.
- 🧩 **Cross-tool plugin** — the same skills, agents, and hook install into VS Code, Claude Code, and GitHub Copilot CLI.

## 🧰 Prerequisites

- A Home Assistant instance with the [Model Context Protocol Server integration](https://www.home-assistant.io/integrations/mcp_server/) enabled.
- A [long-lived access token](https://www.home-assistant.io/docs/authentication/#your-account-profile).
- SSH access to Home Assistant with a host alias `homeassistant` in `~/.ssh/config` (passwordless), used only to fetch automations, scenes, scripts, and logs.
- One of: VS Code with GitHub Copilot, [Claude Code](https://claude.com/product/claude-code), or [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-plugins).

### 🔗 Enabling the Home Assistant MCP server

1. Go to **Settings → Devices & services → Add Integration**.
2. Search for **Model Context Protocol Server** and follow the setup flow.
3. Go to **Profile → Security → Long-lived access tokens** and create a token.

The integration exposes an endpoint at `/api/mcp` over the Streamable HTTP transport — that's the URL and transport every config in this repo uses.

## 📦 Installation

Pick the client you use. All three read the same skills, agents, and hook — only the setup command differs.

### 🖥️ VS Code

```bash
git clone https://github.com/calexandre/homeassistant-assistant.git
code homeassistant-assistant
```

VS Code prompts for:

- **Host** — your Home Assistant URL without `https://` (e.g. `homeassistant.local:8123`).
- **Bearer token** — the long-lived access token you created above.

The MCP configuration lives in [.vscode/mcp.json](.vscode/mcp.json); skills, agents, and the SSH guard hook load automatically from [.github/](.github/).

### 🤖 Claude Code

No checkout needed — add the marketplace and install the plugin straight from GitHub:

```bash
export HA_HOST="homeassistant.local:8123"
export HA_BEARER_TOKEN="your-long-lived-token"
claude plugin marketplace add calexandre/homeassistant-assistant
claude plugin install homeassistant-assistant@homeassistant
claude
```

### 🐙 GitHub Copilot CLI

No checkout needed — add the marketplace and install the plugin straight from GitHub:

```bash
export HA_HOST="homeassistant.local:8123"
export HA_BEARER_TOKEN="your-long-lived-token"
copilot plugin marketplace add calexandre/homeassistant-assistant
copilot plugin install homeassistant-assistant@homeassistant
copilot
```

## 🗂️ Fetching your Home Assistant configs

Automations, scenes, scripts, `configuration.yaml`, and logs are **not** exposed by the MCP server.
Fetch them over SSH instead:

```bash
.github/skills/ha-config-fetch/fetch-ha-data.sh
```

Files land in `ha-data/` (gitignored). The script assumes the standard HAOS config path (`/config`); override it if needed:

```bash
.github/skills/ha-config-fetch/fetch-ha-data.sh /custom/config/path
```

## 💡 Usage examples

Open the chat, pick the **Home Assistant Agent 🏠**, and ask away.

### 🩺 Debugging

```text
> My motion sensor automation isn't triggering — help me debug it.

> Why does this template return unknown? {{ states('sensor.temperature') | float }}
```

The troubleshooting skill walks through config checks, automation traces, and logs before proposing a fix.

### 🤖 Creating automations

```text
> Create an automation that turns on the living room lights at sunset,
  but only if someone is home.

> Turn my kitchen ceiling switch into a scene that also dims the hall lights.
```

### 🔧 ESPHome devices

```text
> Add a BME280 sensor to the hall corridor wall switch over I2C.
```

### 📰 Release notes

```text
/ha-release-notes
```

Generates a personalized summary of a Home Assistant release — highlights, new integrations, and breaking-change impact — based on your actual devices and configs.
Saved to `ha-release-notes/ha-release-[VERSION].md`.

### 🧪 Benchmarking release-note models

Use the **HA Release Multi-Model 🧪** agent to generate and score summaries from multiple models against your live setup.

## 🗺️ Project structure

```text
.claude-plugin/plugin.json   # Plugin manifest (Claude Code + Copilot CLI)
.mcp.json                    # MCP server config for the plugin (http, /api/mcp)
hooks/hooks.json             # SSH read-only guard, Claude/Copilot hook format
.vscode/mcp.json             # MCP server config for the VS Code workspace
.github/
├── agents/                  # Copilot/Claude agents (*.agent.md)
├── skills/                  # Domain skills (SKILL.md), auto-discovered everywhere
├── prompts/                 # VS Code reusable prompts
├── instructions/             # VS Code workflow guidance
└── hooks/                    # SSH read-only guard, VS Code hook format
ha-data/                       # Fetched HA configs and logs (gitignored)
ha-release-notes/              # Generated release summaries (gitignored)
```

## 📖 Resources

- [Home Assistant Docs](https://www.home-assistant.io/docs/)
- [Model Context Protocol Server integration](https://www.home-assistant.io/integrations/mcp_server/)
- [GitHub Copilot](https://docs.github.com/en/copilot)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins-reference)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🧯 Troubleshooting

**Cannot connect to the MCP server:**

1. Confirm the **Model Context Protocol Server** integration is set up in Home Assistant.
2. Test the endpoint directly:

   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" https://your-ha-url/api/mcp
   ```

3. Check that your long-lived token hasn't expired and has the required scope.

**Plugin doesn't load in Claude Code or Copilot CLI:**

```bash
claude plugin marketplace update homeassistant
claude plugin list
copilot plugin marketplace update homeassistant
copilot plugin list
```

Confirm `HA_HOST`/`HA_BEARER_TOKEN` are set in your shell before starting the client. If you're working from a local clone, validate the manifests directly with `claude plugin validate .`.
