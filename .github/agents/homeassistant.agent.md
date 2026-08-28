---
name: Home Assistant Agent 🏠
description: Entry point for Home Assistant work; runs the `homeassistant` skill.
tools: [vscode/askQuestions, execute/getTerminalOutput, execute/killTerminal, execute/sendToTerminal, execute/runInTerminal, read/terminalSelection, read/terminalLastCommand, read/readFile, read/viewImage, agent, 'context7/*', edit/createFile, edit/editFiles, edit/rename, search, web, homeassistant-cazita/GetDateTime, homeassistant-cazita/GetLiveContext, todo]
---

## Compatibility Wrapper

This agent is the `Home Assistant Agent` entry point the release-note
orchestrator dispatches to. Read and follow the `homeassistant` skill, which
owns the live-context gate and the skill routing table.
