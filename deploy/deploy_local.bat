@echo off
REM Auto-Paper-Digest Local Deployment Script for Windows
REM Usage: deploy_local.bat [mode]
REM Modes: dev, prod

setlocal

set MODE=%1
if "%MODE%"=="" set MODE=prod

echo ===================================================
echo Auto-Paper-Digest Local Deployment
echo ===================================================
echo Mode: %MODE%
echo ===================================================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed
    echo Please install Docker Desktop from https://www.docker.com/get-started
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker Compose is not installed
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    if exist .env.example (
        copy .env.example .env
        echo Please edit .env file with your credentials before continuing
        exit /b 1
    ) else (
        echo Error: .env.example not found
        exit /b 1
    )
)

REM Build and start services
if "%MODE%"=="dev" (
    echo Starting in development mode...
    docker-compose -f docker-compose.dev.yml up --build -d
    echo.
    echo ===================================================
    echo Development environment started!
    echo ===================================================
    echo Shell: docker-compose -f docker-compose.dev.yml exec apd-dev bash
    echo Portal: http://localhost:7860
    echo Logs: docker-compose -f docker-compose.dev.yml logs -f
    echo Stop: docker-compose -f docker-compose.dev.yml down
    echo ===================================================
) else (
    echo Starting in production mode...
    docker-compose up --build -d
    echo.
    echo ===================================================
    echo Production environment started!
    echo ===================================================
    echo Portal: http://localhost:7860
    echo Logs: docker-compose logs -f
    echo Stop: docker-compose down
    echo.
    echo Services running:
    docker-compose ps
    echo ===================================================
)

endlocal
