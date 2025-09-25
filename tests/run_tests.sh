#!/bin/bash

# Test runner script for Ontology Chat

echo "🧪 Ontology Chat Test Suite Runner"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests with specific markers
run_test_suite() {
    local marker=$1
    local description=$2

    echo -e "\n${YELLOW}Running ${description}...${NC}"

    if [ "$marker" = "all" ]; then
        pytest -v --tb=short
    else
        pytest -v -m "$marker" --tb=short
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${description} passed${NC}"
    else
        echo -e "${RED}❌ ${description} failed${NC}"
        return 1
    fi
}

# Parse command line arguments
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    unit)
        run_test_suite "unit" "Unit Tests"
        ;;
    integration)
        run_test_suite "integration" "Integration Tests"
        ;;
    performance)
        run_test_suite "performance" "Performance Tests"
        ;;
    slow)
        run_test_suite "slow" "Slow Tests"
        ;;
    coverage)
        echo -e "${YELLOW}Running tests with coverage report...${NC}"
        pytest --cov=api --cov-report=term-missing --cov-report=html
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    quick)
        echo -e "${YELLOW}Running quick tests (excluding slow)...${NC}"
        pytest -v -m "not slow and not performance" --tb=short
        ;;
    all)
        run_test_suite "all" "All Tests"
        ;;
    *)
        echo "Usage: $0 [unit|integration|performance|slow|coverage|quick|all]"
        echo ""
        echo "Options:"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests only"
        echo "  performance  - Run performance benchmarks"
        echo "  slow         - Run slow tests only"
        echo "  coverage     - Run all tests with coverage report"
        echo "  quick        - Run all tests except slow and performance"
        echo "  all          - Run all tests (default)"
        exit 1
        ;;
esac

# Generate summary
echo -e "\n${YELLOW}Test Summary:${NC}"
echo "=================================="

# Check if pytest-html is installed for HTML reports
if pip show pytest-html > /dev/null 2>&1; then
    echo -e "${YELLOW}Generating HTML report...${NC}"
    pytest --html=tests/reports/report.html --self-contained-html
    echo -e "${GREEN}HTML report available at tests/reports/report.html${NC}"
fi

echo -e "\n${GREEN}✅ Test suite execution completed!${NC}"