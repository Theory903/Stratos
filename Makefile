.PHONY: help dev stop lint test build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ──
dev: ## Start all infrastructure services
	docker compose up -d postgres redis kafka minio

stop: ## Stop all services
	docker compose down

# ── Lint ──
lint-python: ## Lint Python services
	cd data-fabric && ruff check src/ tests/
	cd ml && ruff check src/ tests/
	cd nlp && ruff check src/ tests/
	cd orchestrator && ruff check src/ tests/

lint-rust: ## Lint Rust engines
	cd engines/rust && cargo clippy --all-targets -- -D warnings

lint-java: ## Lint Java engines
	cd engines/java && mvn spotless:check

lint-ts: ## Lint frontend
	cd frontend && npm run lint

lint: lint-python lint-rust lint-java lint-ts ## Lint all

# ── Test ──
test-python: ## Test Python services
	cd data-fabric && pytest tests/ -v
	cd ml && pytest tests/ -v
	cd nlp && pytest tests/ -v
	cd orchestrator && pytest tests/ -v

test-rust: ## Test Rust engines
	cd engines/rust && cargo test --all

test-java: ## Test Java engines
	cd engines/java && mvn test

test-ts: ## Test frontend
	cd frontend && npm test

test: test-python test-rust test-java test-ts ## Test all

# ── Build ──
build: ## Build all Docker images
	docker compose build

# ── Database ──
migrate: ## Run database migrations
	cd data-fabric && alembic upgrade head

seed: ## Seed development data
	bash infra/scripts/seed-data.sh
