# Home Assistant Assistant

[![GitHub Copilot](https://img.shields.io/badge/GitHub_Copilot-Enhanced-blue?style=flat-square&logo=github)](https://github.com/features/copilot)
[![Home Assistant](https://img.shields.io/badge/Home_Assistant-Compatible-green?style=flat-square&logo=homeassistant)](https://www.home-assistant.io/)
[![VS Code](https://img.shields.io/badge/VS_Code-Extension-blue?style=flat-square&logo=visualstudiocode)](https://code.visualstudio.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

> An intelligent GitHub Copilot enhancement that accelerates Home Assistant automation development through specialized chatmodes, live entity integration, and curated prompt templates.

[Features](#features) • [Getting Started](#getting-started) • [Usage](#usage) • [Examples](#examples) • [Troubleshooting](#troubleshooting)

---

## Overview

Home Assistant Assistant transforms GitHub Copilot into a specialized Home Assistant development companion. By integrating directly with your Home Assistant instance and providing expert-level guidance based on official documentation, this toolset enables rapid development of automations, scripts, and configurations.

The assistant provides real-time access to your entity states, intelligent code generation, and step-by-step troubleshooting guidance - all within your familiar VS Code environment.

## Features

### Live Home Assistant Integration

- Real-time entity state monitoring through MCP (Model Context Protocol)
- Direct connection to your Home Assistant instance
- Automatic entity discovery and validation

### Specialized GitHub Copilot Chatmode

- Expert Home Assistant development guidance
- Documentation-first approach using official HA docs
- Intelligent YAML generation and validation

### Curated Prompt Library

- Ready-to-use templates for common development tasks
- Conventional commit message generation
- Workflow automation and documentation helpers

### Development Acceleration

- Context-aware automation suggestions
- Template debugging and validation
- Integration guidance with step-by-step instructions

## Getting Started

### Prerequisites

- **VS Code with GitHub Copilot**: Active GitHub Copilot subscription
- **Home Assistant Instance**: Running installation with API access
- **Long-lived Access Token**: Generated from your Home Assistant profile

### Quick Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/calexandre/homeassistant-assistant.git
   cd homeassistant-assistant
   ```

2. **Open in VS Code**

   ```bash
   code .
   ```

3. **Configure MCP Connection**
   The workspace automatically prompts for:
   - Home Assistant host URL (without `https://`)
   - Bearer token for authentication

> [!TIP]
> Generate a long-lived access token in Home Assistant: **Profile** → **Security** → **Long-lived access tokens** → **Create Token**

### First Steps

1. Start a new GitHub Copilot chat in VS Code
2. Select **"Home Assistant"** from the chatmode dropdown
3. Try your first query: *"Show me all my light entities"*

## Usage

### Home Assistant Chatmode

The specialized chatmode provides context-aware assistance:

#### Entity Discovery

- Automatically fetches current entity states before suggestions
- Provides accurate entity IDs and current values
- Validates entity availability in your instance

#### Documentation-Verified Responses

- All guidance based on official Home Assistant documentation
- Links to relevant documentation sections
- Version-specific syntax and best practices

#### Intelligent Code Generation

- Creates working YAML configurations for your setup
- Provides modern syntax (2024.8+ action format)
- Includes customization suggestions and alternatives

### Example Interactions

#### Query Entity States

```text
"What's the current temperature of all my climate entities?"
```

#### Generate Automations

```text
"Create an automation to turn on outdoor lights at sunset when someone is home"
```

#### Debug Issues

```text
"My motion automation isn't triggering, help me troubleshoot"
```

### Available Prompts

Access specialized prompts from the `.github/prompts/` directory:

- **`conventional-commit.prompt.md`** - Generate standardized commit messages
- **`prompt-builder.prompt.md`** - Create custom development prompts
- **`readme-blueprint-generator.prompt.md`** - Generate project documentation
- **`remember.prompt.md`** - Store important project context
- **`boost-prompt.prompt.md`** - Enhance existing prompts

## Examples

### Automation Generation

**Request:**
> Create an automation for bedtime routine - turn off all lights except bedroom lamp, set to 10% brightness

**Generated YAML:**

```yaml
automation:
  - alias: "Bedtime Routine"
    trigger:
      platform: time
      at: "22:30:00"
    action:
      - action: light.turn_off
        target:
          entity_id: all
      - action: light.turn_on
        target:
          entity_id: light.bedroom_lamp
        data:
          brightness_pct: 10
```

### Entity State Query

**Request:**
> Show me all motion sensors and their current states

**Response:**

```text
🏠 Motion Sensors Status:

Living Room:
🤖 binary_sensor.living_room_motion: off (last_changed: 2 hours ago)

Kitchen:
🤖 binary_sensor.kitchen_motion: on (last_changed: 5 minutes ago)

Bedroom:
🤖 binary_sensor.bedroom_motion: off (last_changed: 8 hours ago)
```

## Project Structure

```text
homeassistant-assistant/
├── .github/
│   ├── chatmodes/              # Custom Copilot chat modes
│   │   └── homeassistant.chatmode.md
│   ├── instructions/           # Development workflow guidance
│   └── prompts/               # Reusable prompt templates
├── .vscode/
│   └── mcp.json              # MCP server configuration
└── .temp/                    # Generated code (git ignored)
```

## Troubleshooting

### Connection Issues

#### Cannot connect to Home Assistant

1. Verify your Home Assistant URL is accessible
2. Check bearer token permissions and validity
3. Ensure MCP server add-on is installed and running
4. Test connection: `curl -H "Authorization: Bearer YOUR_TOKEN" https://your-ha-url/api/`

#### Entity not found errors

1. Use the live context feature to get exact entity IDs
2. Check entity availability in Home Assistant Developer Tools
3. Verify integration is properly configured

### Common Problems

#### Automation not triggering

- Check automation traces in Home Assistant
- Validate trigger conditions using Developer Tools
- Review Home Assistant logs for errors

#### Template errors

- Test templates in Developer Tools → Template tab
- Verify entity states and attribute names
- Check Jinja2 syntax and Home Assistant template functions

> [!NOTE]
> All troubleshooting follows official Home Assistant documentation. The chatmode provides step-by-step debugging guidance specific to your configuration.

## Resources

- [Home Assistant Documentation](https://www.home-assistant.io/docs/)
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [VS Code Extensions Marketplace](https://marketplace.visualstudio.com/vscode)
