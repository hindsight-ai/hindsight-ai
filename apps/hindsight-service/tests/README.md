# Tests

This directory contains tests for the Hindsight AI service organized by test type and feature.

## Test Structure

### Unit Tests (`tests/unit/`)
Fast, isolated unit tests with mocks and no database dependencies.
- `test_search_service.py` - Search service logic tests
- `test_pruning_service.py` - Pruning service with database
- `test_pruning_service_mock.py` - Pruning service with mocks
- `test_compression_service.py` - Compression service tests

### Integration Tests (`tests/integration/`)
Tests that use the database and test component interactions.

#### By Feature:
- **agents/** - Agent creation, updates, permissions
- **memory_blocks/** - Memory block CRUD and operations
- **bulk_operations/** - Bulk operations functionality
- **organizations/** - Organization management and memberships
- **keywords/** - Keyword extraction and management
- **search/** - Search functionality and endpoints
- **permissions/** - Authentication and authorization

### End-to-End Tests (`tests/e2e/`)
Full system tests with external dependencies (PostgreSQL, migrations).

### Shared Fixtures (`tests/fixtures/`)
- `conftest.py` - Global test fixtures and database setup
- Helper functions and test data factories

## Running Tests

```bash
cd apps/hindsight-service

# Run all tests
pytest tests/

# Run specific test types
pytest tests/unit/ -m unit
pytest tests/integration/ -m integration
pytest tests/e2e/ -m e2e

# Run tests for specific features
pytest tests/integration/agents/
pytest tests/integration/memory_blocks/

# Run with coverage
pytest --cov=core tests/
```

## Test Categories

- **unit**: Fast unit tests with mocks, no database
- **integration**: Tests with database interactions
- **e2e**: End-to-end tests requiring external services
- **slow**: Tests that take longer than 1 second

## Adding New Tests

1. **Unit tests**: Add to `tests/unit/` if they use mocks and don't need database
2. **Integration tests**: Add to appropriate feature directory under `tests/integration/`
3. **E2E tests**: Add to `tests/e2e/` for full system tests

## Fixtures

Global fixtures are defined in `tests/fixtures/conftest.py`:
- `db_session`: Database session for integration tests
- Database setup and teardown
- Common test data helpers

## Writing New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Use pytest framework
3. Mock external dependencies (database, LLM API calls)
4. Test both positive and negative cases
5. Include edge cases and error conditions
