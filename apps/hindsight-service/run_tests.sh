#!/bin/bash
set -euo pipefail

# Default configuration (mirrors CI with extra diagnostics for slow tests)
REBUILD=false
VERBOSE=false
RUN_SPECIFIC=""
UNIT_ONLY=false
INTEGRATION_ONLY=false
COVERAGE_MODE="default"  # valid: default, nocov, coverage

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

show_help() {
    cat <<'USAGE'
Usage: ./run_tests.sh [OPTIONS]

Run tests in a Docker container that matches the CI environment.

Options:
  -h, --help           Show this help message
  -r, --rebuild        Force rebuild of Docker image
  -v, --verbose        Increase pytest verbosity (prints every test)
  -t, --test TEST      Run a specific test (e.g. tests/unit/test_example.py::test_case)
  --unit               Run only unit tests
  --integration        Run only integration tests
  --no-cov             Disable coverage reporting
  --coverage           Enable coverage reporting (like CI tests.yml)

Examples:
  ./run_tests.sh                       # Run default suite (not e2e) with slow-test timings
  ./run_tests.sh --unit --no-cov       # Unit tests only without coverage
  ./run_tests.sh -t tests/unit/test_example.py::test_case
  ./run_tests.sh --rebuild             # Force rebuild image before running
USAGE
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
            if [[ $# -lt 2 ]]; then
                print_error "Missing argument for --test"
                exit 1
            fi
            RUN_SPECIFIC="$2"
            shift 2
            ;;
        --unit)
            UNIT_ONLY=true
            INTEGRATION_ONLY=false
            shift
            ;;
        --integration)
            INTEGRATION_ONLY=true
            UNIT_ONLY=false
            shift
            ;;
        --no-cov)
            COVERAGE_MODE="nocov"
            shift
            ;;
        --coverage)
            COVERAGE_MODE="coverage"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

quote_command() {
    local quoted=()
    for arg in "$@"; do
        quoted+=("$(printf '%q' "$arg")")
    done
    printf '%s' "${quoted[*]}"
}

PYTEST_CMD=(uv run --extra test pytest)
PYTEST_ARGS=(--maxfail=1 --durations=25)
PYTEST_TARGET=()
PYTEST_VERBOSITY="-vv"
if [[ "$VERBOSE" == true ]]; then
    PYTEST_VERBOSITY="-vvv"
fi
PYTEST_ARGS+=("$PYTEST_VERBOSITY")

if [[ -n "$RUN_SPECIFIC" ]]; then
    PYTEST_TARGET=("$RUN_SPECIFIC")
    if [[ "$COVERAGE_MODE" == "coverage" ]]; then
        PYTEST_ARGS+=(--cov=core --cov-report=term --cov-report=xml:coverage.xml)
    else
        PYTEST_ARGS+=(--no-cov)
    fi
else
    if [[ "$UNIT_ONLY" == true ]]; then
        PYTEST_TARGET=(tests/unit/)
    elif [[ "$INTEGRATION_ONLY" == true ]]; then
        PYTEST_TARGET=(tests/integration/)
    else
        PYTEST_ARGS+=(-m "not e2e")
    fi

    case "$COVERAGE_MODE" in
        coverage)
            PYTEST_ARGS+=(--cov=core --cov-report=term --cov-report=xml:coverage.xml)
            ;;
        nocov)
            PYTEST_ARGS+=(--no-cov)
            ;;
    esac
fi

FULL_CMD=("${PYTEST_CMD[@]}" "${PYTEST_ARGS[@]}")
if [[ ${#PYTEST_TARGET[@]} -gt 0 ]]; then
    FULL_CMD+=("${PYTEST_TARGET[@]}")
fi

TEST_COMMAND="$(quote_command "${FULL_CMD[@]}")"

cd "$(dirname "$0")"

if [[ -x "../../stop_hindsight.sh" ]]; then
    print_status "Stopping any running Hindsight services (to avoid interference)..."
    ../../stop_hindsight.sh || true
else
    print_warning "stop_hindsight.sh not found at repo root; skipping service stop."
fi

print_status "Running tests with command: $TEST_COMMAND"

IMAGE_EXISTS=$(docker images -q hindsight-service-test 2>/dev/null)
if [[ -z "$IMAGE_EXISTS" || "$REBUILD" == true ]]; then
    print_status "Building test Docker image..."
    print_cmd "docker build -f Dockerfile.test -t hindsight-service-test ."
    docker build -f Dockerfile.test -t hindsight-service-test .
else
    print_status "Using existing Docker image (use --rebuild to force rebuild)"
fi

print_status "Running tests in Docker container (matching CI environment)..."
print_cmd "docker run --rm -v $(pwd):/app -w /app hindsight-service-test $TEST_COMMAND"

docker run --rm \
    -v "$(pwd):/app" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -w /app \
    hindsight-service-test \
    /bin/bash -c "$TEST_COMMAND"

TEST_EXIT_CODE=$?

echo ""
if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    print_status "All tests passed! ✅"
else
    print_error "Tests failed with exit code $TEST_EXIT_CODE ❌"
    echo ""
    print_warning "This matches the exact CI environment. If tests pass here but fail in CI,"
    print_warning "the issue might be with CI configuration or environment variables."
fi

exit $TEST_EXIT_CODE
