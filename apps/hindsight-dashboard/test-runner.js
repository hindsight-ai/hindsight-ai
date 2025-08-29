#!/usr/bin/env node

/**
 * Test Runner Script for Hindsight Dashboard E2E Tests
 *
 * This script provides a convenient way to run E2E tests with different configurations
 * and handles common setup tasks.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class TestRunner {
  constructor() {
    this.projectRoot = path.resolve(__dirname);
    this.e2eDir = path.join(this.projectRoot, 'e2e');
  }

  /**
   * Check if services are running
   */
  checkServices() {
    console.log('🔍 Checking if Hindsight services are running...');

    try {
      // Check if dashboard is accessible
      execSync('curl -f http://localhost:3000 > /dev/null 2>&1', { stdio: 'pipe' });
      console.log('✅ Dashboard is accessible at http://localhost:3000');
      return true;
    } catch (error) {
      console.log('❌ Dashboard is not accessible at http://localhost:3000');
      console.log('Please start the services first:');
      console.log('  docker-compose up -d');
      return false;
    }
  }

  /**
   * Install Playwright browsers
   */
  installBrowsers() {
    console.log('🎭 Installing Playwright browsers...');
    try {
      execSync('npx playwright install', { stdio: 'inherit', cwd: this.projectRoot });
      console.log('✅ Playwright browsers installed successfully');
      return true;
    } catch (error) {
      console.log('❌ Failed to install Playwright browsers');
      return false;
    }
  }

  /**
   * Run all E2E tests
   */
  runAllTests(options = {}) {
    const {
      headed = false,
      debug = false,
      browser = null,
      grep = null
    } = options;

    let command = 'npx playwright test';

    if (headed) command += ' --headed';
    if (debug) command += ' --debug';
    if (browser) command += ` --project=${browser}`;
    if (grep) command += ` --grep="${grep}"`;

    console.log(`🚀 Running E2E tests: ${command}`);

    try {
      execSync(command, { stdio: 'inherit', cwd: this.projectRoot });
      console.log('✅ All tests completed successfully');
      return true;
    } catch (error) {
      console.log('❌ Some tests failed');
      return false;
    }
  }

  /**
   * Run pagination tests specifically
   */
  runPaginationTests(options = {}) {
    console.log('📄 Running pagination-specific tests...');
    return this.runAllTests({ ...options, grep: 'pagination' });
  }

  /**
   * Show test report
   */
  showReport() {
    console.log('📊 Opening test report...');
    try {
      execSync('npx playwright show-report', { stdio: 'inherit', cwd: this.projectRoot });
    } catch (error) {
      console.log('❌ Could not open test report');
    }
  }

  /**
   * Run tests with UI mode
   */
  runUITests() {
    console.log('🎮 Running tests in UI mode...');
    try {
      execSync('npm run test:e2e:ui', { stdio: 'inherit', cwd: this.projectRoot });
    } catch (error) {
      console.log('❌ UI mode failed');
    }
  }

  /**
   * Generate test data if needed
   */
  generateTestData() {
    console.log('🧪 Checking test data...');
    // This could be extended to generate test data programmatically
    console.log('ℹ️  Please ensure your database has at least 50 memory blocks for comprehensive testing');
  }

  /**
   * Main execution method
   */
  async run(command = 'all', options = {}) {
    console.log('🎯 Hindsight Dashboard E2E Test Runner');
    console.log('=' .repeat(50));

    // Pre-flight checks
    if (!this.checkServices()) {
      process.exit(1);
    }

    if (!this.installBrowsers()) {
      process.exit(1);
    }

    this.generateTestData();

    // Execute requested command
    let success = false;

    switch (command) {
      case 'all':
        success = this.runAllTests(options);
        break;
      case 'pagination':
        success = this.runPaginationTests(options);
        break;
      case 'ui':
        this.runUITests();
        success = true;
        break;
      case 'report':
        this.showReport();
        success = true;
        break;
      default:
        console.log(`❌ Unknown command: ${command}`);
        this.showHelp();
        process.exit(1);
    }

    if (success && command !== 'report' && command !== 'ui') {
      console.log('\n📊 To view detailed test results:');
      console.log('  npm run test:e2e:report');
      console.log('  # or');
      console.log('  node test-runner.js report');
    }

    process.exit(success ? 0 : 1);
  }

  /**
   * Show help information
   */
  showHelp() {
    console.log(`
Usage: node test-runner.js [command] [options]

Commands:
  all         Run all E2E tests (default)
  pagination  Run pagination-specific tests
  ui          Run tests in UI mode
  report      Show test report

Options:
  --headed    Run tests in headed mode (visible browser)
  --debug     Run tests in debug mode
  --browser   Specify browser (chromium, firefox, webkit)
  --grep      Filter tests by name

Examples:
  node test-runner.js all --headed
  node test-runner.js pagination --browser=chromium
  node test-runner.js ui
  node test-runner.js report

Prerequisites:
  - Hindsight services must be running (docker-compose up -d)
  - Dashboard accessible at http://localhost:3000
  - Sufficient test data in database (50+ memory blocks)
    `);
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0] || 'all';

  // Parse options
  const options = {};
  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const [key, value] = arg.slice(2).split('=');
      options[key] = value || true;
    }
  }

  const runner = new TestRunner();
  runner.run(command, options);
}

module.exports = TestRunner;
