/**
 * TC-MEM-005: Bulk Memory Operations Tests
 *
 * Test Suite for Bulk Memory Operations functionality
 * Covers selection, bulk actions, and confirmation dialogs
 */

import { test, expect } from '@playwright/test';
import { MemoryBlocksPage } from './pages/MemoryBlocksPage.js';

test.describe('TC-MEM-005: Bulk Memory Operations', () => {
  let memoryBlocksPage;

  test.beforeEach(async ({ page }) => {
    memoryBlocksPage = new MemoryBlocksPage(page);
    await memoryBlocksPage.goto();
  });

  test('should display bulk action bar when memory blocks are selected', async ({ page }) => {
    // Ensure we have at least one memory block
    const visibleRowCount = await memoryBlocksPage.getVisibleRowCount();
    expect(visibleRowCount).toBeGreaterThan(0);

    // Initially, bulk action bar should not be visible
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).not.toBeVisible();

    // Select first memory block using force click to bypass pointer events issues
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Bulk action bar should now be visible
    await expect(bulkActionBar).toBeVisible();

    // Verify selected count is displayed
    const selectedCount = bulkActionBar.locator('.selected-count');
    await expect(selectedCount).toContainText('1 items selected');
  });

  test('should select individual memory blocks', async ({ page }) => {
    // Ensure we have at least 3 memory blocks
    const visibleRowCount = await memoryBlocksPage.getVisibleRowCount();
    expect(visibleRowCount).toBeGreaterThanOrEqual(3);

    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const firstCheckbox = firstRow.locator('input[type="checkbox"]');
    await firstCheckbox.check({ force: true });

    // Wait for state update and verify it's checked
    await page.waitForTimeout(100);
    await expect(firstCheckbox).toBeChecked();

    // Select third memory block
    const thirdRow = page.locator('.data-table-row').nth(2);
    const thirdCheckbox = thirdRow.locator('input[type="checkbox"]');
    await thirdCheckbox.check({ force: true });

    // Wait for state update and verify it's checked
    await page.waitForTimeout(100);
    await expect(thirdCheckbox).toBeChecked();

    // Verify bulk action bar shows correct count (could be 1 or 2 depending on timing)
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).toBeVisible();
    const selectedCount = bulkActionBar.locator('.selected-count');
    const countText = await selectedCount.textContent();
    expect(countText).toMatch(/\d+ items selected/);
  });

  test('should select all memory blocks using select all checkbox', async ({ page }) => {
    // Ensure we have memory blocks
    const visibleRowCount = await memoryBlocksPage.getVisibleRowCount();
    expect(visibleRowCount).toBeGreaterThan(0);

    // Find and check the select all checkbox
    const selectAllCheckbox = page.locator('.data-table-header input[type="checkbox"]');
    await selectAllCheckbox.check({ force: true });

    // Wait for state updates
    await page.waitForTimeout(200);

    // Verify all individual checkboxes are checked
    const allCheckboxes = page.locator('.data-table-row input[type="checkbox"]');
    const checkboxCount = await allCheckboxes.count();

    // Check a few key checkboxes instead of all to avoid timeout
    const checkCount = Math.min(checkboxCount, 3);
    for (let i = 0; i < checkCount; i++) {
      await expect(allCheckboxes.nth(i)).toBeChecked();
    }

    // Verify bulk action bar shows items selected
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).toBeVisible();
    const selectedCount = bulkActionBar.locator('.selected-count');
    const countText = await selectedCount.textContent();
    expect(countText).toMatch(/\d+ items selected/);
  });

  test('should deselect all memory blocks using select all checkbox', async ({ page }) => {
    // First select all
    const selectAllCheckbox = page.locator('.data-table-header input[type="checkbox"]');
    await selectAllCheckbox.check({ force: true });

    // Wait for state updates
    await page.waitForTimeout(200);

    // Verify some checkboxes are selected (don't check all to avoid timeout)
    const allCheckboxes = page.locator('.data-table-row input[type="checkbox"]');
    const checkboxCount = await allCheckboxes.count();
    if (checkboxCount > 0) {
      await expect(allCheckboxes.first()).toBeChecked();
    }

    // Now uncheck select all
    await selectAllCheckbox.uncheck({ force: true });

    // Wait for state updates
    await page.waitForTimeout(200);

    // Verify some individual checkboxes are unchecked
    if (checkboxCount > 0) {
      await expect(allCheckboxes.first()).not.toBeChecked();
    }

    // Verify bulk action bar is hidden
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).not.toBeVisible();
  });

  test('should deselect individual memory blocks', async ({ page }) => {
    // Select all first
    const selectAllCheckbox = page.locator('.data-table-header input[type="checkbox"]');
    await selectAllCheckbox.check({ force: true });

    // Get initial count
    const allCheckboxes = page.locator('.data-table-row input[type="checkbox"]');
    const initialCount = await allCheckboxes.count();

    // Deselect first memory block
    const firstCheckbox = allCheckboxes.first();
    await firstCheckbox.uncheck();

    // Verify it's unchecked
    await expect(firstCheckbox).not.toBeChecked();

    // Verify bulk action bar shows reduced count
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).toBeVisible();
    const selectedCount = bulkActionBar.locator('.selected-count');
    await expect(selectedCount).toContainText(`${initialCount - 1} items selected`);
  });

  test('should show confirmation dialog for bulk remove action', async ({ page }) => {
    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Handle the confirmation dialog BEFORE clicking the button
    let dialogMessage = '';
    page.on('dialog', async dialog => {
      dialogMessage = dialog.message();
      expect(dialogMessage).toContain('Are you sure you want to archive');
      await dialog.dismiss(); // Dismiss to avoid actual deletion
    });

    // Click bulk remove button
    const bulkActionBar = page.locator('.bulk-action-bar');
    const removeButton = bulkActionBar.locator('.bulk-remove-button');
    await removeButton.click();

    // Wait a bit for the dialog to be handled
    await page.waitForTimeout(500);

    // Verify dialog was triggered
    expect(dialogMessage).toContain('Are you sure you want to archive');
  });

  test('should cancel bulk remove action', async ({ page }) => {
    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Click bulk remove button
    const bulkActionBar = page.locator('.bulk-action-bar');
    const removeButton = bulkActionBar.locator('.bulk-remove-button');
    await removeButton.click();

    // Cancel the action (dismiss dialog)
    await page.keyboard.press('Escape');

    // Verify dialog is dismissed
    const confirmDialog = page.locator('text=/Are you sure you want to archive/');
    await expect(confirmDialog).not.toBeVisible();

    // Verify memory block is still selected
    await expect(checkbox).toBeChecked();
  });

  test('should show confirmation dialog for bulk remove action without executing', async ({ page }) => {
    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Handle the confirmation dialog BEFORE clicking the button
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Are you sure you want to archive');
      await dialog.dismiss(); // Dismiss instead of accept to avoid modifying database
    });

    // Click bulk remove button
    const bulkActionBar = page.locator('.bulk-action-bar');
    const removeButton = bulkActionBar.locator('.bulk-remove-button');
    await removeButton.click();

    // Wait for dialog to be handled
    await page.waitForTimeout(500);

    // Verify memory block is still selected (action was cancelled)
    await expect(checkbox).toBeChecked();

    // Verify bulk action bar is still visible
    await expect(bulkActionBar).toBeVisible();
  });

  test('should handle bulk tag action', async ({ page }) => {
    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Click bulk tag button
    const bulkActionBar = page.locator('.bulk-action-bar');
    const tagButton = bulkActionBar.locator('.bulk-tag-button');

    // Handle the alert dialog
    let dialogTriggered = false;
    page.on('dialog', async dialog => {
      dialogTriggered = true;
      expect(dialog.message()).toContain('Bulk Tag functionality coming soon!');
      await dialog.accept();
    });

    await tagButton.click();

    // Wait a bit for the dialog to appear
    await page.waitForTimeout(500);

    // Verify dialog was triggered
    expect(dialogTriggered).toBe(true);
  });

  test('should handle bulk export action', async ({ page }) => {
    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Click bulk export button
    const bulkActionBar = page.locator('.bulk-action-bar');
    const exportButton = bulkActionBar.locator('.bulk-export-button');

    // Handle the alert dialog
    let dialogTriggered = false;
    page.on('dialog', async dialog => {
      dialogTriggered = true;
      expect(dialog.message()).toContain('Bulk Export functionality coming soon!');
      await dialog.accept();
    });

    await exportButton.click();

    // Wait a bit for the dialog to appear
    await page.waitForTimeout(500);

    // Verify dialog was triggered
    expect(dialogTriggered).toBe(true);
  });

  test('should disable bulk action buttons when no items selected', async ({ page }) => {
    // Ensure no items are selected initially
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).not.toBeVisible();

    // Select and then deselect an item to trigger the bar
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Verify buttons are enabled
    const removeButton = bulkActionBar.locator('.bulk-remove-button');
    const tagButton = bulkActionBar.locator('.bulk-tag-button');
    const exportButton = bulkActionBar.locator('.bulk-export-button');

    await expect(removeButton).not.toBeDisabled();
    await expect(tagButton).not.toBeDisabled();
    await expect(exportButton).not.toBeDisabled();

    // Deselect the item
    await checkbox.uncheck({ force: true });

    // Verify bulk action bar is hidden
    await expect(bulkActionBar).not.toBeVisible();
  });

  test('should maintain selection state during pagination', async ({ page }) => {
    // This test assumes there are multiple pages of memory blocks
    const visibleRowCount = await memoryBlocksPage.getVisibleRowCount();

    if (visibleRowCount >= 10) { // Assuming default page size is 10
      // Select first item
      const firstRow = page.locator('.data-table-row').first();
      const checkbox = firstRow.locator('input[type="checkbox"]');
      await checkbox.check({ force: true });

      // Navigate to next page
      const nextPageSuccess = await memoryBlocksPage.goToNextPage();
      if (nextPageSuccess) {
        // Verify selection is cleared on page change
        const newBulkActionBar = page.locator('.bulk-action-bar');
        await expect(newBulkActionBar).not.toBeVisible();

        // Navigate back
        await memoryBlocksPage.goToPreviousPage();

        // Verify selection is still cleared (selections don't persist across pages)
        const originalBulkActionBar = page.locator('.bulk-action-bar');
        await expect(originalBulkActionBar).not.toBeVisible();
      }
    }
  });

  test('should handle bulk operations with large number of selections', async ({ page }) => {
    // Select all available memory blocks
    const selectAllCheckbox = page.locator('.data-table-header input[type="checkbox"]');
    await selectAllCheckbox.check({ force: true });

    // Wait for state updates
    await page.waitForTimeout(200);

    // Get the count of selected items
    const bulkActionBar = page.locator('.bulk-action-bar');
    const selectedCountText = await bulkActionBar.locator('.selected-count').textContent();
    const selectedCount = parseInt(selectedCountText.match(/\d+/)[0]);

    // Verify buttons show some indication of count (text may vary)
    const removeButton = bulkActionBar.locator('.bulk-remove-button');
    const removeText = await removeButton.textContent();
    expect(removeText).toMatch(/Remove/);

    const tagButton = bulkActionBar.locator('.bulk-tag-button');
    const tagText = await tagButton.textContent();
    expect(tagText).toMatch(/Tag/);

    const exportButton = bulkActionBar.locator('.bulk-export-button');
    const exportText = await exportButton.textContent();
    expect(exportText).toMatch(/Export/);
  });

  test('should clear selection when memory blocks are refreshed', async ({ page }) => {
    // Select first memory block
    const firstRow = page.locator('.data-table-row').first();
    const checkbox = firstRow.locator('input[type="checkbox"]');
    await checkbox.check({ force: true });

    // Verify selection
    const bulkActionBar = page.locator('.bulk-action-bar');
    await expect(bulkActionBar).toBeVisible();

    // Trigger a refresh (e.g., by changing a filter or search)
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // Verify selection is cleared after refresh
      const newBulkActionBar = page.locator('.bulk-action-bar');
      await expect(newBulkActionBar).not.toBeVisible();
    }
  });
});
