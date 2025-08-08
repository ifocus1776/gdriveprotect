#!/bin/bash

# Quick Test Runner for GDriveProtect
# This script provides easy testing options

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 GDriveProtect Test Runner${NC}"
echo "================================"

# Function to check if container is running
check_container() {
    if curl -s http://localhost:5000/api/dlp/health >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start container
start_container() {
    echo -e "${YELLOW}🚀 Starting container...${NC}"
    docker run -d \
        --name gdriveprotect-test \
        -p 5000:5000 \
        -e GOOGLE_CLOUD_PROJECT=ifocus-innovations \
        gdriveprotect
    
    echo -e "${YELLOW}⏳ Waiting for container to be ready...${NC}"
    timeout 60 bash -c 'until curl -s http://localhost:5000/api/dlp/health; do sleep 5; done'
    echo -e "${GREEN}✅ Container is ready!${NC}"
}

# Function to run quick tests
quick_test() {
    echo -e "${BLUE}🔍 Running quick health checks...${NC}"
    
    endpoints=(
        "/api/dlp/health"
        "/api/drive/health"
        "/api/vault/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        echo -n "Testing $endpoint: "
        if curl -s "http://localhost:5000$endpoint" >/dev/null; then
            echo -e "${GREEN}✅ OK${NC}"
        else
            echo -e "${RED}❌ FAIL${NC}"
        fi
    done
}

# Function to run full test suite
full_test() {
    echo -e "${BLUE}🧪 Running full test suite...${NC}"
    
    if ! python3 -c "import requests" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing requests...${NC}"
        pip3 install requests
    fi
    
    python3 tests/test_api_endpoints.py
}

# Function to run performance test
performance_test() {
    echo -e "${BLUE}⚡ Running performance test...${NC}"
    
    for i in {1..5}; do
        echo "Test $i:"
        for endpoint in "/api/dlp/health" "/api/drive/health" "/api/vault/health"; do
            echo -n "  $endpoint: "
            start_time=$(date +%s.%N)
            curl -s "http://localhost:5000$endpoint" >/dev/null
            end_time=$(date +%s.%N)
            duration=$(echo "$end_time - $start_time" | bc -l)
            echo -e "${GREEN}${duration}s${NC}"
        done
        echo
    done
}

# Function to cleanup
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    docker stop gdriveprotect-test 2>/dev/null || true
    docker rm gdriveprotect-test 2>/dev/null || true
}

# Main menu
case "${1:-help}" in
    "start")
        cleanup
        start_container
        echo -e "${GREEN}✅ Container started and ready for testing!${NC}"
        echo "Run './run_tests.sh quick' to test endpoints"
        ;;
    "quick")
        if ! check_container; then
            echo -e "${RED}❌ Container not running. Run './run_tests.sh start' first${NC}"
            exit 1
        fi
        quick_test
        ;;
    "full")
        if ! check_container; then
            echo -e "${RED}❌ Container not running. Run './run_tests.sh start' first${NC}"
            exit 1
        fi
        full_test
        ;;
    "perf")
        if ! check_container; then
            echo -e "${RED}❌ Container not running. Run './run_tests.sh start' first${NC}"
            exit 1
        fi
        performance_test
        ;;
    "stop")
        cleanup
        echo -e "${GREEN}✅ Container stopped${NC}"
        ;;
    "restart")
        cleanup
        start_container
        quick_test
        ;;
    "ci")
        echo -e "${BLUE}🚀 Running CI/CD test suite...${NC}"
        bash scripts/ci_test.sh
        ;;
    *)
        echo "Usage: $0 {start|quick|full|perf|stop|restart|ci}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the test container"
        echo "  quick   - Run quick health checks"
        echo "  full    - Run full test suite"
        echo "  perf    - Run performance tests"
        echo "  stop    - Stop the test container"
        echo "  restart - Restart container and run quick tests"
        echo "  ci      - Run full CI/CD test suite"
        echo ""
        echo "Example:"
        echo "  ./run_tests.sh start"
        echo "  ./run_tests.sh quick"
        echo "  ./run_tests.sh stop"
        ;;
esac
