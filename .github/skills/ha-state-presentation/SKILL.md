---
name: ha-state-presentation
description: >-
  Present Home Assistant live entity states with domain emojis, grouped by
  area or function. Use when answering current states, status checks, or
  monitoring queries from GetLiveContext output.
---

# HA State Presentation

## When to use

- The user asks for current entity states, a status check, or monitoring.
- You have already called `GetLiveContext` (the agent's universal first step).

## Domain emojis

| Emoji | Domain / class |
|---|---|
| 💡 | lights (`light`) |
| 🌡️ | climate / temperature sensors (`climate`, `sensor` with temperature) |
| 🔌 | switches and outlets (`switch`) |
| 🎵 | media players (`media_player`) |
| 🏠 | areas and general home status |
| 🔋 | battery sensors |
| 🚨 | security / alarm (`alarm_control_panel`, `binary_sensor` with security classes) |
| 📺 | TVs and displays |
| 🚪 | doors and locks (`lock`, `binary_sensor` with door/opening classes) |
| 🌊 | water sensors and pumps |
| 🤖 | vacuum cleaners and robotic devices |

## Presentation rules

- Group related entities by area or function.
- Include relevant state detail when available: brightness, temperature, battery level, etc.
- Use the `GetLiveContext` tool to retrieve the real-time data — never assume entity IDs.
