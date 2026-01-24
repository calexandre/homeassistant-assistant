# Home Assistant Assistant

GitHub Copilot workspace for building automations, scripts, and configurations on your existing Home Assistant installation. Not for Home Assistant core development.

The agent fetches your live entities via MCP and uses official documentation with code examples to provide accurate, hallucination-free guidance.

## Setup

### Prerequisites

- VS Code with GitHub Copilot
- Home Assistant instance with API access
- [MCP Server for Home Assistant](https://github.com/pdelfino/mcp-server-homeassistant) add-on installed
- Long-lived access token

### Home Assistant MCP Server Setup

1. Install the MCP Server add-on in Home Assistant:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Add repository: `https://github.com/pdelfino/mcp-server-homeassistant`
   - Install **MCP Server for Home Assistant**
   - Start the add-on

2. Generate a long-lived access token:
   - Go to **Profile** → **Security** → **Long-lived access tokens**
   - Click **Create Token** and copy it

### Installation

```bash
git clone https://github.com/calexandre/homeassistant-assistant.git
code homeassistant-assistant
```

VS Code will prompt for:

- **Host**: Your Home Assistant URL without `https://` (e.g., `homeassistant.local:8123`)
- **Bearer token**: The long-lived access token you created

The MCP configuration is in [.vscode/mcp.json](.vscode/mcp.json):

```json
{
  "servers": {
    "homeassistant": {
      "url": "https://${input:ha_host}/mcp_server/sse",
      "type": "http",
      "headers": {
        "Authorization": "Bearer ${input:ha_bearer_token}"
      }
    }
  }
}
```

## Usage

1. Open GitHub Copilot chat
2. Select **Home Assistant** agent
3. Ask questions like:
   - "Show me all my light entities"
   - "Create an automation to turn on lights at sunset"
   - "Debug why my motion sensor automation isn't triggering"

### Home Assistant Agent

The [homeassistant.agent.md](.github/agents/homeassistant.agent.md) provides expert assistance for building automations and configurations:

- **Live entity discovery**: Fetches real-time device and entity states before providing suggestions
- **Documentation-first**: Searches official HA docs and retrieves working examples before responding—avoids hallucinating syntax or deprecated patterns
- **Source citations**: Links to exact documentation sections used
- **Modern syntax**: Uses current patterns (2024.8+ action format)

**Examples:**

```text
> What's the status of all my climate devices?

> Create a motion-activated light automation for the living room

> Help me debug this template: {{ states('sensor.temperature') | float }}
```

### Release Notes Analyzer

The [ha-release-notes.prompt.md](.github/prompts/ha-release-notes.prompt.md) generates personalized release summaries based on your setup:

**Usage:**

```text
/ha-release-notes
```

**Output includes:**

- Feature highlights relevant to your devices
- New integrations matching your setup
- Improvements to integrations you use
- Breaking changes impact assessment
- Update recommendation

Summaries are saved to `ha-release-notes/ha-release-[VERSION].md`.

## Project Structure

```text
.github/
├── agents/          # Copilot agents
├── instructions/    # Workflow guidance
└── prompts/         # Reusable prompts
.vscode/
└── mcp.json         # MCP server config
ha-release-notes/    # Generated release summaries
```

## Resources

- [Home Assistant Docs](https://www.home-assistant.io/docs/)
- [GitHub Copilot](https://docs.github.com/en/copilot)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## Troubleshooting

**Cannot connect to MCP server:**

1. Verify the MCP Server add-on is running in Home Assistant
2. Test the endpoint: `curl -H "Authorization: Bearer YOUR_TOKEN" https://your-ha-url/mcp_server/sse`
3. Check that your token has the required permissions
