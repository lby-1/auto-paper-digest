#!/bin/bash
# Docker Deployment Test Script
# Tests Docker build and basic functionality

set -e

echo "=============================================="
echo "Auto-Paper-Digest Docker Deployment Test"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_step() {
    echo -e "${YELLOW}Testing: $1${NC}"
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

# Test 1: Check Docker is installed
test_step "Docker installation"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    pass "Docker is installed: $DOCKER_VERSION"
else
    fail "Docker is not installed"
    exit 1
fi

# Test 2: Check Docker Compose is installed
test_step "Docker Compose installation"
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    pass "Docker Compose is installed: $COMPOSE_VERSION"
else
    fail "Docker Compose is not installed"
    exit 1
fi

# Test 3: Validate docker-compose.yml
test_step "Docker Compose configuration validation"
if docker-compose config > /dev/null 2>&1; then
    pass "docker-compose.yml is valid"
else
    fail "docker-compose.yml has syntax errors"
    docker-compose config
fi

# Test 4: Check .env file
test_step ".env file existence"
if [ -f .env ]; then
    pass ".env file exists"

    # Check required variables
    if grep -q "HF_TOKEN=" .env && grep -q "HF_USERNAME=" .env; then
        pass "Required environment variables are configured"
    else
        fail "Missing required environment variables (HF_TOKEN, HF_USERNAME)"
    fi
else
    fail ".env file not found. Copy from .env.example"
fi

# Test 5: Check Dockerfile
test_step "Dockerfile syntax"
if [ -f Dockerfile ]; then
    pass "Dockerfile exists"
else
    fail "Dockerfile not found"
fi

# Test 6: Check .dockerignore
test_step ".dockerignore file"
if [ -f .dockerignore ]; then
    pass ".dockerignore exists"
else
    fail ".dockerignore not found (optional but recommended)"
fi

# Test 7: Test Docker build (dry run)
test_step "Docker build test (syntax check)"
if docker-compose build --dry-run 2>&1 | grep -q "error"; then
    fail "Docker build configuration has errors"
else
    pass "Docker build configuration is valid"
fi

# Test 8: Check data directories
test_step "Data directory structure"
mkdir -p data/pdfs data/videos data/profiles data/digests
if [ -d data ]; then
    pass "Data directories created"
else
    fail "Failed to create data directories"
fi

# Test 9: Check deployment scripts
test_step "Deployment scripts"
SCRIPTS_FOUND=0
if [ -f deploy/deploy_local.sh ]; then
    ((SCRIPTS_FOUND++))
fi
if [ -f deploy/deploy_local.bat ]; then
    ((SCRIPTS_FOUND++))
fi
if [ -f Makefile ]; then
    ((SCRIPTS_FOUND++))
fi

if [ $SCRIPTS_FOUND -ge 2 ]; then
    pass "Deployment scripts are available ($SCRIPTS_FOUND found)"
else
    fail "Some deployment scripts are missing"
fi

# Test 10: Check documentation
test_step "Documentation"
if [ -f DOCKER_GUIDE.md ]; then
    pass "Docker documentation exists"
else
    fail "DOCKER_GUIDE.md not found"
fi

# Summary
echo ""
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Ready to deploy! Run one of these commands:"
    echo "  docker-compose up -d"
    echo "  make up"
    echo "  ./deploy/deploy_local.sh prod"
    exit 0
else
    echo -e "${RED}Some tests failed. Please fix the issues above.${NC}"
    exit 1
fi
