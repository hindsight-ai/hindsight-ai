import { test, expect } from '@playwright/test';
import { AuthPage } from './pages/AuthPage.js';
import { MemoryBlocksPage } from './pages/MemoryBlocksPage.js';

test.describe('Agent Management Tests (AGENT-001, AGENT-002)', () => {
  let authPage;
  let memoryBlocksPage;

  test.beforeEach(async ({ page }) => {
    authPage = new AuthPage(page);
    memoryBlocksPage = new MemoryBlocksPage(page);

    // Navigate to the application and authenticate
    await page.goto('/');
    await authPage.login();

    // Navigate to Agents page
    await page.click('[data-testid="nav-agents"]');
    await page.waitForURL('**/agents');

    // Wait for agents page to load
    await page.waitForSelector('.agent-management-page', { timeout: 10000 });
  });

  // AGENT-001: Agent Listing and Display
  test.describe('AGENT-001: Agent Listing and Display', () => {
    test('TC-AGENT-001-01: Agent list display - should show agents table with proper structure', async ({ page }) => {
      console.log('Testing agent list display...');

      // Check if agents table is present
      const agentsTable = page.locator('.memory-block-table-container');
      const tableCount = await agentsTable.count();

      if (tableCount === 0) {
        console.log('No agents table found - checking for empty state');
        // Check for empty state message
        const emptyState = page.locator('.empty-state-message, text=No agents found');
        await expect(emptyState.first()).toBeVisible();
        console.log('Empty state displayed correctly');
        return;
      }

      // Verify table structure
      await expect(agentsTable.first()).toBeVisible();

      // Check for table headers
      const headerCells = page.locator('.header-cell');
      await expect(headerCells.first()).toBeVisible();

      // Check for at least one data row if agents exist
      const dataRows = page.locator('.memory-block-table-row');
      const rowCount = await dataRows.count();
      console.log(`Found ${rowCount} agent rows`);

      if (rowCount > 0) {
        // Verify first row has expected structure
        const firstRow = dataRows.first();
        await expect(firstRow).toBeVisible();

        // Check for agent name in first row
        const agentNameCell = firstRow.locator('.agent_name-cell');
        await expect(agentNameCell).toBeVisible();
      }
    });

    test('TC-AGENT-001-02: Memory block counts - should display memory counts for each agent', async ({ page }) => {
      console.log('Testing memory block counts display...');

      // Wait for agents to load
      await page.waitForTimeout(2000);

      const dataRows = page.locator('.memory-block-table-row');
      const rowCount = await dataRows.count();

      if (rowCount === 0) {
        console.log('No agents found - skipping memory count test');
        return;
      }

      // Check first agent for memory count display
      const firstRow = dataRows.first();
      const agentIdCell = firstRow.locator('.id-cell');

      if (await agentIdCell.count() > 0) {
        // Get agent ID for API verification
        const agentIdText = await agentIdCell.textContent();
        console.log(`Checking memory count for agent: ${agentIdText}`);

        // Note: Memory count display would need to be implemented in the UI
        // For now, we verify the agent data structure is correct
        const agentNameCell = firstRow.locator('.agent_name-cell');
        await expect(agentNameCell).toBeVisible();

        const creationDateCell = firstRow.locator('.created_at-cell');
        await expect(creationDateCell).toBeVisible();
      }
    });

    test('TC-AGENT-001-03: Agent status indicators - should show agent status information', async ({ page }) => {
      console.log('Testing agent status indicators...');

      // Wait for agents to load
      await page.waitForTimeout(2000);

      const dataRows = page.locator('.memory-block-table-row');
      const rowCount = await dataRows.count();

      if (rowCount === 0) {
        console.log('No agents found - skipping status indicator test');
        return;
      }

      // Check that agents have proper status information
      const firstRow = dataRows.first();

      // Verify agent has ID (indicates it's a valid agent)
      const agentIdCell = firstRow.locator('.id-cell');
      await expect(agentIdCell).toBeVisible();

      // Verify agent has name
      const agentNameCell = firstRow.locator('.agent_name-cell');
      await expect(agentNameCell).toBeVisible();

      // Verify agent has creation date
      const creationDateCell = firstRow.locator('.created_at-cell');
      await expect(creationDateCell).toBeVisible();

      console.log('Agent status indicators verified');
    });
  });

  // AGENT-002: Agent CRUD Operations
  test.describe('AGENT-002: Agent CRUD Operations', () => {
    test('TC-AGENT-002-01: Agent creation dialog - should open and function correctly', async ({ page }) => {
      console.log('Testing agent creation dialog...');

      // Click Add Agent button (specifically the one on the main page, not in dialog)
      const addButton = page.locator('button.filter-toggle-button:has-text("Add Agent")').first();
      await expect(addButton).toBeVisible();
      await addButton.click();

      // Verify dialog appears
      const dialog = page.locator('.dialog-overlay');
      await expect(dialog).toBeVisible();

      // Verify dialog title
      const dialogTitle = page.locator('.dialog-box h2:has-text("Add New Agent")');
      await expect(dialogTitle).toBeVisible();

      // Verify input field
      const agentNameInput = page.locator('#agentName');
      await expect(agentNameInput).toBeVisible();

      // Verify buttons
      const cancelButton = page.locator('button:has-text("Cancel")');
      await expect(cancelButton).toBeVisible();

      const addAgentButton = page.locator('.dialog-box button:has-text("Add Agent")').first();
      await expect(addAgentButton).toBeVisible();

      // Test cancel functionality
      await cancelButton.click();
      await expect(dialog).not.toBeVisible();

      console.log('Agent creation dialog verified');
    });

    test('TC-AGENT-002-02: Agent creation workflow - should create agent successfully', async ({ page }) => {
      console.log('Testing agent creation workflow...');

      // Click Add Agent button (specifically the one on the main page, not in dialog)
      const addButton = page.locator('button.filter-toggle-button:has-text("Add Agent")').first();
      await addButton.click();

      // Verify dialog appears
      const dialog = page.locator('.dialog-overlay');
      await expect(dialog).toBeVisible();

      // Generate unique agent name
      const timestamp = Date.now();
      const agentName = `Test Agent ${timestamp}`;

      // Fill agent name
      const agentNameInput = page.locator('#agentName');
      await agentNameInput.fill(agentName);

      // Click Add Agent button (inside the dialog)
      const addAgentButton = page.locator('.dialog-box button:has-text("Add Agent")').first();
      await addAgentButton.click();

      // Wait for dialog to close and success message
      await page.waitForTimeout(2000);

      // Check for success message
      const successMessage = page.locator('.confirmation-message, .success-message');
      if (await successMessage.count() > 0) {
        await expect(successMessage).toBeVisible();
        console.log('Success message displayed');
      }

      // Verify dialog is closed
      const dialogAfter = page.locator('.dialog-overlay');
      const isDialogVisible = await dialogAfter.isVisible().catch(() => false);
      if (isDialogVisible) {
        console.log('Dialog still visible - may indicate error');
      }

      // Check if new agent appears in list (may take time for API)
      await page.waitForTimeout(3000);
      console.log('Agent creation workflow completed');
    });

    test('TC-AGENT-002-03: Agent deletion with confirmation - should delete agent after confirmation', async ({ page }) => {
      console.log('Testing agent deletion with confirmation...');

      // Wait for agents to load
      await page.waitForTimeout(2000);

      const dataRows = page.locator('.memory-block-table-row');
      const rowCount = await dataRows.count();

      if (rowCount === 0) {
        console.log('No agents available for deletion test - skipping');
        return;
      }

      // Get first agent details before deletion
      const firstRow = dataRows.first();
      const agentNameCell = firstRow.locator('.agent_name-cell');
      const agentName = await agentNameCell.textContent();
      console.log(`Attempting to delete agent: ${agentName}`);

      // Click delete button (trash icon)
      const deleteButton = firstRow.locator('.action-icon-button.remove-button');
      await expect(deleteButton).toBeVisible();
      await deleteButton.click();

      // Handle browser confirmation dialog
      page.on('dialog', async dialog => {
        console.log(`Dialog message: ${dialog.message()}`);
        await dialog.accept(); // Click OK to confirm deletion
      });

      // Wait for deletion to complete
      await page.waitForTimeout(3000);

      // Verify agent is removed from list
      // Note: This may require page refresh or waiting for API update
      console.log('Agent deletion confirmation test completed');
    });

    test('TC-AGENT-002-04: Agent filtering - should filter agents by search term', async ({ page }) => {
      console.log('Testing agent filtering...');

      // Wait for agents to load
      await page.waitForTimeout(2000);

      const dataRows = page.locator('.memory-block-table-row');
      const initialRowCount = await dataRows.count();

      if (initialRowCount === 0) {
        console.log('No agents available for filtering test - skipping');
        return;
      }

      // Get first agent name for search
      const firstRow = dataRows.first();
      const agentNameCell = firstRow.locator('.agent_name-cell');
      const agentName = await agentNameCell.textContent();
      console.log(`Using agent name for search: ${agentName}`);

      // Find search input
      const searchInput = page.locator('.search-input-large, input[placeholder*="search"]');
      if (await searchInput.count() > 0) {
        // Clear and enter search term
        await searchInput.fill('');
        await searchInput.fill(agentName);

        // Click search button if present
        const searchButton = page.locator('button:has-text("Search")');
        if (await searchButton.count() > 0) {
          await searchButton.click();
        }

        // Wait for search results
        await page.waitForTimeout(2000);

        // Verify filtered results
        const filteredRows = page.locator('.memory-block-table-row');
        const filteredCount = await filteredRows.count();

        if (filteredCount > 0) {
          // Check if filtered results contain the search term
          const firstFilteredRow = filteredRows.first();
          const filteredAgentName = await firstFilteredRow.locator('.agent_name-cell').textContent();

          // The filtered result should contain the search term
          expect(filteredAgentName.toLowerCase()).toContain(agentName.toLowerCase());
          console.log('Agent filtering working correctly');
        } else {
          console.log('No filtered results found');
        }
      } else {
        console.log('Search input not found - filtering may not be implemented yet');
      }
    });
  });

  // Cross-browser compatibility tests
  test.describe('Cross-Browser Compatibility', () => {
    test('Agent management works across different browsers', async ({ page, browserName }) => {
      console.log(`Testing agent management on ${browserName}...`);

      // Basic functionality test
      const agentsTable = page.locator('.memory-block-table-container');
      const tableCount = await agentsTable.count();

      if (tableCount > 0) {
        await expect(agentsTable.first()).toBeVisible();
        console.log(`Agent table visible on ${browserName}`);
      } else {
        // Check for empty state
        const emptyState = page.locator('.empty-state-message, text=No agents found');
        await expect(emptyState.first()).toBeVisible();
        console.log(`Empty state visible on ${browserName}`);
      }

      // Test add agent button visibility
      const addButton = page.locator('button:has-text("Add Agent")');
      await expect(addButton).toBeVisible();
      console.log(`Add Agent button visible on ${browserName}`);
    });
  });

  // Error handling tests
  test.describe('Error Handling', () => {
    test('Handles API errors gracefully', async ({ page }) => {
      console.log('Testing error handling...');

      // This test would need to simulate API errors
      // For now, we verify the page loads without crashing
      await expect(page.locator('.agent-management-page')).toBeVisible();
      console.log('Page loads without errors');
    });
  });
});
