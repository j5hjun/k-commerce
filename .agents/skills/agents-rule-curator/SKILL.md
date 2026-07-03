---
name: agents-rule-curator
description: Distill repository rules from an ongoing conversation and add only the user-selected rules to the appropriate AGENTS.md file. Use when a user asks to extract, summarize, draft, select, or apply coding/test/workflow rules from discussion history into AGENTS.md, especially when the desired rules are implicit in prior conversation and need confirmation before editing.
---

# Agents Rule Curator

## Workflow

Use this skill to turn conversational decisions into durable `AGENTS.md` instructions without adding unapproved or overly broad rules.

1. Identify the target `AGENTS.md`.
   - Prefer the nearest scoped file for the rule, such as `packages/mcp/AGENTS.md` for MCP-package rules.
   - Use the repository root `AGENTS.md` only for rules that apply broadly across the repo.

2. Extract candidate rules from the conversation.
   - Convert repeated decisions, explicit preferences, and accepted review comments into concise imperative rules.
   - Ignore one-off troubleshooting details, temporary commands, environment incidents, and implementation notes that are not reusable.
   - Preserve scope: do not turn a rule about one provider, test folder, or command into a global rule.

3. Show a short numbered draft before editing when the user has not already selected exact items.
   - Present candidate selection, explanations, and confirmation questions in Korean when the conversation is in Korean.
   - Write the final rule text that will be inserted into `AGENTS.md` in English.
   - Keep each rule one sentence where practical.
   - Group related rules under a small heading only when it improves scanability.
   - Ask the user which numbered items to add.

4. Edit only the selected rules.
   - Add the rules to an existing relevant section when one exists.
   - Create a short section when needed, for example `## Smoke Test Rules`.
   - Keep existing AGENTS.md file maps and instructions intact.

5. Validate the edit.
   - Read the edited block to catch duplication, scope drift, or awkward wording.
   - Run formatting or lint checks only when the repository already has a cheap relevant check for docs or Markdown.
   - Summarize exactly which rules were added and where.

## Rule Quality

- Write rules as stable behavior, not as a transcript of the discussion.
- Use Korean for curation discussion and English for the durable `AGENTS.md` instructions.
- Prefer direct instructions: "Place MCP server tests under `packages/mcp/tests/`" instead of "We decided to place..."
- Include concrete paths, commands, or file names only when they are part of the reusable rule.
- Avoid adding rules that merely restate normal engineering practice unless the conversation established a repo-specific preference.
- If a rule conflicts with an existing `AGENTS.md`, point out the conflict and ask before editing.

## Example

For a conversation where the user selects rules 2, 3, and 4 from a repository-workflow discussion, add only those selected rules to the scoped `AGENTS.md`. Do not add unselected candidates, and do not rewrite unrelated file-map entries unless the selected rule requires it.
