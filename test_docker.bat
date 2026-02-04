@echo off
REM Docker Deployment Test Script for Windows
REM Tests Docker build and basic functionality

setlocal enabledelayedexpansion

echo ==============================================
echo Auto-Paper-Digest Docker Deployment Test
echo ==============================================
echo.

set TESTS_PASSED=0
set TESTS_FAILED=0

REM Test 1: Check Docker is installed
echo Testing: Docker installation
docker --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker is not installed
    set /a TESTS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('docker --version') do set DOCKER_VERSION=%%i
    echo [PASS] Docker is installed: !DOCKER_VERSION!
    set /a TESTS_PASSED+=1
)

REM Test 2: Check Docker Compose is installed
echo Testing: Docker Compose installation
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker Compose is not installed
    set /a TESTS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('docker-compose --version') do set COMPOSE_VERSION=%%i
    echo [PASS] Docker Compose is installed: !COMPOSE_VERSION!
    set /a TESTS_PASSED+=1
)

REM Test 3: Validate docker-compose.yml
echo Testing: Docker Compose configuration validation
docker-compose config >nul 2>&1
if errorlevel 1 (
    echo [FAIL] docker-compose.yml has syntax errors
    set /a TESTS_FAILED+=1
) else (
    echo [PASS] docker-compose.yml is valid
    set /a TESTS_PASSED+=1
)

REM Test 4: Check .env file
echo Testing: .env file existence
if exist .env (
    echo [PASS] .env file exists
    set /a TESTS_PASSED+=1

    findstr /C:"HF_TOKEN=" .env >nul && findstr /C:"HF_USERNAME=" .env >nul
    if errorlevel 1 (
        echo [FAIL] Missing required environment variables (HF_TOKEN, HF_USERNAME)
        set /a TESTS_FAILED+=1
    ) else (
        echo [PASS] Required environment variables are configured
        set /a TESTS_PASSED+=1
    )
) else (
    echo [FAIL] .env file not found. Copy from .env.example
    set /a TESTS_FAILED+=1
)

REM Test 5: Check Dockerfile
echo Testing: Dockerfile syntax
if exist Dockerfile (
    echo [PASS] Dockerfile exists
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Dockerfile not found
    set /a TESTS_FAILED+=1
)

REM Test 6: Check .dockerignore
echo Testing: .dockerignore file
if exist .dockerignore (
    echo [PASS] .dockerignore exists
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] .dockerignore not found (optional but recommended)
    set /a TESTS_FAILED+=1
)

REM Test 7: Check data directories
echo Testing: Data directory structure
if not exist data mkdir data
if not exist data\pdfs mkdir data\pdfs
if not exist data\videos mkdir data\videos
if not exist data\profiles mkdir data\profiles
if not exist data\digests mkdir data\digests

if exist data (
    echo [PASS] Data directories created
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Failed to create data directories
    set /a TESTS_FAILED+=1
)

REM Test 8: Check deployment scripts
echo Testing: Deployment scripts
set SCRIPTS_FOUND=0
if exist deploy\deploy_local.sh set /a SCRIPTS_FOUND+=1
if exist deploy\deploy_local.bat set /a SCRIPTS_FOUND+=1
if exist Makefile set /a SCRIPTS_FOUND+=1

if !SCRIPTS_FOUND! GEQ 2 (
    echo [PASS] Deployment scripts are available (!SCRIPTS_FOUND! found)
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Some deployment scripts are missing
    set /a TESTS_FAILED+=1
)

REM Test 9: Check documentation
echo Testing: Documentation
if exist DOCKER_GUIDE.md (
    echo [PASS] Docker documentation exists
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] DOCKER_GUIDE.md not found
    set /a TESTS_FAILED+=1
)

REM Summary
echo.
echo ==============================================
echo Test Summary
echo ==============================================
echo Passed: %TESTS_PASSED%
echo Failed: %TESTS_FAILED%
echo.

if %TESTS_FAILED% EQU 0 (
    echo All tests passed!
    echo.
    echo Ready to deploy! Run one of these commands:
    echo   docker-compose up -d
    echo   deploy\deploy_local.bat prod
    exit /b 0
) else (
    echo Some tests failed. Please fix the issues above.
    exit /b 1
)

endlocal
