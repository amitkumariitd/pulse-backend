# Makefile for pulse-backend
# Provides convenient shortcuts for Docker operations

.PHONY: help build up down logs test clean restart shell db-shell

# Docker compose file paths
DOCKER_DIR := deployment/docker
COMPOSE_FILE := $(DOCKER_DIR)/docker-compose.yml
COMPOSE_TEST_FILE := $(DOCKER_DIR)/docker-compose.test.yml
COMPOSE_FLAGS := --project-directory . -f

# Default target
help:
	@echo "Pulse Backend - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make up          - Start all services (app + database)"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View application logs"
	@echo "  make build       - Build Docker images"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests in Docker"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make test-int    - Run integration tests only"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make db-reset    - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Utilities:"
	@echo "  make shell       - Open shell in app container"
	@echo "  make clean       - Remove all containers and volumes"
	@echo "  make ps          - Show running containers"
	@echo ""

# Development commands
up:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) up -d
	@echo "Services started. Access app at http://localhost:8000/health"

down:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) down

restart:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) restart

logs:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) logs -f app

build:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) build

# Testing commands
test:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) up --abort-on-container-exit --remove-orphans
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) down -v

test-unit:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) run --rm test python -m pytest tests/unit/ -v
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) down -v

test-int:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) run --rm test python -m pytest tests/integration/ -v
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) down -v

# Database commands
db-shell:
	docker exec -it pulse-postgres psql -U pulse -d pulse

db-reset:
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) down -v; \
		docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) up -d postgres; \
		echo "Database reset complete"; \
	fi

# Utility commands
shell:
	docker exec -it pulse-backend /bin/bash

clean:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) down -v --remove-orphans
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_TEST_FILE) down -v --remove-orphans
	@echo "All containers and volumes removed"

ps:
	docker-compose $(COMPOSE_FLAGS) $(COMPOSE_FILE) ps

# Production build
prod-build:
	docker build -t pulse-backend:latest --target production -f $(DOCKER_DIR)/Dockerfile .

# Run production container locally
prod-run:
	docker run -d \
		-p 8000:8000 \
		-e ENVIRONMENT=local \
		-e PULSE_DB_HOST=host.docker.internal \
		-e PULSE_DB_PASSWORD=changeme \
		--name pulse-backend-prod \
		pulse-backend:latest
	@echo "Production container started at http://localhost:8000"

prod-stop:
	docker stop pulse-backend-prod || true
	docker rm pulse-backend-prod || true

