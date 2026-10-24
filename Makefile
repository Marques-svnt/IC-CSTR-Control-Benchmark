SHELL := /bin/bash
VENV_BIN := .venv/bin
PYTHON := $(VENV_BIN)/python
PYTEST := $(VENV_BIN)/pytest
RUFF := $(VENV_BIN)/ruff

.PHONY: help test lint desk-check exp01 exp02 paper01-pdf paper01-pack sync-vault clean

help:
	@echo "========================================================================"
	@echo "  CSTR Non-Linear Control Research Monorepo - Automation Workflow"
	@echo "========================================================================"
	@echo "  make test          - Executa os 125 testes unitários e de integração"
	@echo "  make lint          - Valida conformidade estrita com Ruff (check + format)"
	@echo "  make desk-check    - Valida requisitos editoriais da Elsevier (cas-dc)"
	@echo "  make exp01         - Roda benchmark determinístico do Artigo 1 (JPC)"
	@echo "  make exp02         - Roda campanha de robustez e Monte Carlo"
	@echo "  make paper01-pdf   - Compila manuscrito Elsevier cas-dc com latexmk"
	@echo "  make paper01-pack  - Empacota ready_to_overleaf.zip com checksums"
	@echo "  make sync-vault    - Sincroniza artefatos com o cofre Obsidian"
	@echo "  make clean         - Remove caches e arquivos intermediários de compilação"
	@echo "========================================================================"

test:
	$(PYTEST) tests/ --strict-markers -v

lint:
	$(RUFF) check src/ tests/ experiments/ scripts/
	$(RUFF) format --check src/ tests/ experiments/ scripts/

desk-check:
	$(PYTHON) scripts/verify_elsevier_desk_check.py --paper-dir papers/01_journal_of_process_control
	$(PYTHON) scripts/verify_elsevier_desk_check.py --paper-dir papers/02_computers_chemical_engineering
	$(PYTHON) scripts/verify_elsevier_desk_check.py --paper-dir papers/03_chemical_engineering_research_design

exp01:
	$(PYTHON) experiments/exp_01_classical_benchmark.py

exp02:
	$(PYTHON) experiments/exp_02_robustness_campaign.py

paper01-pdf:
	cd papers/01_journal_of_process_control && latexmk -pdf -interaction=nonstopmode main.tex

paper02-pdf:
	cd papers/02_computers_chemical_engineering && latexmk -pdf -interaction=nonstopmode main.tex

paper03-pdf:
	cd papers/03_chemical_engineering_research_design && latexmk -pdf -interaction=nonstopmode main.tex

papers-pdf: paper01-pdf paper02-pdf paper03-pdf

paper01-pack: paper01-pdf desk-check
	cd papers/01_journal_of_process_control/ready-to-overleaf && zip -FS -r ../ready_to_overleaf.zip . -x "*.DS_Store" "*__pycache__*"
	@echo "Artefato gerado: papers/01_journal_of_process_control/ready_to_overleaf.zip"

paper02-pack: paper02-pdf desk-check
	cd papers/02_computers_chemical_engineering/ready-to-overleaf && zip -FS -r ../ready_to_overleaf.zip . -x "*.DS_Store" "*__pycache__*"
	@echo "Artefato gerado: papers/02_computers_chemical_engineering/ready_to_overleaf.zip"

paper03-pack: paper03-pdf desk-check
	cd papers/03_chemical_engineering_research_design/ready-to-overleaf && zip -FS -r ../ready_to_overleaf.zip . -x "*.DS_Store" "*__pycache__*"
	@echo "Artefato gerado: papers/03_chemical_engineering_research_design/ready_to_overleaf.zip"

papers-pack: paper01-pack paper02-pack paper03-pack

sync-vault:
	python3 /home/marques/vault/svnt/scripts/sync_antigravity.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".hypothesis" -exec rm -rf {} +
	find papers/ -type f \( -name "*.aux" -o -name "*.bbl" -o -name "*.blg" -o -name "*.log" -o -name "*.out" -o -name "*.fdb_latexmk" -o -name "*.fls" \) -delete
	rm -rf .coverage
