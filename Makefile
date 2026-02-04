.PHONY: help build up down logs shell test clean dev-up dev-down dev-shell

# Default target
help:
	@echo "Auto-Paper-Digest Docker Commands"
	@echo "=================================="
	@echo "Production:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs"
	@echo "  make shell       - Open shell in APD container"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up      - Start development environment"
	@echo "  make dev-down    - Stop development environment"
	@echo "  make dev-shell   - Open shell in dev container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean up Docker resources"
	@echo "  make rebuild     - Rebuild and restart"

# Production commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started! Portal: http://localhost:7860"

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec apd bash

restart:
	docker-compose restart

rebuild: down build up

# Development commands
dev-up:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Dev environment started! Portal: http://localhost:7860"

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-shell:
	docker-compose -f docker-compose.dev.yml exec apd-dev bash

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Testing
test:
	docker-compose exec apd pytest tests/

# Maintenance
clean:
	docker-compose down -v
	docker system prune -f

ps:
	docker-compose ps

# Quick commands
status: ps

stop: down

start: up
