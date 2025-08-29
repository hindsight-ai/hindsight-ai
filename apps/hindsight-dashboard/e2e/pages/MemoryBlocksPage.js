/**
 * Page Object for Memory Blocks page
 * Provides reusable methods for interacting with memory blocks table and pagination
 */
export class MemoryBlocksPage {
  constructor(page) {
    this.page = page;
    this.tableContainer = page.locator('.memory-block-table-container');
    this.tableRows = page.locator('.memory-block-table-row');
    this.tableHeader = page.locator('.memory-block-table-header');
  }

  /**
   * Navigate to memory blocks page
   */
  async goto() {
    await this.page.goto('/');
    await this.page.waitForURL(/.*\/(|memory-blocks)$/);
    await this.waitForTableLoad();
  }

  /**
   * Wait for table to load completely
   */
  async waitForTableLoad() {
    await this.page.waitForSelector('.memory-block-table-container', { timeout: 10000 });
    await this.page.waitForSelector('.memory-block-table-row', { timeout: 10000 });
  }

  /**
   * Get current page number from indicator
   */
  async getCurrentPage() {
    const pageInput = this.page.locator('.page-input');
    if (await pageInput.isVisible()) {
      const value = await pageInput.inputValue();
      return parseInt(value) || 1;
    }
    // Fallback to text-based detection
    const pageIndicator = this.page.locator('text=/Page \d+/');
    const text = await pageIndicator.textContent();
    const match = text.match(/Page (\d+)/);
    return match ? parseInt(match[1]) : 1;
  }

  /**
   * Get total number of visible rows
   */
  async getVisibleRowCount() {
    return await this.tableRows.count();
  }

  /**
   * Get all memory block IDs currently visible
   */
  async getVisibleMemoryBlockIds() {
    return await this.page.locator('.memory-block-table-row [data-testid*="id"], .memory-block-table-row .id-cell').allTextContents();
  }

  /**
   * Navigate to next page
   */
  async goToNextPage() {
    const nextButton = this.page.locator('button:has-text("Next")');
    if (await nextButton.isVisible() && !(await nextButton.isDisabled())) {
      await nextButton.click();
      await this.page.waitForTimeout(500);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Navigate to previous page
   */
  async goToPreviousPage() {
    const prevButton = this.page.locator('button:has-text("Previous")');
    if (await prevButton.isVisible() && !(await prevButton.isDisabled())) {
      await prevButton.click();
      await this.page.waitForTimeout(500);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Navigate to first page
   */
  async goToFirstPage() {
    const firstButton = this.page.locator('button:has-text("<<")');
    if (await firstButton.isVisible() && !(await firstButton.isDisabled())) {
      await firstButton.click();
      await this.page.waitForTimeout(500);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Navigate to last page
   */
  async goToLastPage() {
    const lastButton = this.page.locator('button:has-text(">>")');
    if (await lastButton.isVisible() && !(await lastButton.isDisabled())) {
      await lastButton.click();
      await this.page.waitForTimeout(500);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Set page size
   */
  async setPageSize(pageSize) {
    const pageSizeSelector = this.page.locator('#per-page-select');
    if (await pageSizeSelector.isVisible()) {
      await pageSizeSelector.selectOption(pageSize.toString());
      await this.page.waitForTimeout(500);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Check if pagination controls are visible
   */
  async arePaginationControlsVisible() {
    const paginationControls = this.page.locator('.pagination');
    const hasControls = await paginationControls.isVisible();

    // Also check for individual navigation buttons
    const nextButton = this.page.locator('button:has-text("Next")');
    const hasNextButton = await nextButton.isVisible();

    return hasControls || hasNextButton;
  }

  /**
   * Check if next button is disabled (indicating last page)
   */
  async isNextButtonDisabled() {
    const nextButton = this.page.locator('button:has-text("Next")');
    return await nextButton.isVisible() && await nextButton.isDisabled();
  }

  /**
   * Check if previous button is disabled (indicating first page)
   */
  async isPreviousButtonDisabled() {
    const prevButton = this.page.locator('button:has-text("Previous")');
    return await prevButton.isVisible() && await prevButton.isDisabled();
  }

  /**
   * Check if first button is disabled (indicating first page)
   */
  async isFirstButtonDisabled() {
    const firstButton = this.page.locator('button:has-text("<<")');
    return await firstButton.isVisible() && await firstButton.isDisabled();
  }

  /**
   * Check if last button is disabled (indicating last page)
   */
  async isLastButtonDisabled() {
    const lastButton = this.page.locator('button:has-text(">>")');
    return await lastButton.isVisible() && await lastButton.isDisabled();
  }

  /**
   * Search/filter memory blocks
   */
  async search(searchTerm) {
    const searchInput = this.page.locator('input[type="search"], input[placeholder*="search"], [data-testid="search-input"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(searchTerm);
      await searchInput.press('Enter');
      await this.page.waitForTimeout(1000);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Sort by column
   */
  async sortByColumn(columnName) {
    const sortableHeader = this.page.locator(`.sortable-header:has-text("${columnName}"), [data-testid*="sort"]:has-text("${columnName}")`);
    if (await sortableHeader.isVisible()) {
      await sortableHeader.click();
      await this.page.waitForTimeout(500);
      await this.waitForTableLoad();
      return true;
    }
    return false;
  }

  /**
   * Get column sort direction
   */
  async getSortDirection(columnName) {
    const header = this.page.locator(`.sortable-header:has-text("${columnName}"), [data-testid*="sort"]:has-text("${columnName}")`);
    const sortArrow = header.locator('.sort-arrow, :has-text("▲"), :has-text("▼")');

    if (await sortArrow.isVisible()) {
      const arrowText = await sortArrow.textContent();
      if (arrowText.includes('▲')) return 'asc';
      if (arrowText.includes('▼')) return 'desc';
    }
    return null;
  }

  /**
   * Resize column
   */
  async resizeColumn(columnIndex, deltaX) {
    const resizeHandle = this.page.locator('.resize-handle, [data-testid="resize-handle"]').nth(columnIndex);
    if (await resizeHandle.isVisible()) {
      await resizeHandle.dragTo(this.page.locator('body'), {
        targetPosition: { x: deltaX, y: 0 }
      });
      await this.page.waitForTimeout(500);
      return true;
    }
    return false;
  }

  /**
   * Get column width
   */
  async getColumnWidth(columnIndex) {
    const column = this.tableRows.first().locator('.data-cell').nth(columnIndex);
    const boundingBox = await column.boundingBox();
    return boundingBox?.width;
  }

  /**
   * Wait for console errors
   */
  async waitForConsoleErrors(timeout = 1000) {
    const errors = [];
    const errorPromise = new Promise((resolve) => {
      const handler = (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      };

      this.page.on('console', handler);
      setTimeout(() => {
        this.page.off('console', handler);
        resolve(errors);
      }, timeout);
    });

    return errorPromise;
  }

  /**
   * Check if page is responsive on mobile
   */
  async setMobileViewport() {
    await this.page.setViewportSize({ width: 375, height: 667 });
    await this.page.waitForTimeout(500);
  }

  /**
   * Test keyboard navigation
   */
  async testKeyboardNavigation() {
    // Focus on pagination container
    const paginationContainer = this.page.locator('.pagination-controls, [data-testid="pagination"]');
    await paginationContainer.focus();

    // Test Tab navigation
    await this.page.keyboard.press('Tab');
    const focusedElement = this.page.locator(':focus');
    return await focusedElement.isVisible();
  }

  /**
   * Get button dimensions for accessibility testing
   */
  async getButtonDimensions(buttonText) {
    const button = this.page.locator(`button:has-text("${buttonText}")`);
    if (await button.isVisible()) {
      return await button.boundingBox();
    }
    return null;
  }

  /**
   * Measure performance
   */
  async measureLoadTime() {
    const startTime = Date.now();
    await this.waitForTableLoad();
    return Date.now() - startTime;
  }

  /**
   * Measure pagination navigation time
   */
  async measureNavigationTime(navigationFunction) {
    const startTime = Date.now();
    const success = await navigationFunction.call(this);
    if (success) {
      await this.waitForTableLoad();
      return Date.now() - startTime;
    }
    return null;
  }
}
