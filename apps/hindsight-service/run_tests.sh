#!/bin/bash
set -euo pipefail

# Default values (matches CI exactly)
TEST_COMMAND="uv run --extra test pytest --maxfail=1 -q -m \"not e2e\""
REBUILD=false
VERBOSE=false
RUN_SPECIFIC=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_cmd() {
    echo -e "${BLUE}[CMD]${NC} $1"
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Run tests in a Docker container that matches the CI environment"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -r, --rebuild        Force rebuild of Docker image"
    echo "  -v, --verbose        Enable verbose output"
    echo "  -t, --test TEST      Run specific test (e.g., 'tests/unit/test_bulk_operations_planning.py::test_bulk_move_conflict_detection')"
    echo "  --unit               Run only unit tests"
    echo "  --integration        Run only integration tests"
    echo "  --no-cov             Disable coverage reporting
  --coverage           Enable coverage reporting (like CI tests.yml)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests (like CI)"
    echo "  $0 --unit --no-cov                   # Run only unit tests without coverage"
    echo "  $0 -t 'tests/unit/test_bulk_operations_planning.py::test_bulk_move_conflict_detection'"
    echo "  $0 --rebuild                         # Force rebuild image and run tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--test)
            RUN_SPECIFIC="$2"
            shift 2
            ;;
        --unit)
            TEST_COMMAND="uv run --extra test pytest tests/unit/ --maxfail=1 -q"
            shift
            ;;
        --integration)
            TEST_COMMAND="uv run --extra test pytest tests/integration/ --maxfail=1 -q"
            shift
            ;;
        --no-cov)
            TEST_COMMAND="${TEST_COMMAND/--maxfail=1 -q/--maxfail=1 -q --no-cov}"
            shift
            ;;
        --coverage)
            TEST_COMMAND="${TEST_COMMAND/-q/-q --cov=core --cov-report=term --cov-report=xml:coverage.xml}"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# If specific test is provided, modify command
if [ -n "$RUN_SPECIFIC" ]; then
    TEST_COMMAND="uv run --extra test pytest '$RUN_SPECIFIC' -v --no-cov"
fi

# If verbose, add -v flag
if [ "$VERBOSE" = true ] && [[ ! "$TEST_COMMAND" == *"-v"* ]]; then
    TEST_COMMAND="${TEST_COMMAND/-q/-v}"
fi

# Change to the hindsight-service directory
cd "$(dirname "$0")"

# Proactively stop any running Hindsight services to avoid E2E interference
if [ -x "../../stop_hindsight.sh" ]; then
    print_status "Stopping any running Hindsight services (to avoid interference)..."
    ../../stop_hindsight.sh || true
else
    print_warning "stop_hindsight.sh not found at repo root; skipping service stop."
fi

print_status "Running tests with command: $TEST_COMMAND"

# Check if image exists and rebuild if necessary
IMAGE_EXISTS=$(docker images -q hindsight-service-test 2> /dev/null)
if [ -z "$IMAGE_EXISTS" ] || [ "$REBUILD" = true ]; then
    print_status "Building test Docker image..."
    print_cmd "docker build -f Dockerfile.test -t hindsight-service-test ."
    docker build -f Dockerfile.test -t hindsight-service-test .
    
    if [ $? -ne 0 ]; then
        print_error "Failed to build Docker image"
        exit 1
    fi
else
    print_status "Using existing Docker image (use --rebuild to force rebuild)"
fi

print_status "Running tests in Docker container (matching CI environment)..."
print_cmd "docker run --rm -v $(pwd):/app -w /app hindsight-service-test $TEST_COMMAND"

# Run tests with the specified command
# Mount the current directory to preserve any test artifacts
# Mount Docker socket to enable testcontainers to work
docker run --rm \
    -v "$(pwd):/app" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -w /app \
    hindsight-service-test \
    /bin/bash -c "$TEST_COMMAND"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status "All tests passed! ✅"
else
    print_error "Tests failed with exit code $TEST_EXIT_CODE ❌"
    echo ""
    print_warning "This matches the exact CI environment. If tests pass here but fail in CI,"
    print_warning "the issue might be with CI configuration or environment variables."
fi

exit $TEST_EXIT_CODE
