---
description: 'Analyze Home Assistant release notes and provide personalized summaries based on your current smart home setup. Includes highlights, integration improvements, and backward-incompatible change impact assessment.'
agent: 'homeassistant'
---

# Home Assistant Release Notes Analyzer

Analyze a Home Assistant release and provide a personalized summary based on my current setup.

## Input

Provide the release notes URL in this format:
- **Release URL**: `$input`

If no URL is provided, use the latest release from: `https://www.home-assistant.io/blog/`

## Workflow

1. **Get Current Setup Context**
   - Use `GetLiveContext` to retrieve all devices, entities, and areas in my Home Assistant instance
   - Note the integrations, device types, and domains in use

2. **Fetch Home Assistant Configs**
   - Run `scripts/fetch-ha-configs.sh` to download the latest automations, scenes, scripts, and configuration YAML from the live instance
   - Read `ha-configs/automations.yaml`, `ha-configs/scenes.yaml`, `ha-configs/scripts.yaml`, and `ha-configs/configuration.yaml`
   - Note all integrations, services, entity IDs, triggers, conditions, and actions referenced in the configs

3. **Fetch Release Notes**
   - Fetch the release notes page from the provided URL
   - Extract all highlights, new integrations, improvements, and breaking changes
   - **Capture section anchors**: Note the HTML anchor IDs for each highlight section (e.g., `#home-dashboard-improvements`, `#new-integrations`)

4. **Generate Personalized Summary**

   For each major highlight, provide:
   - **Feature Name**: Brief description with a **clickable link** to the section anchor in the release notes (e.g., `[Home Dashboard Improvements](URL#home-dashboard-improvements)`)
   - **What's New**: 1-2 sentence explanation
   - **Hint for Your Setup**: How this feature could benefit your specific devices/areas

5. **New Integrations Review**
   - List new integrations that could be relevant to your setup
   - Highlight any that match your existing device categories

6. **Integration Improvements**
   - Focus on improvements to integrations you currently use
   - Note any that affect your specific devices

7. **Backward-Incompatible Changes Assessment**

   Cross-reference each breaking change against **both** the live entity context (from `GetLiveContext`) **and** the fetched config files (from `ha-configs/`):
   - **Integration**: Name
   - **Affected**: Yes/No — check if the integration, service, entity ID, or deprecated feature appears in automations, scenes, scripts, or configuration YAML
   - **Config Impact**: List any automations, scenes, or scripts that reference the affected integration or deprecated functionality (by alias or entity ID)
   - **Action Required**: If affected, what you need to do and which config files need updating

## Output Format

**IMPORTANT**: Use only headings and bullet points throughout the entire report. Do NOT use markdown tables in any section.

# 🏠 Release Summary for [Version]

## [Feature Name](URL#anchor)
- **What's New**: 1-2 sentence explanation of the feature
- **Hint for Your Setup**: How this could benefit your specific devices/areas

## [Another Feature](URL#anchor)
- **What's New**: ...
- **Hint for Your Setup**: ...

> Repeat for each major highlight. Feature names must be clickable links to the release notes section.

## 🔌 New Integrations of Interest
- **[Integration Name](URL#anchor)**: Brief description and why it's relevant to your setup
- Each integration name should link to its documentation or release section

## 🔧 Improvements to Your Integrations
- **[Integration Name](URL#anchor)**: Description of improvement and affected devices
- Include links to the relevant section in the release notes

## Backward-Incompatible Changes ✅ or ⚠️

> Use ✅ if none of the breaking changes affect the user's setup. Use ⚠️ if there are considerations to be taken.

**Summary**: Brief 1-2 sentence overview stating whether the user has problems or not based on their setup analysis.

### [Integration Name](URL#anchor)
- **Affects You?**: Yes/No
- **Config Impact**: List automations, scenes, or scripts that reference the affected integration (if any)
- **Action Required**: What you need to do and which config files need updating (if affected)

> Repeat for each breaking change. Link each integration to its section in the release notes.

## ✅ Update Recommendation
- Safe to update / Review required / Wait for patch

## File Output

Save the generated summary to the `ha-release-notes/` folder using this naming convention:
- **Filename**: `ha-release-[VERSION].md` (e.g., `ha-release-2026.1.md`)
- If the file already exists, update it with the latest content
- If the file does not exist, create it

## Example Usage

```
Analyze https://www.home-assistant.io/blog/2026/01/07/release-20261/
```
