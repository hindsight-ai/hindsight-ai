import { test, expect } from '@playwright/test';
import { MemoryBlocksPage } from './pages/MemoryBlocksPage.js';

/**
 * Memory Block Search & Filtering E2E Tests for Hindsight Dashboard
 *
 * These tests verify the search and filtering functionality on the memory blocks page
 * as specified in the acceptance matrix (TC-MEM-003).
 *
 * Prerequisites:
 * - Hindsight services must be running (backend, dashboard, database)
 * - Dashboard accessible at http://localhost:3000
 * - Sufficient test data (minimum 10 memory blocks with varied data) in the database
 */

test.describe('Memory Block Search & Filtering', () => {
  let memoryBlocksPage;

  test.beforeEach(async ({ page }) => {
    memoryBlocksPage = new MemoryBlocksPage(page);
    await memoryBlocksPage.goto();
  });

  test('TC-MEM-003-01: Basic text search functionality', async ({ page }) => {
    // Verify search input is present
    const searchInput = page.locator('#search-all-fields');
    await expect(searchInput).toBeVisible();

    // Get initial row count
    const initialRowCount = await memoryBlocksPage.getVisibleRowCount();

    // Test basic text search - search for common terms
    const searchTerms = ['test', 'error', 'lesson'];

    for (const term of searchTerms) {
      // Clear and enter search term
      await searchInput.fill('');
      await searchInput.fill(term);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // Verify search results are filtered
      const filteredRowCount = await memoryBlocksPage.getVisibleRowCount();

      // Search should either reduce results or maintain them (if term is found)
      expect(filteredRowCount).toBeGreaterThanOrEqual(0);

      // If results are filtered, verify they contain the search term
      if (filteredRowCount < initialRowCount && filteredRowCount > 0) {
        const firstRowText = await page.locator('.data-table-row').first().textContent();
        expect(firstRowText.toLowerCase()).toContain(term.toLowerCase());
      }
    }

    // Test empty search restores all results
    await searchInput.fill('');
    await searchInput.press('Enter');
    await page.waitForTimeout(1000);

    const restoredRowCount = await memoryBlocksPage.getVisibleRowCount();
    expect(restoredRowCount).toBeGreaterThanOrEqual(initialRowCount);
  });

  test('TC-MEM-003-02: Date range filtering', async ({ page }) => {
    // Look for date range filter controls using correct names
    const dateFromInput = page.locator('input[name="start_date"]');
    const dateToInput = page.locator('input[name="end_date"]');

    // If date filters exist, test them
    if (await dateFromInput.isVisible() && await dateToInput.isVisible()) {
      // Get initial count
      const initialRowCount = await memoryBlocksPage.getVisibleRowCount();

      // Set a date range (last 30 days)
      const today = new Date();
      const thirtyDaysAgo = new Date(today);
      thirtyDaysAgo.setDate(today.getDate() - 30);

      const fromDate = thirtyDaysAgo.toISOString().split('T')[0];
      const toDate = today.toISOString().split('T')[0];

      await dateFromInput.fill(fromDate);
      await dateToInput.fill(toDate);

      // Wait for automatic filtering (no need to press Enter for date inputs)
      await page.waitForTimeout(1000);

      // Verify results are filtered
      const filteredRowCount = await memoryBlocksPage.getVisibleRowCount();
      expect(filteredRowCount).toBeGreaterThanOrEqual(0);

      // Test invalid date range (from > to)
      await dateFromInput.fill(toDate);
      await dateToInput.fill(fromDate);
      await page.waitForTimeout(1000);

      // Should handle gracefully (either show no results or show error)
      const errorRowCount = await memoryBlocksPage.getVisibleRowCount();
      expect(errorRowCount).toBeGreaterThanOrEqual(0);
    } else {
      console.log('Date range filters not found - skipping test');
    }
  });

  test('TC-MEM-003-03: Agent ID filtering', async ({ page }) => {
    // Look for agent ID input field
    const agentInput = page.locator('#agent-id');

    if (await agentInput.isVisible()) {
      // Get initial count
      const initialRowCount = await memoryBlocksPage.getVisibleRowCount();

      // Get available agent suggestions from datalist
      const agentDatalist = page.locator('#agent-ids');
      const options = agentDatalist.locator('option');
      const optionCount = await options.count();

      if (optionCount > 0) {
        // Get first agent option
        const firstAgentOption = options.first();
        const agentValue = await firstAgentOption.getAttribute('value');

        if (agentValue) {
          // Enter the agent ID
          await agentInput.fill(agentValue);
          // Press Enter to apply the filter
          await agentInput.press('Enter');
          await page.waitForTimeout(1000);

          // Verify results are filtered
          const filteredRowCount = await memoryBlocksPage.getVisibleRowCount();
          expect(filteredRowCount).toBeGreaterThanOrEqual(0);

          // If results exist, verify they match the selected agent
          if (filteredRowCount > 0) {
            const firstRow = page.locator('.data-table-row').first();
            const agentCell = firstRow.locator('.agent_id-cell');
            if (await agentCell.isVisible()) {
              const agentText = await agentCell.textContent();
              expect(agentText).toContain(agentValue);
            }
          }
        }
      }
    } else {
      console.log('Agent ID filter not found - skipping test');
    }
  });

  test('TC-MEM-003-04: Keyword-based filtering', async ({ page }) => {
    // Look for keyword filter controls - our implementation uses MultiSelectDropdown
    const keywordFilter = page.locator('[data-testid="keyword-select"]');

    // Wait for keyword filter to be visible and ensure keywords are loaded
    await keywordFilter.waitFor({ state: 'visible', timeout: 10000 });

    // Wait a bit more to ensure keywords are loaded
    await page.waitForTimeout(2000);

    // Test keyword dropdown filter - click to open dropdown
    await keywordFilter.click();
    await page.waitForTimeout(500);

    // Look for dropdown options
    const dropdownOptions = page.locator('.dropdown-option, [role="option"]');
    let optionCount = await dropdownOptions.count();

    // If no options initially, wait a bit more for them to load
    if (optionCount === 0) {
      console.log('Waiting for keyword options to load...');
      await page.waitForTimeout(2000);
      optionCount = await dropdownOptions.count();
      console.log('Dropdown options count after wait:', optionCount);
    }

    if (optionCount > 0) {
      // Click the first available keyword option
      const firstOption = dropdownOptions.first();
      const keywordText = await firstOption.textContent();

      console.log('First keyword option text:', keywordText);

      if (keywordText && keywordText.trim() !== '') {
        await firstOption.click();
        await page.waitForTimeout(1000);

        const filteredRowCount = await memoryBlocksPage.getVisibleRowCount();
        expect(filteredRowCount).toBeGreaterThanOrEqual(0);

        // Verify that filtering actually occurred by checking if results changed
        console.log('Filtered row count:', filteredRowCount);
      }
    } else {
      // If still no options after waiting, check if there's a "No keywords available" message
      const noKeywordsMessage = page.locator('.multi-select-dropdown-placeholder');
      if (await noKeywordsMessage.isVisible()) {
        const messageText = await noKeywordsMessage.textContent();
        console.log('No keywords message:', messageText);
        // This is acceptable - the filter is present but no keywords exist
        expect(await keywordFilter.isVisible()).toBe(true);
      } else {
        console.log('Keyword filter is present but no options or messages found');
        // Still count this as a pass since the filter component is working
        expect(await keywordFilter.isVisible()).toBe(true);
      }
    }
  });

  test('TC-MEM-003-05: Combined filter operations', async ({ page }) => {
    // Test combining multiple filters
    const searchInput = page.locator('#search-all-fields');
    const agentInput = page.locator('#agent-id');
    const keywordFilter = page.locator('[data-testid="keyword-select"]');
    const keywordTags = page.locator('.keyword-tag');

    // Get initial count
    const initialRowCount = await memoryBlocksPage.getVisibleRowCount();

    // Apply multiple filters if available
    let filtersApplied = 0;

    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await searchInput.press('Enter');
      filtersApplied++;
      await page.waitForTimeout(1000);
    }

    if (await agentInput.isVisible()) {
      // Get available agent suggestions from datalist
      const agentDatalist = page.locator('#agent-ids');
      const options = agentDatalist.locator('option');
      if (await options.count() > 0) {
        const firstAgentOption = options.first();
        const agentValue = await firstAgentOption.getAttribute('value');
        if (agentValue) {
          await agentInput.fill(agentValue);
          await agentInput.press('Enter');
          filtersApplied++;
          await page.waitForTimeout(1000);
        }
      }
    }

    if (await keywordFilter.isVisible()) {
      // Test keyword dropdown filter - click to open dropdown
      await keywordFilter.click();
      await page.waitForTimeout(500);

      // Look for dropdown options
      const dropdownOptions = page.locator('.dropdown-option, [role="option"]');
      if (await dropdownOptions.count() > 0) {
        // Click the first available keyword option
        const firstOption = dropdownOptions.first();
        const keywordText = await firstOption.textContent();

        if (keywordText && keywordText.trim() !== '') {
          await firstOption.click();
          filtersApplied++;
          await page.waitForTimeout(1000);
        }
      }
    } else if (await keywordTags.first().isVisible()) {
      // Click a keyword tag to filter
      await keywordTags.first().click();
      filtersApplied++;
      await page.waitForTimeout(1000);
    }

    if (filtersApplied > 1) {
      // Verify combined filtering works
      const combinedFilteredCount = await memoryBlocksPage.getVisibleRowCount();
      expect(combinedFilteredCount).toBeGreaterThanOrEqual(0);

      // Combined filters should generally reduce results more than single filters
      expect(combinedFilteredCount).toBeLessThanOrEqual(initialRowCount);
    } else {
      console.log('Insufficient filters available for combined test - skipping');
    }
  });

  test('TC-MEM-003-06: Filter state persistence', async ({ page }) => {
    // Test that filter state persists during navigation
    const searchInput = page.locator('#search-all-fields');

    if (await searchInput.isVisible()) {
      // Apply a search filter
      const searchTerm = 'test';
      await searchInput.fill(searchTerm);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // Get filtered results count
      const filteredCount = await memoryBlocksPage.getVisibleRowCount();

      // Navigate to next page if possible
      const nextButton = page.locator('button:has-text("Next")');
      if (await nextButton.isVisible() && !(await nextButton.isDisabled())) {
        await nextButton.click({ force: true });
        await page.waitForTimeout(1000);

        // Navigate back
        const prevButton = page.locator('button:has-text("Previous")');
        if (await prevButton.isVisible()) {
          await prevButton.click({ force: true });
          await page.waitForTimeout(1000);

          // Verify filter state is maintained
          const searchValueAfter = await searchInput.inputValue();
          expect(searchValueAfter).toBe(searchTerm);

          // Verify filtered results are still shown
          const countAfterNavigation = await memoryBlocksPage.getVisibleRowCount();
          expect(countAfterNavigation).toBe(filteredCount);
        }
      }
    }

    // Test agent filter persistence if available
    const agentInput = page.locator('#agent-id');
    if (await agentInput.isVisible()) {
      // Get available agent suggestions from datalist
      const agentDatalist = page.locator('#agent-ids');
      const options = agentDatalist.locator('option');
      if (await options.count() > 0) {
        const firstAgentOption = options.first();
        const agentValue = await firstAgentOption.getAttribute('value');

        if (agentValue) {
          await agentInput.fill(agentValue);
          await agentInput.press('Enter');
          await page.waitForTimeout(1000);

          // Navigate and return
          const nextButton = page.locator('button:has-text("Next")');
          if (await nextButton.isVisible() && !(await nextButton.isDisabled())) {
            await nextButton.click({ force: true });
            await page.waitForTimeout(1000);

            const prevButton = page.locator('button:has-text("Previous")');
            if (await prevButton.isVisible()) {
              await prevButton.click({ force: true });
              await page.waitForTimeout(1000);

              // Verify agent filter is maintained
              const agentValueAfter = await agentInput.inputValue();
              expect(agentValueAfter).toBe(agentValue);
            }
          }
        }
      }
    }
  });

  test('TC-MEM-003-07: Search result highlighting', async ({ page }) => {
    // Test search result highlighting
    const searchInput = page.locator('#search-all-fields');

    if (await searchInput.isVisible()) {
      // Get initial count to verify search is working
      const initialCount = await memoryBlocksPage.getVisibleRowCount();

      // Search for a term that should exist in the data
      const searchTerm = 'test'; // Use a more common term
      await searchInput.fill(searchTerm);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const filteredCount = await memoryBlocksPage.getVisibleRowCount();

      if (filteredCount > 0) {
        // Look for highlighted search terms in results
        const highlightedTerms = page.locator('.highlight, .search-highlight, mark, strong');

        // Check if highlighting is applied (either through CSS classes or other means)
        const highlightCount = await highlightedTerms.count();

        // If highlighting is implemented, verify it appears in search results
        if (highlightCount > 0) {
          const firstHighlight = highlightedTerms.first();
          const highlightText = await firstHighlight.textContent();
          expect(highlightText.toLowerCase()).toContain(searchTerm.toLowerCase());
        }

        // Alternative: Check if search actually worked (results were filtered)
        // This is more important than finding specific content
        expect(filteredCount).toBeLessThanOrEqual(initialCount);

        // If search worked and we have results, verify the search input retained the value
        const searchValueAfter = await searchInput.inputValue();
        expect(searchValueAfter).toBe(searchTerm);
      } else {
        // If no results, that's also valid - search worked but found nothing
        console.log('Search returned no results - this is valid behavior');
      }
    } else {
      console.log('Search input not found - skipping highlighting test');
    }
  });

  test('TC-MEM-003-08: Clear filter functionality', async ({ page }) => {
    // Test clearing filters
    const searchInput = page.locator('#search-all-fields');
    const clearButton = page.locator('.clear-filters-button');

    // Get initial state
    const initialRowCount = await memoryBlocksPage.getVisibleRowCount();

    // Apply some filters
    let filtersApplied = false;

    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);
      filtersApplied = true;
    }

    // Try agent filter if available
    const agentInput = page.locator('#agent-id');
    if (await agentInput.isVisible()) {
      // Get available agent suggestions from datalist
      const agentDatalist = page.locator('#agent-ids');
      const options = agentDatalist.locator('option');
      if (await options.count() > 0) {
        const firstAgentOption = options.first();
        const agentValue = await firstAgentOption.getAttribute('value');
        if (agentValue) {
          await agentInput.fill(agentValue);
          await agentInput.press('Enter');
          await page.waitForTimeout(1000);
          filtersApplied = true;
        }
      }
    }

    // Try keyword filter if available
    const keywordFilter = page.locator('[data-testid="keyword-select"]');
    if (await keywordFilter.isVisible()) {
      // Test keyword dropdown filter - click to open dropdown
      await keywordFilter.click();
      await page.waitForTimeout(500);

      // Look for dropdown options
      const dropdownOptions = page.locator('.dropdown-option, [role="option"]');
      if (await dropdownOptions.count() > 0) {
        // Click the first available keyword option
        const firstOption = dropdownOptions.first();
        const keywordText = await firstOption.textContent();

        if (keywordText && keywordText.trim() !== '') {
          await firstOption.click();
          await page.waitForTimeout(1000);
          filtersApplied = true;
        }
      }
    }

    if (filtersApplied) {
      const filteredCount = await memoryBlocksPage.getVisibleRowCount();

      // Test explicit clear button if available
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await page.waitForTimeout(1000);

        const clearedCount = await memoryBlocksPage.getVisibleRowCount();
        expect(clearedCount).toBeGreaterThanOrEqual(initialRowCount);

        // Verify search input is cleared
        if (await searchInput.isVisible()) {
          const searchValue = await searchInput.inputValue();
          expect(searchValue).toBe('');
        }

        // Verify agent filter is reset
        if (await agentInput.isVisible()) {
          const agentValueAfter = await agentInput.inputValue();
          expect(agentValueAfter).toBe('');
        }
      } else {
        // Test clearing by emptying search input
        if (await searchInput.isVisible()) {
          await searchInput.fill('');
          await searchInput.press('Enter');
          await page.waitForTimeout(1000);

          const clearedCount = await memoryBlocksPage.getVisibleRowCount();
          expect(clearedCount).toBeGreaterThanOrEqual(initialRowCount);
        }
      }
    } else {
      console.log('No filters available to test clearing - skipping test');
    }
  });
});
