.PHONY: help validate validate-gaps validate-scenario validate-patch build-indexes test smoke-server run-server lint format typecheck clean

MANIFEST ?= mock_data/dma_subsystem/project_manifest.yaml
PYTHON ?= python
FILE ?=

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

validate: ## Validate the project manifest
	$(PYTHON) scripts/validate_manifest.py --manifest $(MANIFEST)

validate-gaps: ## Validate coverage_gaps.json
	$(PYTHON) scripts/validate_coverage_gaps.py --manifest $(MANIFEST)

validate-scenario: ## Validate a scenario card (usage: make validate-scenario FILE=path/to/card.json)
	$(PYTHON) scripts/validate_scenario_card.py --file $(FILE)

validate-patch: ## Validate a testcase patch (usage: make validate-patch FILE=path/to/patch.json)
	$(PYTHON) scripts/validate_patch_metadata.py --file $(FILE)

# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

build-indexes: ## Build all mock indexes from manifest data
	$(PYTHON) scripts/generate_mock_index.py --manifest $(MANIFEST)

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

run-server: ## Start the DV Context MCP server (manual, blocking)
	$(PYTHON) -m dv_mcp.dv_context_server.server

smoke-server: ## Smoke-test: verify server module imports and tool registration
	PYTHONPATH=. $(PYTHON) scripts/smoke_server.py

# ---------------------------------------------------------------------------
# Testing & Quality
# ---------------------------------------------------------------------------

test: ## Run all tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Run ruff linter
	$(PYTHON) -m ruff check .

lint-fix: ## Run ruff linter with auto-fix
	$(PYTHON) -m ruff check --fix .

format: ## Run ruff formatter
	$(PYTHON) -m ruff format .

typecheck: ## Run mypy type checker
	$(PYTHON) -m mypy lib/ scripts/ dv_mcp/

# ---------------------------------------------------------------------------
# Full acceptance
# ---------------------------------------------------------------------------

accept: validate validate-gaps build-indexes test smoke-server ## Run all acceptance checks

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove generated files (but keep mock indexes — they are fixtures)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
