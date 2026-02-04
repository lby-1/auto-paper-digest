#!/bin/bash
# Local Docker Deployment Script
# Usage: ./deploy_local.sh [mode]
# Modes: dev, prod

set -e

MODE=${1:-prod}

echo "==================================================="
echo "Auto-Paper-Digest Local Deployment"
echo "==================================================="
echo "Mode: $MODE"
echo "==================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    echo "Please install Docker Compose"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Please edit .env file with your credentials before continuing"
        exit 1
    else
        echo "Error: .env.example not found"
        exit 1
    fi
fi

# Build and start services
if [ "$MODE" = "dev" ]; then
    echo "Starting in development mode..."
    docker-compose -f docker-compose.dev.yml up --build -d
    echo ""
    echo "==================================================="
    echo "Development environment started!"
    echo "==================================================="
    echo "Shell: docker-compose -f docker-compose.dev.yml exec apd-dev bash"
    echo "Portal: http://localhost:7860"
    echo "Logs: docker-compose -f docker-compose.dev.yml logs -f"
    echo "Stop: docker-compose -f docker-compose.dev.yml down"
    echo "==================================================="
else
    echo "Starting in production mode..."
    docker-compose up --build -d
    echo ""
    echo "==================================================="
    echo "Production environment started!"
    echo "==================================================="
    echo "Portal: http://localhost:7860"
    echo "Logs: docker-compose logs -f"
    echo "Stop: docker-compose down"
    echo ""
    echo "Services running:"
    docker-compose ps
    echo "==================================================="
fi
