# Home Assistant Assistant

[![GitHub Copilot](https://img.shields.io/badge/GitHub_Copilot-Enhanced-blue?style=flat-square&logo=github)](https://github.com/features/copilot)
[![Home Assistant](https://img.shields.io/badge/Home_Assistant-Compatible-green?style=flat-square&logo=homeassistant)](https://www.home-assistant.io/)
[![VS Code](https://img.shields.io/badge/VS_Code-Extension-blue?style=flat-square&logo=visualstudiocode)](https://code.visualstudio.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

> An intelligent GitHub Copilot assistant toolset specifically designed to accelerate Home Assistant automation development

[Features](#features) • [Getting Started](#getting-started) • [Configuration](#configuration) • [Usage](#usage) • [Project Structure](#project-structure)

---

## Overview

Home Assistant Assistant is a comprehensive GitHub Copilot enhancement that transforms how you develop Home Assistant automations. By leveraging specialized chatmodes, prompts, and direct integration with your Home Assistant instance, this toolset provides contextual assistance that understands your specific setup and entity states.

Whether you're building complex automations, troubleshooting configurations, or exploring new integrations, this assistant provides intelligent suggestions based on the official Home Assistant documentation and your live system state.

## Features

- **Live Entity Integration**: Direct connection to your Home Assistant instance for real-time entity state information
- **Specialized Chat Mode**: Custom GitHub Copilot chatmode optimized for Home Assistant development
- **Curated Prompt Library**: Ready-to-use prompts for common Home Assistant development tasks
- **Documentation-First Approach**: All suggestions are based on official Home Assistant documentation
- **Workflow Automation**: Streamlined development workflows with conventional commits and automated processes
- **Template Generation**: Intelligent code generation for automations, scripts, and configurations

## Getting Started

### Prerequisites

- **VS Code with GitHub Copilot**: Ensure you have GitHub Copilot enabled in VS Code
- **Home Assistant Instance**: A running Home Assistant installation with API access
- **Bearer Token**: Long-lived access token from your Home Assistant instance

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/calexandre/homeassistant-assistant.git
   cd homeassistant-assistant
   ```

2. **Set up VS Code workspace**: Open the project in VS Code to automatically load the custom prompts and chatmodes.

3. **Configure Home Assistant connection**:
   - The MCP (Model Context Protocol) configuration will prompt you for:
     - Your Home Assistant host URL
     - Your Home Assistant bearer token

> [!TIP]
> To create a long-lived access token in Home Assistant, go to your profile settings and create a new token in the "Long-lived access tokens" section.

### Quick Start

1. Open any file in VS Code within this workspace
2. Start a new chat with GitHub Copilot
3. Select the "Home Assistant" chatmode from the dropdown
4. Ask questions like:
   - "Show me all my light entities"
   - "Create an automation to turn on lights at sunset"
   - "Help me troubleshoot why my automation isn't working"

## Configuration

### MCP Server Setup

The project includes a pre-configured MCP server connection that securely connects to your Home Assistant instance:

```jsonc
{
  "servers": {
    "homeassistant-cazita": {
      "url": "https://${input:ha_host}/mcp_server/sse",
      "type": "http",
      "headers": {
        "Authorization": "Bearer ${input:ha_bearer_token}"
      }
    }
  }
}
```

This configuration:

- Uses input variables to avoid hardcoding sensitive information
- Connects to your Home Assistant's MCP server endpoint
- Provides secure authentication via bearer token

### Security

- **No Secrets in Git**: All sensitive configuration uses input prompts
- **Local-Only Temp Files**: Generated code is stored in `.temp/` (ignored by Git)
- **Token Security**: Bearer tokens are never committed to the repository

## Usage

### Home Assistant Chatmode

The specialized chatmode provides:

1. **Entity Discovery**: Automatically fetches current entity states before making suggestions
2. **Documentation Verification**: All responses are validated against official Home Assistant docs
3. **Template Generation**: Creates working YAML configurations for your specific setup
4. **Troubleshooting Guidance**: Step-by-step debugging help based on your actual configuration

### Available Prompts

- **`conventional-commit.prompt.md`**: Generate standardized commit messages
- **`prompt-builder.prompt.md`**: Create custom prompts for specific use cases  
- **`readme-blueprint-generator.prompt.md`**: Generate documentation for your projects
- **`remember.prompt.md`**: Store and recall important project context
- **`boost-prompt.prompt.md`**: Enhance existing prompts with additional capabilities

### Workflow Integration

The project includes automated workflows for:

- **Thought Logging**: Track Copilot's decision-making process
- **Markdown Standardization**: Consistent documentation formatting  
- **Safe Code Generation**: Temporary file handling for generated code

## Examples

### Creating an Automation

```yaml
# Generated by Home Assistant Assistant
automation:
  - alias: "Sunset Lighting"
    trigger:
      platform: sun
      event: sunset
    condition:
      condition: state
      entity_id: binary_sensor.occupancy_living_room
      state: 'on'
    action:
      service: light.turn_on
      target:
        entity_id: light.living_room_main
      data:
        brightness_pct: 75
```

### Entity State Query

Ask: *"What's the current state of all my climate entities?"*

Response includes real-time data from your Home Assistant instance with current temperatures, modes, and settings.

## Project Structure

```text
homeassistant-assistant/
├── .github/
│   ├── chatmodes/           # Custom Copilot chat modes
│   ├── instructions/        # Workflow and formatting instructions  
│   └── prompts/            # Reusable prompt templates
├── .vscode/
│   └── mcp.json           # Home Assistant MCP server configuration
├── .temp/                 # Generated code (Git ignored)
└── README.md
```

## Troubleshooting

### Connection Issues

If you can't connect to your Home Assistant instance:

1. **Verify URL**: Ensure your Home Assistant URL is accessible from your development environment
2. **Check Token**: Confirm your bearer token has the necessary permissions
3. **Network Access**: Verify there are no firewalls blocking the connection
4. **MCP Server**: Ensure the MCP server component is installed and running in Home Assistant

### Common Problems

- **Entity not found**: Use the live context feature to get exact entity IDs
- **Automation not triggering**: Check the automation trace in Home Assistant
- **Template errors**: Validate templates using Home Assistant's template developer tools

## Contributing

Contributions are welcome! This project follows conventional commit standards and includes automated workflows for consistent development.

1. Fork the repository
2. Create a feature branch
3. Use the conventional commit prompts for commit messages
4. Submit a pull request

## Resources

- [Home Assistant Documentation](https://www.home-assistant.io/docs/)
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [VS Code Extensions](https://marketplace.visualstudio.com/vscode)
