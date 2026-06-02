.PHONY: help validate validate-gaps validate-scenario validate-patch static-check build-indexes build-real-index test smoke-server run-server lint format typecheck clean

MANIFEST ?= mock_data/dma_subsystem/project_manifest.yaml
PYTHON ?= $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)
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

static-check: ## Run static patch checks (usage: make static-check FILE=path/to/patch.json MANIFEST=path/to/manifest.yaml)
	$(PYTHON) scripts/static_patch_check.py --file $(FILE) --manifest $(MANIFEST)

# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

build-indexes: ## Build all mock indexes from manifest data
	$(PYTHON) scripts/generate_mock_index.py --manifest $(MANIFEST)

build-real-index: ## Build coverage index from real URG report (axi2ahb)
	$(PYTHON) scripts/build_coverage_index.py --manifest mock_data/axi2ahb/project_manifest.yaml

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

accept: validate validate-gaps build-indexes build-real-index lint typecheck test smoke-server ## Run all acceptance checks

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove generated files (but keep mock indexes — they are fixtures)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
