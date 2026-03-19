.PHONY: setup install dev run clean lint test playwright help

# Default target
help: ## Show this help message
	@echo.
	@echo  Company Career Scout - Available Commands
	@echo  ==========================================
	@echo.
	@echo  make setup       - Create venv with uv and install all deps
	@echo  make install     - Install dependencies only (venv must exist)
	@echo  make playwright  - Install Playwright browsers
	@echo  make dev         - Full setup + run (first time)
	@echo  make run         - Start the Streamlit app
	@echo  make clean       - Remove venv, cache, and compiled files
	@echo  make lint        - Syntax-check all Python files
	@echo  make test        - Run tests
	@echo  make env         - Copy .env.example to .env
	@echo.

# ── Environment Setup ──────────────────────────────────────

setup: ## Create virtual environment with uv and install deps
	uv venv
	uv pip install -r requirements.txt

install: ## Install/update dependencies into existing venv
	uv pip install -r requirements.txt

playwright: ## Install Playwright Chromium browser
	uv run playwright install chromium

env: ## Create .env from template (won't overwrite existing)
	@if not exist .env copy .env.example .env && echo Created .env from template || echo .env already exists

# ── Development ────────────────────────────────────────────

dev: setup playwright env ## Full first-time setup then run
	uv run streamlit run frontend/app.py

run: ## Start the Streamlit dashboard
	uv run streamlit run frontend/app.py

lint: ## Syntax-check all Python files
	uv run python -m compileall -q agents core frontend

test: ## Run tests (if any exist)
	uv run python -m pytest tests/ -v

# ── Cleanup ────────────────────────────────────────────────

clean: ## Remove venv, cache DB, and compiled files
	@if exist .venv rmdir /s /q .venv
	@if exist data\cache.db del data\cache.db
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@echo Cleaned up.
