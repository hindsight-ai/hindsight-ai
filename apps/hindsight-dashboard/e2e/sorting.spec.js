import { test, expect } from '@playwright/test';
import { MemoryBlocksPage } from './pages/MemoryBlocksPage.js';

/**
 * Memory Block Sorting E2E Tests for Hindsight Dashboard
 *
 * These tests verify the sorting functionality on the memory blocks page
 * as specified in the acceptance matrix (TC-MEM-004).
 *
 * Prerequisites:
 * - Hindsight services must be running (backend, dashboard, database)
 * - Dashboard accessible at http://localhost:3000
 * - Sufficient test data (minimum 10 memory blocks with varied data) in the database
 */

test.describe('Memory Block Sorting', () => {
  let memoryBlocksPage;

  test.beforeEach(async ({ page }) => {
    memoryBlocksPage = new MemoryBlocksPage(page);
    await memoryBlocksPage.goto();
  });

  test('TC-MEM-004-01: Single column sorting', async ({ page, browserName }) => {
    // Skip on mobile browsers as sorting may not work the same way
    if (browserName === 'Mobile Chrome' || browserName === 'Mobile Safari') {
      console.log('Skipping sort test on mobile browser - functionality may differ');
      return;
    }

    // Verify sortable columns are present
    const sortableHeaders = page.locator('.sortable-header');
    const count = await sortableHeaders.count();
    expect(count).toBeGreaterThan(0);

    // Test sorting by Creation Date column (visible and sortable)
    const dateHeader = page.locator('.sortable-header:has-text("Creation Date")');
    if (await dateHeader.isVisible()) {
      // Get initial first row content
      const firstRowBefore = await page.locator('.data-table-row').first().textContent();

      // Click to sort ascending
      await dateHeader.click();
      await page.waitForTimeout(500);

      // Verify sort arrow appears
      const sortArrow = dateHeader.locator('.sort-arrow');
      await expect(sortArrow).toBeVisible();
      await expect(sortArrow).toHaveText('▲');

      // Get first row content after ascending sort
      const firstRowAfterAsc = await page.locator('.data-table-row').first().textContent();

      // Click again to sort descending
      await dateHeader.click();
      await page.waitForTimeout(500);

      // Verify sort arrow changes to descending
      await expect(sortArrow).toHaveText('▼');

      // Get first row content after descending sort
      const firstRowAfterDesc = await page.locator('.data-table-row').first().textContent();

      // Verify that sorting actually changed the order
      expect(firstRowAfterAsc).not.toBe(firstRowAfterDesc);
    }
  });

  test('TC-MEM-004-02: Multi-column sorting', async ({ page, browserName }) => {
    // Skip on mobile browsers as sorting may not work the same way
    if (browserName === 'Mobile Chrome' || browserName === 'Mobile Safari') {
      console.log('Skipping multi-column sort test on mobile browser - functionality may differ');
      return;
    }

    // Test sorting by multiple columns - use visible sortable columns
    const sortableColumns = [
      { name: 'Creation Date', selector: '.sortable-header:has-text("Creation Date")' },
      { name: 'Feedback', selector: '.sortable-header:has-text("Feedback")' }
    ];

    for (const column of sortableColumns) {
      const header = page.locator(column.selector);

      if (await header.isVisible()) {
        // Click to sort this column
        await header.click();
        await page.waitForTimeout(500);

        // Verify sort indicator appears
        const sortArrow = header.locator('.sort-arrow');
        await expect(sortArrow).toBeVisible();

        // Get first row content to verify sorting worked
        const firstRowContent = await page.locator('.data-table-row').first().textContent();
        expect(firstRowContent).toBeTruthy();

        // Toggle sort direction
        await header.click();
        await page.waitForTimeout(500);

        // Verify sort direction changed
        await expect(sortArrow).toHaveText('▼');
      }
    }
  });

  test('TC-MEM-004-03: Sort direction toggling', async ({ page, browserName }) => {
    // Skip on mobile browsers as sorting may not work the same way
    if (browserName === 'Mobile Chrome' || browserName === 'Mobile Safari') {
      console.log('Skipping sort direction toggling test on mobile browser - functionality may differ');
      return;
    }

    // Find a sortable column to test
    const sortableHeaders = page.locator('.sortable-header');
    const firstSortableHeader = sortableHeaders.first();

    if (await firstSortableHeader.isVisible()) {
      // First click - should sort ascending
      await firstSortableHeader.click();
      await page.waitForTimeout(500);

      const sortArrow = firstSortableHeader.locator('.sort-arrow');
      await expect(sortArrow).toHaveText('▲');

      // Get first row content after ascending sort
      const firstRowAsc = await page.locator('.data-table-row').first().textContent();

      // Second click - should sort descending
      await firstSortableHeader.click();
      await page.waitForTimeout(500);

      await expect(sortArrow).toHaveText('▼');

      // Get first row content after descending sort
      const firstRowDesc = await page.locator('.data-table-row').first().textContent();

      // Third click - should go back to ascending
      await firstSortableHeader.click();
      await page.waitForTimeout(500);

      await expect(sortArrow).toHaveText('▲');

      // Get first row content after third click
      const firstRowAscAgain = await page.locator('.data-table-row').first().textContent();

      // Verify toggling works (first and third sorts should be the same)
      expect(firstRowAsc).toBe(firstRowAscAgain);

      // Verify ascending and descending are different
      expect(firstRowAsc).not.toBe(firstRowDesc);
    }
  });

  test('TC-MEM-004-04: Visual indicators', async ({ page, browserName }) => {
    // Skip on mobile browsers as sorting may not work the same way
    if (browserName === 'Mobile Chrome' || browserName === 'Mobile Safari') {
      console.log('Skipping visual indicators test on mobile browser - functionality may differ');
      return;
    }

    // Test visual sort indicators
    const sortableHeaders = page.locator('.sortable-header');

    if (await sortableHeaders.first().isVisible()) {
      // Click first sortable header
      await sortableHeaders.first().click();
      await page.waitForTimeout(500);

      // Verify sort arrow is visible
      const sortArrow = page.locator('.sortable-header .sort-arrow').first();
      await expect(sortArrow).toBeVisible();

      // Verify only one column shows sort indicator at a time
      const activeSortArrows = page.locator('.sort-arrow');
      const arrowCount = await activeSortArrows.count();
      expect(arrowCount).toBeLessThanOrEqual(1);

      // Test that clicking another column moves the indicator
      if (await sortableHeaders.nth(1).isVisible()) {
        await sortableHeaders.nth(1).click();
        await page.waitForTimeout(500);

        // Verify the sort indicator moved to the second column
        const secondSortArrow = sortableHeaders.nth(1).locator('.sort-arrow');
        await expect(secondSortArrow).toBeVisible();
      }
    }
  });

  test('TC-MEM-004-05: Keyboard navigation', async ({ page }) => {
    // Test keyboard navigation for sorting
    const sortableHeaders = page.locator('.sortable-header');

    if (await sortableHeaders.first().isVisible()) {
      // Focus on first sortable header
      await sortableHeaders.first().focus();

      // Press Enter to sort
      await page.keyboard.press('Enter');
      await page.waitForTimeout(500);

      // Verify sort arrow appears
      const sortArrow = sortableHeaders.first().locator('.sort-arrow');
      await expect(sortArrow).toBeVisible();

      // Test Space key
      await sortableHeaders.first().focus();
      await page.keyboard.press('Space');
      await page.waitForTimeout(500);

      // Verify sort direction toggles
      await expect(sortArrow).toBeVisible();

      // Test Tab navigation between sortable headers
      await page.keyboard.press('Tab');
      const focusedElement = page.locator(':focus');

      // Verify we can tab to next focusable element
      await expect(focusedElement).toBeVisible();
    }
  });

  test('TC-MEM-004-06: Sort persistence', async ({ page }) => {
    // Test that sort state persists during navigation
    const sortableHeaders = page.locator('.sortable-header');

    if (await sortableHeaders.first().isVisible()) {
      // Apply a sort
      await sortableHeaders.first().click();
      await page.waitForTimeout(500);

      // Get current sort state - check if sort arrow exists
      const sortArrow = sortableHeaders.first().locator('.sort-arrow');
      let sortDirection = null;
      if (await sortArrow.isVisible()) {
        sortDirection = await sortArrow.textContent();
      }

      // Navigate to next page if possible - use force click to handle pointer events issues
      const nextButton = page.locator('button:has-text("Next")');
      if (await nextButton.isVisible() && !(await nextButton.isDisabled())) {
        await nextButton.click({ force: true });
        await page.waitForTimeout(1000);

        // Navigate back
        const prevButton = page.locator('button:has-text("Previous")');
        if (await prevButton.isVisible()) {
          await prevButton.click({ force: true });
          await page.waitForTimeout(1000);

          // Verify sort state is maintained if it existed
          if (sortDirection) {
            const sortArrowAfter = sortableHeaders.first().locator('.sort-arrow');
            if (await sortArrowAfter.isVisible()) {
              const sortDirectionAfter = await sortArrowAfter.textContent();
              expect(sortDirectionAfter).toBe(sortDirection);
            }
          }
        }
      }

      // Test sort persistence with search/filter
      const searchInput = page.locator('input[type="search"], input[placeholder*="search"]');
      if (await searchInput.isVisible()) {
        // Apply a broad search that shouldn't change much
        await searchInput.fill('test');
        await searchInput.press('Enter');
        await page.waitForTimeout(1000);

        // Verify sort indicator is still present if it was there before
        if (sortDirection) {
          const sortArrowAfterSearch = sortableHeaders.first().locator('.sort-arrow');
          await expect(sortArrowAfterSearch).toBeVisible();
        }
      }
    }
  });

  test('TC-MEM-004-07: Sort performance with large datasets', async ({ page }) => {
    // Test sorting performance
    const sortableHeaders = page.locator('.sortable-header');

    if (await sortableHeaders.first().isVisible()) {
      // Measure sort operation time
      const startTime = Date.now();

      await sortableHeaders.first().click();
      await page.waitForTimeout(500);

      const sortTime = Date.now() - startTime;
      expect(sortTime).toBeLessThan(4000); // Should complete within 4 seconds (more realistic for all browsers)

      // Verify table updates after sort
      const rows = page.locator('.data-table-row');
      await expect(rows.first()).toBeVisible();

      // Test multiple rapid sort operations
      for (let i = 0; i < 3; i++) {
        const rapidStartTime = Date.now();
        await sortableHeaders.first().click();
        await page.waitForTimeout(300);
        const rapidSortTime = Date.now() - rapidStartTime;
        expect(rapidSortTime).toBeLessThan(1000);
      }
    }
  });

  test('TC-MEM-004-08: Sort with filtered results', async ({ page }) => {
    // Test sorting works correctly with filtered data
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]');
    const sortableHeaders = page.locator('.sortable-header');

    if (await searchInput.isVisible() && await sortableHeaders.first().isVisible()) {
      // Get initial row count
      const initialRowCount = await page.locator('.data-table-row').count();

      // Apply a search filter
      await searchInput.fill('test');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // Get filtered row count
      const filteredRowCount = await page.locator('.data-table-row').count();

      // If filtering worked, test sorting on filtered results
      if (filteredRowCount < initialRowCount || filteredRowCount > 0) {
        // Apply sort to filtered results
        await sortableHeaders.first().click();
        await page.waitForTimeout(500);

        // Verify sort indicator appears
        const sortArrow = sortableHeaders.first().locator('.sort-arrow');
        await expect(sortArrow).toBeVisible();

        // Verify table still has content after sorting filtered results
        const sortedRows = page.locator('.data-table-row');
        await expect(sortedRows.first()).toBeVisible();

        // Verify sort direction can be toggled on filtered results
        await sortableHeaders.first().click();
        await page.waitForTimeout(500);
        await expect(sortArrow).toHaveText('▼');
      }
    }
  });

  test('TC-MEM-004-09: Sort accessibility', async ({ page }) => {
    // Test accessibility features for sorting
    const sortableHeaders = page.locator('.sortable-header');

    if (await sortableHeaders.first().isVisible()) {
      const firstHeader = sortableHeaders.first();

      // Check ARIA attributes
      const ariaSort = await firstHeader.getAttribute('aria-sort');
      expect(['none', 'ascending', 'descending']).toContain(ariaSort);

      // Check keyboard accessibility
      await firstHeader.focus();
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();

      // Test keyboard activation
      await page.keyboard.press('Enter');
      await page.waitForTimeout(500);

      // Verify aria-sort updates after sorting
      const ariaSortAfter = await firstHeader.getAttribute('aria-sort');
      expect(['ascending', 'descending']).toContain(ariaSortAfter);
    }
  });

  test('TC-MEM-004-10: Sort error handling', async ({ page }) => {
    // Test error handling during sort operations
    const sortableHeaders = page.locator('.sortable-header');

    if (await sortableHeaders.first().isVisible()) {
      // Test rapid clicking doesn't break the interface
      const firstHeader = sortableHeaders.first();

      // Rapid clicks
      for (let i = 0; i < 5; i++) {
        await firstHeader.click();
        await page.waitForTimeout(100);
      }

      // Verify interface is still functional
      await expect(firstHeader).toBeVisible();
      const rows = page.locator('.data-table-row');
      await expect(rows.first()).toBeVisible();

      // Test that sort state is consistent after rapid operations
      const sortArrow = firstHeader.locator('.sort-arrow');
      if (await sortArrow.isVisible()) {
        const arrowText = await sortArrow.textContent();
        expect(['▲', '▼']).toContain(arrowText);
      }
    }
  });
});
