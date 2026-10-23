# Shortcuts for the common workflows. Run `make` (or `make help`) to list them.
# Plain POSIX make: works with the GNU Make 3.81 that ships with macOS.

API_URL    ?= http://localhost:8000
ADMIN_ID   ?= R-101
CSV        ?= candidates_import.csv
COMPOSE    ?= docker compose

.DEFAULT_GOAL := help
.PHONY: help up down reset logs ps import install db migrate api web test e2e test-all

help: ## List the available commands
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

# --- Full stack (Docker only) ------------------------------------------------

up: ## Build and start db, api and web in the background
	$(COMPOSE) up -d --build --wait
	@echo "UI: http://localhost:5173  API: $(API_URL)  Postgres: localhost:5433"

down: ## Stop the stack (keeps the database volume)
	$(COMPOSE) down

reset: ## Stop the stack and DELETE the database volume
	$(COMPOSE) down -v

logs: ## Follow the logs of every service
	$(COMPOSE) logs -f

ps: ## Show the stack's containers
	$(COMPOSE) ps

import: ## Import the CSV as the Admin and print the Import Report
	@curl -sS --fail-with-body --retry 30 --retry-connrefused --retry-delay 1 \
		-X POST $(API_URL)/api/v1/candidates/import \
		-H "X-Recruiter-Id: $(ADMIN_ID)" -F file=@$(CSV) | python3 -m json.tool

# --- Local development -------------------------------------------------------

install: ## Install backend, frontend and Playwright browser dependencies
	cd backend && uv sync
	cd backend && uv run playwright install chromium
	cd frontend && npm ci

db: ## Start only Postgres (localhost:5433)
	$(COMPOSE) up -d --wait db

migrate: db ## Apply the migrations to the dev database
	cd backend && uv run alembic upgrade head

api: migrate ## Run the API locally with reload on :8000
	cd backend && uv run uvicorn --factory app.main:create_app --reload

web: ## Run the Vite dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev

# --- Tests -------------------------------------------------------------------

test: db ## Run the default suite (unit, API integration, RLS)
	cd backend && uv run pytest

e2e: up ## Run the Playwright e2e suite against the running stack
	cd backend && uv run playwright install chromium
	cd backend && uv run pytest -m e2e

test-all: test e2e ## Run the default suite, then the e2e suite
