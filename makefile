# --- Configuration ---
VENV := .venv
SRC := src/main.py

SCRIPT_PATH := $(shell realpath $(SRC))
LOG_CRON := $(shell pwd)/cron.log
LOG_BOOT := $(shell pwd)/boot.log
REQUIREMENTS := requirements.txt

OS := $(shell uname -s 2>/dev/null || echo Windows)
OS := Windows

UTF8_ENV := LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
# Default target
.DEFAULT_GOAL := help

ifeq ($(OS),Windows)
	PYTHON := $(shell pwd)/$(VENV)/Scripts/python.exe
	PIP := $(shell pwd)/$(VENV)/Scripts/pip.exe
else
	PYTHON := $(shell pwd)/$(VENV)/bin/python
	PIP := $(shell pwd)/$(VENV)/bin/pip
endif

.PHONY: help venv install update run logs cron clean freeze check

# --- Targets ---
install:  ## Create venv if it doesn't exist and install all dependencies
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
	fi
	. $(VENV)/bin/activate && $(PIP) install -r requirements.txt || $(PIP) install -r requirements.txt

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

run: ## Run the sun-checker script
	$(PYTHON) $(SRC)

clean:  ## Remove __pycache__ and .pyc files
	find . -type d -name '__pycache__' -exec rm -r {} + || true
	find . -name '*.pyc' -delete || true

logs: ## Show boot and cron logs
	@echo "Tailing logs (cron + boot)..."
	@tail -f $(LOG_CRON) $(LOG_BOOT)

cron:
	@echo "Installing crontab entries..."
	@crontab -l 2>/dev/null | grep -v "$(PYTHON)" > temp_cron || true
	@echo "*/15 * * * * cd $(shell pwd) && $(UTF8_ENV) $(PYTHON) $(SRC) >> cron.log 2>&1" >> temp_cron
	@sort -u temp_cron > temp_cron_sorted
	@crontab temp_cron_sorted
	@rm -f temp_cron temp_cron_sorted
	@echo "Crontab updated. Use 'crontab -l' to verify."


help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf ">  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
