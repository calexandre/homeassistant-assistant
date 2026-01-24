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

3. **Generate Personalized Summary**

   For each major highlight, provide:
   - **Feature Name**: Brief description
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

### 🏠 Release Summary for [Version]

#### Highlights
| Feature | Description | Hint for Your Setup |
|---------|-------------|---------------------|
| ... | ... | ... |

#### 🔌 New Integrations of Interest
- List only those relevant to your setup

#### 🔧 Improvements to Your Integrations
- List improvements affecting your current integrations

#### ⚠️ Backward-Incompatible Changes
| Integration | Affects You? | Action Required |
|-------------|--------------|-----------------|
| ... | Yes/No | ... |

#### ✅ Update Recommendation
- Safe to update / Review required / Wait for patch

## Example Usage

```
Analyze https://www.home-assistant.io/blog/2026/01/07/release-20261/
```
