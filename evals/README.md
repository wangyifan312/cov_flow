# Evals Directory

Evaluation cases for the DV AI Coverage Closure Skill Pack.

## Purpose

Eval cases verify that the Skills correctly:
- Trigger the expected MCP tool calls
- Produce the expected output structure
- Follow the workflow defined in each SKILL.md

## Current Status

**Eval runner dry-run mode implemented.** The runner validates eval YAML structure without LLM execution.

## How to Use (Current)

### Manual Review (without runner)

1. Copy the eval YAML
2. Paste the `prompt` into Claude Code
3. Verify the tool calls match `expected_tools`
4. Verify the output contains `expected_output_keys`
5. Verify the classification matches `expected_classification`

### Automated Validation (with runner)

**Single eval**:
```bash
python scripts/run_eval.py --eval evals/triage_gap_0001.yaml --dry-run
```

**Batch mode** (all evals in directory):
```bash
python scripts/run_eval.py --eval-dir evals/ --dry-run
```

**Output to file**:
```bash
python scripts/run_eval.py --eval evals/triage_gap_0001.yaml --out report.json
```

The runner validates:
1. YAML is parseable
2. Required fields exist: eval_id, task_mode, prompt, expected_tools
3. task_mode is valid enum: triage, scenario, generate-case, feedback
4. expected_tools is non-empty
5. Each tool in expected_tools exists in registered tools
6. expected_classification (if present) is valid enum

**Note**: LLM execution is deferred to Phase 6.

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

## Adding New Evals

1. Create a new YAML file in this directory
2. Follow the structure above
3. Use placeholder variables (`{project}`, `{scope}`) in prompts
4. Include at least one expected tool call
5. Add notes about what to verify beyond tool calls
