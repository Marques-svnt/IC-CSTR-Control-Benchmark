SHELL := /bin/bash
VENV_BIN := .venv/bin
PYTHON := $(if $(wildcard $(VENV_BIN)/python),$(VENV_BIN)/python,python3)
PYTEST := $(if $(wildcard $(VENV_BIN)/pytest),$(VENV_BIN)/pytest,pytest)
RUFF := $(if $(wildcard $(VENV_BIN)/ruff),$(VENV_BIN)/ruff,ruff)

.PHONY: help test lint reproduce-numbers exp01 exp02 clean

help:
	@echo "========================================================================"
	@echo "  IC-CSTR-Control-Benchmark (JPC v2.0.0) - Reproducibility Workflow"
	@echo "========================================================================"
	@echo "  make test              - Run unit and property-based tests (pytest)"
	@echo "  make lint              - Check code style and formatting (ruff)"
	@echo "  make reproduce-numbers - Regenerate all 418 LaTeX macros & condensed tables from CSVs"
	@echo "  make exp01             - Run nominal classical benchmark (Paper 1)"
	@echo "  make exp02             - Run robustness and noise campaign (Paper 1)"
	@echo "  make clean             - Remove Python/pytest caches and temporary outputs"
	@echo "========================================================================"

test:
	$(PYTEST) tests/ --strict-markers -v

lint:
	$(RUFF) check src/ tests/ experiments/ scripts/
	$(RUFF) format --check src/ tests/ experiments/ scripts/

reproduce-numbers:
	$(PYTHON) scripts/jpc_numbers.py

exp01:
	$(PYTHON) experiments/exp_01_classical_benchmark.py

exp02:
	$(PYTHON) experiments/exp_02_robustness_campaign.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".hypothesis" -exec rm -rf {} +
	rm -rf .coverage outputs/
