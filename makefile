# --- Configuration ---
VENV := .venv
SRC := src/main.py
REQUIREMENTS := requirements.txt

HOME := $(shell pwd)
PROJECT_NAME := $(notdir $(HOME))

LOG_CRON := $(HOME)/cron.log

LOGROTATE_CONF := /etc/logrotate.d/$(PROJECT_NAME)
LOGTMP := $(HOME)/$(PROJECT_NAME)_rotate.conf

OS := $(shell uname -s 2>/dev/null || echo Windows)
#OS := Windows

# Default target
.DEFAULT_GOAL := help

ifeq ($(OS),Windows)
	SCRIPT_PATH := $(HOME)/$(VENV)/Scripts
	ACTIVATE := $(SCRIPT_PATH)/activate.bat
	PYTHON := $(SCRIPT_PATH)/python.exe
	PIP := $(SCRIPT_PATH)/pip.exe
else
	SCRIPT_PATH := $(HOME)/$(VENV)/bin
	ACTIVATE := $(SCRIPT_PATH)/activate
	PYTHON := $(SCRIPT_PATH)/python
	PIP := $(SCRIPT_PATH)/pip
endif

.PHONY: help venv install update run logs cron clean freeze check

# --- Targets ---
install:  ## Create venv if it doesn't exist and install all dependencies
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
	fi
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

run: ## Run the sun-checker script
	$(PYTHON) $(SRC)

clean:  ## Remove __pycache__ and .pyc files
	find . -type d -name '__pycache__' -exec rm -r {} + || true
	find . -name '*.pyc' -delete || true

logs: ## Show boot and cron logs
	@echo "Tailing logs (cron + boot)..."
	@tail -f $(LOG_CRON) $(LOG_BOOT)

cron: ## Register the script in crontab (Linux)
	@echo "Installing crontab entries..."
	@crontab -l 2>/dev/null | grep -v "$(PYTHON)" > temp_cron || true
	@echo "*/15 * * * * cd $(shell pwd) && $(PYTHON) $(SRC) >> cron.log 2>&1" >> temp_cron
	@sort -u temp_cron > temp_cron_sorted
	@crontab temp_cron_sorted
	@rm -f temp_cron temp_cron_sorted
	@echo "Crontab updated. Use 'crontab -l' to verify."

setup-logrotate: ## Setup logrotate for cron logs (Linux)
	@echo "Setup logrotate for cron logs..."
	@echo "$(LOG_CRON) {"          >  $(LOGTMP)
	@echo "    weekly"              >> $(LOGTMP)
	@echo "    rotate 3"           >> $(LOGTMP)
	@echo "    compress"           >> $(LOGTMP)
	@echo "    missingok"          >> $(LOGTMP)
	@echo "    notifempty"         >> $(LOGTMP)
	@echo "    copytruncate"       >> $(LOGTMP)
	@echo "}"                      >> $(LOGTMP)
##	@sudo mv $(LOGTMP) $(LOGROTATE_CONF)
	@echo "Rotation of logs  installed at $(LOGROTATE_CONF)"


vars: ## Show variables
	@echo OS: $(OS)
	@echo HOME: $(HOME)
	@echo VENV: $(VENV)
	@echo SCRIPT_PATH: $(SCRIPT_PATH)
	@echo PYTHON: $(PYTHON)
	@echo PIP: $(PIP)
	@echo PPROJECT_NAME: $(PROJECT_NAME)
	@echo LOG_CRON: $(LOG_CRON)
	@echo LOGROTATE_CONF: $(LOGROTATE_CONF)
	@echo LOGTMP: $(LOGTMP)


help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf ">  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
