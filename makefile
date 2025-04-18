# --- Configuration ---
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/Scripts/python.exe
PIP := $(VENV_DIR)/Scripts/pip.exe

# Default target
.DEFAULT_GOAL := help

# --- Targets ---

install:  ## Install all dependencies from requirements.txt
	$(PIP) install -r requirements.txt

freeze:  ## Freeze current venv to requirements.txt
	$(PIP) freeze > requirements.txt

update:  ## Upgrade all packages to latest versions (safely)
	@outdated=$$($(PIP) list --outdated --format=columns | awk 'NR>2 {print $$1}'); \
	if [ -n "$$outdated" ]; then \
		echo "Updating: $$outdated"; \
		echo "$$outdated" | xargs -n1 $(PIP) install -U; \
	else \
		echo "All packages are up to date."; \
	fi

check:  ## Show outdated packages
	$(PIP) list --outdated

run:  ## Run the sun-checker script
	$(PYTHON) src/main.py

clean:  ## Remove __pycache__ and .pyc files
	find . -type d -name '__pycache__' -exec rm -r {} + || true
	find . -name '*.pyc' -delete || true

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "🛠  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
