# IRD-AI OS — Air-Gapped Deployment Makefile
# Target: full stack running within 15 minutes on an offline machine.
#
# Workflow (internet-connected machine):
#   make airgap-save          → export images to .airgap-images/*.tar
#   make airgap-bundle        → zip images + repo for transport
#
# Workflow (air-gapped machine):
#   make airgap-load          → load images from .airgap-images/*.tar
#   cp .env.airgap .env       → set passwords (edit before first run)
#   make airgap-up            → start all services (~5 min first boot)
#   make airgap-check         → verify health

COMPOSE_FILE        := docker-compose.airgap.yml
COMPOSE_PROD        := docker-compose.yml
IMAGE_DIR           := .airgap-images
BUNDLE_NAME         := ird-ai-airgap-bundle.tar.gz

# Pinned versions matching docker-compose.airgap.yml
INFRA_IMAGES := \
  postgres:16-alpine \
  redis:7-alpine \
  qdrant/qdrant:v1.9.2 \
  neo4j:5.19-community \
  ollama/ollama:0.1.44

.PHONY: help airgap-save airgap-load airgap-check airgap-up airgap-down \
        airgap-logs airgap-bundle dev-up dev-down test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Air-Gap preparation (run on internet-connected machine) ──────────────────

airgap-save: ## Pull and save all images as tarballs for offline transport
	mkdir -p $(IMAGE_DIR)
	@echo "→ Pulling and saving $(words $(INFRA_IMAGES)) infrastructure images..."
	@for img in $(INFRA_IMAGES); do \
	  safe=$$(echo $$img | tr '/:' '__'); \
	  echo "  Saving $$img → $(IMAGE_DIR)/$$safe.tar"; \
	  docker pull $$img && docker save $$img -o $(IMAGE_DIR)/$$safe.tar; \
	done
	@echo "→ Building API image..."
	docker build -t ird-ai-api:0.9.0 .
	docker save ird-ai-api:0.9.0 -o $(IMAGE_DIR)/ird-ai-api__0.9.0.tar
	@echo "✓ All images saved to $(IMAGE_DIR)/"

airgap-bundle: airgap-save ## Create a single archive for transport (images + source)
	tar -czf $(BUNDLE_NAME) \
	  --exclude='.git' \
	  --exclude='__pycache__' \
	  --exclude='.venv' \
	  --exclude='*.pyc' \
	  $(IMAGE_DIR) \
	  .
	@echo "✓ Bundle ready: $(BUNDLE_NAME)"
	@echo "  Size: $$(du -sh $(BUNDLE_NAME) | cut -f1)"

# ── Air-Gap deployment (run on offline machine) ──────────────────────────────

airgap-load: ## Load pre-saved image tarballs into local Docker daemon
	@echo "→ Loading images from $(IMAGE_DIR)/"
	@for f in $(IMAGE_DIR)/*.tar; do \
	  echo "  Loading $$f..."; \
	  docker load -i $$f; \
	done
	@echo "✓ All images loaded."

airgap-check: ## Verify all required images are available locally
	@bash scripts/airgap-preflight.sh

airgap-up: airgap-check ## Start the full air-gapped stack (waits for health)
	@if [ ! -f .env ]; then \
	  echo "⚠ No .env file found. Copying .env.airgap template..."; \
	  cp .env.airgap .env 2>/dev/null || echo "  (no .env.airgap template — using defaults)"; \
	fi
	docker compose -f $(COMPOSE_FILE) up -d --build
	@echo ""
	@echo "✓ IRD-AI stack starting. Waiting for services..."
	@sleep 5
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "  API:    http://localhost:8000"
	@echo "  Health: http://localhost:8000/health"
	@echo "  Audit:  http://localhost:8000/audit/system-manifest"

airgap-down: ## Stop the air-gapped stack (preserves volumes)
	docker compose -f $(COMPOSE_FILE) down

airgap-destroy: ## Stop and remove ALL data volumes (destructive)
	@echo "⚠ This will delete all data. Press Ctrl+C to cancel..."
	@sleep 5
	docker compose -f $(COMPOSE_FILE) down -v

airgap-logs: ## Stream logs from all services
	docker compose -f $(COMPOSE_FILE) logs -f

airgap-status: ## Show running service health
	docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "API not yet ready"

# ── Development ──────────────────────────────────────────────────────────────

dev-up: ## Start development stack (with Prometheus + Jaeger)
	docker compose -f $(COMPOSE_PROD) up -d

dev-down: ## Stop development stack
	docker compose -f $(COMPOSE_PROD) down

# ── Quality ──────────────────────────────────────────────────────────────────

test: ## Run test suite (excludes Docker-dependent integration tests)
	python -m pytest tests/ -q \
	  --ignore=tests/test_infrastructure.py \
	  --ignore=tests/memory \
	  --ignore=tests/integration

lint: ## Run ruff linter
	python -m ruff check .
