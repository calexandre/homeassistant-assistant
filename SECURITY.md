# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through [GitHub's private vulnerability reporting](https://github.com/calexandre/homeassistant-assistant/security/advisories/new) (the **Report a vulnerability** button on the Security tab). Please don't open a public issue.

Include the client and version you used, what you ran, and what happened. This is a spare-time project, so a reply may take a few days; confirmed reports get a fix or a plan in the advisory.

## Supported versions

Fixes land on the latest release only. Update the plugin (`claude plugin marketplace update homeassistant`, or the Copilot CLI equivalent) before reporting.

## In scope

- **SSH guard bypasses:** any command the agent can run that writes to, uploads to, or opens an interactive session on the `homeassistant` host despite the read-only guard in `.github/hooks/ssh-ha-readonly-guard.py`.
- **Secret exposure:** a skill, script, or default that fetches, prints, or commits `secrets.yaml`, access tokens, or other credentials.
- **Unsafe defaults** in the fetch script, hook configuration, or MCP configuration shipped in this repository.

## Out of scope

- Vulnerabilities in Home Assistant, its MCP Server integration, or SSH add-ons: report them to the [Home Assistant project](https://www.home-assistant.io/security/).
- Vulnerabilities in Claude Code, GitHub Copilot, or VS Code: report them to their vendors.
- Guard evasion through shell variables, aliases, functions, or encoded commands. The guard is documented as a protection against mistakes, not a sandbox.
