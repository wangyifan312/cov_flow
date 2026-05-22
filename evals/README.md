# Evals Directory

Evaluation cases for the DV AI Coverage Closure Skill Pack.

## Purpose

Eval cases verify that the Skills correctly:
- Trigger the expected MCP tool calls
- Produce the expected output structure
- Follow the workflow defined in each SKILL.md

## Current Status

**Manual review stage.** Eval runner is not yet implemented (planned for Phase 2C).

## YAML Structure

Each eval file is a YAML document with the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eval_id` | string | yes | Unique identifier for this eval case |
| `task_mode` | string | yes | One of: `triage`, `scenario`, `generate-case`, `feedback` |
| `prompt` | string | yes | The user prompt to give to Claude Code |
| `expected_tools` | list | yes | MCP tools that should be called |
| `expected_classification` | string | no | Expected gap classification (for triage evals) |
| `expected_output_keys` | list | no | Expected keys in the output |
| `notes` | string | no | Additional context or expected behaviors |

## How to Use (Current)

1. Copy the eval YAML
2. Paste the `prompt` into Claude Code
3. Verify the tool calls match `expected_tools`
4. Verify the output contains `expected_output_keys`
5. Verify the classification matches `expected_classification`

## Future: Automated Eval Runner

Phase 2C will implement an eval runner that:
- Executes each eval YAML automatically
- Captures tool calls and outputs
- Compares against expected values
- Generates a quality report

## Adding New Evals

1. Create a new YAML file in this directory
2. Follow the structure above
3. Use placeholder variables (`{project}`, `{scope}`) in prompts
4. Include at least one expected tool call
5. Add notes about what to verify beyond tool calls
