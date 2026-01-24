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

2. **Fetch Release Notes**
   - Fetch the release notes page from the provided URL
   - Extract all highlights, new integrations, improvements, and breaking changes
   - **Capture section anchors**: Note the HTML anchor IDs for each highlight section (e.g., `#home-dashboard-improvements`, `#new-integrations`)

3. **Generate Personalized Summary**

   For each major highlight, provide:
   - **Feature Name**: Brief description with a **clickable link** to the section anchor in the release notes (e.g., `[Home Dashboard Improvements](URL#home-dashboard-improvements)`)
   - **What's New**: 1-2 sentence explanation
   - **Hint for Your Setup**: How this feature could benefit your specific devices/areas

4. **New Integrations Review**
   - List new integrations that could be relevant to your setup
   - Highlight any that match your existing device categories

5. **Integration Improvements**
   - Focus on improvements to integrations you currently use
   - Note any that affect your specific devices

6. **Backward-Incompatible Changes Assessment**

   For each breaking change:
   - **Integration**: Name
   - **Affected**: Yes/No based on your setup
   - **Action Required**: If affected, what you need to do

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
- **Action Required**: What you need to do (if affected)

> Repeat for each breaking change. Link each integration to its section in the release notes.

## ✅ Update Recommendation
- Safe to update / Review required / Wait for patch

## Example Usage

```
Analyze https://www.home-assistant.io/blog/2026/01/07/release-20261/
```
