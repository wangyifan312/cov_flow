.PHONY: help validate validate-gaps validate-scenario validate-patch validate-feedback static-check build-indexes build-real-index build-real-tb-index build-spec-index build-reg-index build-rtl-index build-dma-indexes build-sim-history-index test smoke-server run-server lint format typecheck clean

MANIFEST ?= mock_data/dma_subsystem/project_manifest.yaml
PYTHON ?= python3
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

validate-feedback: ## Validate a feedback report (usage: make validate-feedback FILE=path/to/report.json)
	$(PYTHON) scripts/validate_feedback_report.py --feedback $(FILE)

static-check: ## Run static patch checks (usage: make static-check FILE=path/to/patch.json MANIFEST=path/to/manifest.yaml)
	$(PYTHON) scripts/static_patch_check.py --file $(FILE) --manifest $(MANIFEST)

# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

build-indexes: ## Build all mock indexes from manifest data
	$(PYTHON) scripts/generate_mock_index.py --manifest $(MANIFEST)

build-real-index: ## Build coverage index from real URG report (axi2ahb)
	$(PYTHON) scripts/build_coverage_index.py --manifest mock_data/axi2ahb/project_manifest.yaml

build-real-tb-index: ## Build TB index from real UVM sources (axi2ahb, requires AXI2AHB_ROOT)
	$(PYTHON) scripts/build_tb_index.py --manifest mock_data/axi2ahb/project_manifest.yaml --out mock_data/axi2ahb/.dv_ai_index

build-spec-index: ## Build spec index from markdown FS (dma_subsystem)
	$(PYTHON) scripts/build_spec_index.py --manifest $(MANIFEST)

build-reg-index: ## Build register index from YAML definitions (dma_subsystem)
	$(PYTHON) scripts/build_reg_index.py --manifest $(MANIFEST)

build-rtl-index: ## Build RTL index from SV sources (dma_subsystem)
	$(PYTHON) scripts/build_rtl_index.py --manifest $(MANIFEST)

build-sim-history-index: ## Build simulation history index (dma_subsystem)
	$(PYTHON) scripts/build_sim_history_index.py --manifest $(MANIFEST)

build-dma-indexes: build-spec-index build-reg-index build-rtl-index build-sim-history-index ## Build all indexes for dma_subsystem

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

accept: validate validate-gaps build-indexes build-dma-indexes build-real-index lint typecheck test smoke-server ## Run all acceptance checks

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove generated files (but keep mock indexes — they are fixtures)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
