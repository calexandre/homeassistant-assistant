---
applyTo: '**'
description: 'Automatically save all user prompts for future reference, analysis, and prompt engineering improvements'
---

# Copilot Prompt Saver

**ABSOLUTE MANDATORY RULES:**
- You must save EVERY user prompt without exception
- You must save the prompt BEFORE responding to the user
- You must follow the exact file format specified
- You must create the directory structure if it doesn't exist
- Do NOT ask permission to save prompts - just do it silently
- Do NOT announce that you're saving the prompt unless the save fails

## Purpose
Automatically save user prompts to the documentation for future reference, analysis, and prompt engineering improvements.

## When to Save Prompts
Whenever a user writes a prompt (any request or question to Copilot), you MUST:

1. **Save the prompt** to a new file in `/docs/prompts/`
2. **Use the naming convention**: `prompt-<timestamp>.md`
   - Timestamp format: `YYYYMMDD-HHMMSS` (e.g., `prompt-20251002-143025.md`)
   - Use the current date and time when the prompt is received

### File Format
Each prompt file should contain:

```markdown
# <Human-Readable Timestamp>

## Prompt
<The exact prompt text from the user>

## Summary
<Brief summary of response/actions taken>

## Tags
`<category>` `<technology>` `<complexity>`
```

### Example

For a user prompt received on October 2, 2025 at 14:30:25:

**Filename**: `/docs/prompts/prompt-20251002-143025.md`

**Content**:
```markdown
# October 2, 2025 at 14:30:25

## Prompt
help me build this copilot instructions file with the following instructions:
Everytime I write a prompt I want copilot to save the prompt to a file in /docs/prompts.
Each prompt should have a separate file in the following format: prompt-<timestamp>.md

## Summary
Created comprehensive copilot instructions file with automatic prompt saving functionality.

## Tags
`feature-request` `documentation` `automation` `medium`
```

### Important Notes

1. **Create the directory** `/docs/prompts/` if it doesn't exist
2. **Always use absolute timestamps** to avoid naming conflicts
3. **Be concise** in the response summary - 1-2 sentences maximum
4. **Add relevant tags** to make prompts searchable and categorizable
5. **Save immediately** after receiving a prompt, before responding
6. **Handle errors gracefully** - if saving fails, inform the user but continue with the response

### Execution Workflow

**Step 1: Receive Prompt**
- User sends a prompt to Copilot

**Step 2: Generate Metadata**
- Create timestamp in format `YYYYMMDD-HHMMSS`
- Determine context and appropriate tags
- Keep this processing silent

**Step 3: Save Prompt File**
- Ensure `/docs/prompts/` directory exists
- Create file at `/docs/prompts/prompt-<timestamp>.md`
- Write prompt content using the template above
- Work silently without announcements

**Step 4: Proceed with User Request**
- Continue with normal response to the user's original request
- Only mention the save if it failed

**ENFORCEMENT RULES:**
- NEVER skip saving a prompt
- NEVER ask permission to save
- NEVER be verbose about the saving process
- ALWAYS save before responding
- ALWAYS use exact timestamp format
- ALWAYS follow the template structure
- If directory doesn't exist, create it silently
- If save fails, inform user briefly and continue
