# Hindsight Dashboard E2E Tests

This directory contains end-to-end tests for the Hindsight Dashboard using Playwright.

## Prerequisites

Before running the tests, ensure that:

1. **Hindsight Services are Running**: All services must be running in the background:
   - Backend API (hindsight-service)
   - Database (PostgreSQL)
   - Dashboard (React app at http://localhost:3000)

2. **Test Data**: The database should contain sufficient test data:
   - Minimum 50 memory blocks for comprehensive pagination testing
   - Various memory block types and statuses
   - Test user accounts if authentication is enabled

3. **Node.js Dependencies**: Install dependencies:
   ```bash
   cd apps/hindsight-dashboard
   npm install
   ```

## Running the Tests

### Install Playwright Browsers
```bash
npx playwright install
```

### Run All Tests
```bash
npm run test:e2e
```

### Run Tests in Headed Mode (visible browser)
```bash
npm run test:e2e:headed
```

### Run Tests in Debug Mode
```bash
npm run test:e2e:debug
```

### Run Tests with UI Mode
```bash
npm run test:e2e:ui
```

### Run Specific Test File
```bash
npx playwright test pagination.spec.js
```

### Run Tests in Specific Browser
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Test Structure

### pagination.spec.js
Comprehensive test suite for memory block pagination functionality covering:

- **TC-MEM-001-01**: Pagination controls display correctly
- **TC-MEM-001-02**: Page navigation works in all directions (First, Previous, Next, Last)
- **TC-MEM-001-03**: Page size selection (10, 25, 50, 100 items per page)
- **TC-MEM-001-04**: Current page indicator accuracy
- **TC-MEM-001-05**: Pagination with filtered results
- **TC-MEM-001-06**: Pagination state persistence across interactions
- **TC-MEM-001-07**: Column resizing compatibility with pagination
- **TC-MEM-001-08**: Performance with large datasets
- **TC-MEM-001-09**: Data integrity during pagination (no data loss)
- **TC-MEM-001-10**: Responsive design on mobile devices
- **TC-MEM-001-11**: Keyboard navigation support
- **TC-MEM-001-12**: Error handling during pagination

## Test Configuration

The tests are configured in `playwright.config.js` with:

- **Base URL**: `http://localhost:3000`
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari
- **Parallel Execution**: Fully parallel for faster test runs
- **Retries**: 2 retries on CI, 0 in development
- **Timeouts**: 10-second timeout for page loads
- **Tracing**: Automatic trace collection on first retry

## Test Data Requirements

For optimal test coverage, ensure your test database contains:

### Memory Blocks
- **Minimum Count**: 50+ memory blocks
- **Content Variety**: Different lessons learned, errors, keywords
- **Date Range**: Spread across multiple months for date filtering
- **Agent Distribution**: Multiple agents with associated memory blocks
- **Status Variety**: Mix of active and archived memory blocks

### Sample Data Structure
```sql
-- Example memory blocks for testing
INSERT INTO memory_blocks (id, content, lessons_learned, agent_id, created_at) VALUES
('test-001', 'Test content 1', 'Lesson 1', 'agent-1', NOW() - INTERVAL '30 days'),
('test-002', 'Test content 2', 'Lesson 2', 'agent-1', NOW() - INTERVAL '20 days'),
-- ... more test data
```

## Troubleshooting

### Common Issues

1. **Tests Fail Due to Missing Data**
   - Ensure database has sufficient test data
   - Check that memory blocks are properly seeded

2. **Page Load Timeouts**
   - Verify all services are running
   - Check network connectivity
   - Increase timeout in playwright.config.js if needed

3. **Authentication Issues**
   - Ensure authentication is properly configured
   - Check if test user credentials are valid

4. **Browser Launch Failures**
   - Run `npx playwright install` to install browsers
   - Check system resources (memory, disk space)

### Debug Mode
Use debug mode to step through tests:
```bash
npm run test:e2e:debug
```

### Visual Debugging
Use UI mode to see test execution:
```bash
npm run test:e2e:ui
```

## Test Reports

Test results are generated in the `test-results/` directory with:
- HTML reports with screenshots
- Trace files for debugging
- Video recordings of failed tests

## CI/CD Integration

For CI/CD pipelines, add these commands:

```yaml
# GitHub Actions example
- name: Install Playwright
  run: npx playwright install

- name: Run E2E Tests
  run: npm run test:e2e
  env:
    CI: true
```

## Extending Tests

### Adding New Test Cases
1. Create new test files in the `e2e/` directory
2. Follow the naming convention: `*.spec.js`
3. Use descriptive test names that match acceptance criteria
4. Include proper setup and teardown

### Test Best Practices
1. **Use Page Objects**: Create reusable page object classes
2. **Data-Driven Tests**: Use test data from external files
3. **Screenshot on Failure**: Automatic screenshots for debugging
4. **Parallel Execution**: Design tests to run in parallel
5. **Clean State**: Ensure tests don't interfere with each other

## Performance Benchmarks

Expected performance metrics:
- **Page Load Time**: < 3 seconds
- **Pagination Navigation**: < 2 seconds
- **Search Results**: < 2 seconds
- **Table Rendering**: < 1 second for up to 1000 rows

## Accessibility Testing

Tests include accessibility checks:
- Keyboard navigation support
- Screen reader compatibility
- Touch-friendly button sizes (minimum 44px)
- High contrast mode compatibility

## Browser Compatibility

Tests run on:
- **Desktop**: Chrome, Firefox, Safari
- **Mobile**: Chrome Mobile, Safari Mobile
- **Responsive**: Various viewport sizes

---

## Quick Start

1. **Start Services**:
   ```bash
   # From project root
   docker-compose up -d
   ```

2. **Install Dependencies**:
   ```bash
   cd apps/hindsight-dashboard
   npm install
   npx playwright install
   ```

3. **Run Tests**:
   ```bash
   npm run test:e2e
   ```

4. **View Results**:
   ```bash
   npx playwright show-report
