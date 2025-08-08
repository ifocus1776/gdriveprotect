#!/bin/bash

# CI/CD Test Script for GDriveProtect
# This script runs comprehensive tests for the API endpoints

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="gdriveprotect-test"
IMAGE_NAME="gdriveprotect"
PORT=5000
TIMEOUT=60
MAX_RETRIES=5

echo -e "${BLUE}🚀 Starting CI/CD Test Suite for GDriveProtect${NC}"
echo "=================================================="

# Function to cleanup containers
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up containers...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
}

# Function to check if port is available
check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${RED}❌ Port $PORT is already in use${NC}"
        echo "Please stop any existing containers or services using port $PORT"
        exit 1
    fi
}

# Function to wait for container to be ready
wait_for_container() {
    echo -e "${YELLOW}⏳ Waiting for container to be ready...${NC}"
    
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:$PORT/api/dlp/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Container is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Container not ready yet (attempt $((retries + 1))/$MAX_RETRIES)${NC}"
        sleep 10
        retries=$((retries + 1))
    done
    
    echo -e "${RED}❌ Container failed to start within timeout${NC}"
    return 1
}

# Function to run tests
run_tests() {
    echo -e "${BLUE}🧪 Running API tests...${NC}"
    
    # Install test dependencies if needed
    if ! python3 -c "import requests" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
        pip3 install requests
    fi
    
    # Run the test suite
    python3 tests/test_api_endpoints.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        return 1
    fi
}

# Function to check Docker image
check_docker_image() {
    echo -e "${BLUE}🐳 Checking Docker image...${NC}"
    
    if ! docker images | grep -q $IMAGE_NAME; then
        echo -e "${YELLOW}📦 Building Docker image...${NC}"
        docker build -t $IMAGE_NAME .
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Docker build failed${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Docker image exists${NC}"
    fi
}

# Function to run container
start_container() {
    echo -e "${BLUE}🚀 Starting test container...${NC}"
    
    # Start container in background
    docker run -d \
        --name $CONTAINER_NAME \
        -p $PORT:5000 \
        -e GOOGLE_CLOUD_PROJECT=ifocus-innovations \
        $IMAGE_NAME
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to start container${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Container started${NC}"
}

# Function to check container logs
check_logs() {
    echo -e "${BLUE}📋 Container logs:${NC}"
    docker logs $CONTAINER_NAME --tail 20
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}⚡ Running performance tests...${NC}"
    
    # Test response times
    local endpoints=(
        "/api/dlp/health"
        "/api/drive/health"
        "/api/vault/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        echo -n "Testing $endpoint: "
        start_time=$(date +%s.%N)
        response=$(curl -s -w "%{http_code}" http://localhost:$PORT$endpoint -o /dev/null)
        end_time=$(date +%s.%N)
        
        duration=$(echo "$end_time - $start_time" | bc)
        
        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✅ ${duration}s${NC}"
        else
            echo -e "${RED}❌ HTTP $response${NC}"
        fi
    done
}

# Function to run security tests
run_security_tests() {
    echo -e "${BLUE}🔒 Running security tests...${NC}"
    
    # Test for common security headers
    local security_headers=(
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
    )
    
    response=$(curl -s -I http://localhost:$PORT/api/dlp/health)
    
    for header in "${security_headers[@]}"; do
        if echo "$response" | grep -q "$header"; then
            echo -e "${GREEN}✅ $header header present${NC}"
        else
            echo -e "${YELLOW}⚠️  $header header missing${NC}"
        fi
    done
}

# Main execution
main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Check port availability
    check_port
    
    # Check Docker image
    check_docker_image
    
    # Start container
    start_container
    
    # Wait for container to be ready
    if ! wait_for_container; then
        check_logs
        exit 1
    fi
    
    # Run tests
    if ! run_tests; then
        check_logs
        exit 1
    fi
    
    # Run performance tests
    run_performance_tests
    
    # Run security tests
    run_security_tests
    
    echo -e "${GREEN}🎉 All CI/CD tests completed successfully!${NC}"
}

# Run main function
main "$@"
