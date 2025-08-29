# Tests

This directory contains unit tests for the Hindsight AI service components.

## Running Tests

To run all tests:

```bash
cd apps/hindsight-service
pytest tests/
```

To run a specific test file:

```bash
pytest tests/test_pruning_service.py
```

To run tests with coverage:

```bash
pytest --cov=core tests/
```

## Test Structure

- `test_pruning_service.py` - Tests for the memory pruning functionality
- (Additional test files will be added as more components are tested)

## Prerequisites

Make sure you have the test dependencies installed:

```bash
pip install pytest pytest-cov
```

## Test Categories

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Focus on logic and edge cases

### Integration Tests
- Test interactions between components
- Database operations
- API endpoint testing

## Writing New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Use pytest framework
3. Mock external dependencies (database, LLM API calls)
4. Test both positive and negative cases
5. Include edge cases and error conditions
