/**
 * Page Object for Memory Block Detail page
 * Provides reusable methods for interacting with memory block detail views
 */
export class MemoryBlockDetailPage {
  constructor(page) {
    this.page = page;
    this.detailContainer = page.locator('.memory-block-detail-container');
    this.backButton = page.locator('button:has-text("Back to List")');
    this.editButton = page.locator('button:has-text("Edit")');
    this.saveButton = page.locator('button:has-text("Save Changes")');
    this.cancelButton = page.locator('button:has-text("Cancel")');
    this.deleteButton = page.locator('button:has-text("Delete")');
  }

  /**
   * Navigate to memory block detail page by ID
   */
  async goto(memoryBlockId) {
    await this.page.goto(`/memory-blocks/${memoryBlockId}`);
    // Wait for either the detail container or an error message
    await Promise.race([
      this.page.waitForSelector('.memory-block-detail-container', { timeout: 10000 }),
      this.page.waitForSelector('p:has-text("Error")', { timeout: 10000 }),
      this.page.waitForSelector('p:has-text("Memory block not found")', { timeout: 10000 })
    ]);
  }

  /**
   * Wait for detail page to load completely
   */
  async waitForDetailLoad() {
    await this.page.waitForSelector('.memory-block-detail-container', { timeout: 10000 });
    await this.page.waitForSelector('.detail-item', { timeout: 10000 });
  }

  /**
   * Get memory block ID from detail view
   */
  async getMemoryBlockId() {
    const idElement = this.page.locator('.detail-item:has(.detail-label:has-text("ID")) .detail-value').first();
    return await idElement.textContent();
  }

  /**
   * Get memory block agent ID from detail view
   */
  async getAgentId() {
    const agentIdElement = this.page.locator('.detail-item:has(.detail-label:has-text("Agent ID")) .detail-value').first();
    return await agentIdElement.textContent();
  }

  /**
   * Get memory block conversation ID from detail view
   */
  async getConversationId() {
    const conversationIdElement = this.page.locator('.detail-item:has(.detail-label:has-text("Conversation ID")) .detail-value').first();
    return await conversationIdElement.textContent();
  }

  /**
   * Get creation date from detail view
   */
  async getCreationDate() {
    const creationDateElement = this.page.locator('.detail-item:has(.detail-label:has-text("Creation Date")) .detail-value').first();
    const text = await creationDateElement.textContent();
    return text === 'N/A' ? null : text;
  }

  /**
   * Get feedback score from detail view
   */
  async getFeedbackScore() {
    const feedbackScoreElement = this.page.locator('.detail-item:has(.detail-label:has-text("Feedback Score")) .detail-value').first();
    const text = await feedbackScoreElement.textContent();
    return text === 'N/A' ? null : text;
  }

  /**
   * Get retrieval count from detail view
   */
  async getRetrievalCount() {
    const retrievalCountElement = this.page.locator('.detail-item:has(.detail-label:has-text("Retrieval Count")) .detail-value').first();
    const text = await retrievalCountElement.textContent();
    return text === 'N/A' ? null : text;
  }

  /**
   * Get lessons learned content from detail view
   */
  async getLessonsLearned() {
    const lessonsLearnedElement = this.page.locator('.detail-item:has(.detail-label:has-text("Lessons Learned")) .detail-value').first();
    return await lessonsLearnedElement.textContent();
  }

  /**
   * Get errors content from detail view
   */
  async getErrors() {
    const errorsElement = this.page.locator('.detail-item:has(.detail-label:has-text("Errors")) .detail-value').first();
    return await errorsElement.textContent();
  }

  /**
   * Get external history link from detail view
   */
  async getExternalHistoryLink() {
    const linkElement = this.page.locator('.detail-item:has(.detail-label:has-text("External History Link")) .detail-value').first();
    return await linkElement.textContent();
  }

  /**
   * Get metadata from detail view
   */
  async getMetadata() {
    const metadataElement = this.page.locator('.detail-item:has(.detail-label:has-text("Metadata")) .detail-value pre').first();
    const text = await metadataElement.textContent();
    return text === 'N/A' ? null : text;
  }

  /**
   * Get keywords from detail view
   */
  async getKeywords() {
    const keywordsElement = this.page.locator('.detail-item:has(.detail-label:has-text("Keywords")) .detail-value').first();
    return await keywordsElement.textContent();
  }

  /**
   * Check if all expected detail fields are visible
   */
  async verifyAllDetailFieldsVisible() {
    const fields = [
      'ID',
      'Agent ID',
      'Conversation ID',
      'Creation Date',
      'Feedback Score',
      'Retrieval Count',
      'Lessons Learned',
      'Errors',
      'External History Link',
      'Metadata',
      'Keywords'
    ];

    for (const field of fields) {
      const fieldLocator = this.page.locator(`.detail-item:has(.detail-label:has-text("${field}"))`).first();
      if (!(await fieldLocator.isVisible())) {
        throw new Error(`Field "${field}" is not visible`);
      }
    }
    return true;
  }

  /**
   * Click the back to list button
   */
  async clickBackToList() {
    await this.backButton.click();
    await this.page.waitForURL(/.*\/(|memory-blocks)$/, { timeout: 10000 });
  }

  /**
   * Click the edit button to enter edit mode
   */
  async clickEdit() {
    await this.editButton.click();
    await this.page.waitForSelector('button:has-text("Save Changes")', { timeout: 5000 });
  }

  /**
   * Check if page is in edit mode
   */
  async isInEditMode() {
    return await this.saveButton.isVisible();
  }

  /**
   * Click the cancel button to exit edit mode
   */
  async clickCancel() {
    await this.cancelButton.click();
    await this.page.waitForSelector('button:has-text("Edit")', { timeout: 5000 });
  }

  /**
   * Update lessons learned in edit mode
   */
  async updateLessonsLearned(newLessons) {
    const textarea = this.page.locator('textarea[name="lessons_learned"]');
    await textarea.fill(newLessons);
  }

  /**
   * Update errors in edit mode
   */
  async updateErrors(newErrors) {
    const textarea = this.page.locator('textarea[name="errors"]');
    await textarea.fill(newErrors);
  }

  /**
   * Update external history link in edit mode
   */
  async updateExternalHistoryLink(newLink) {
    const input = this.page.locator('input[name="external_history_link"]');
    await input.fill(newLink);
  }

  /**
   * Update feedback score in edit mode
   */
  async updateFeedbackScore(newScore) {
    const input = this.page.locator('input[name="feedback_score"]');
    await input.fill(newScore.toString());
  }

  /**
   * Click save changes button
   */
  async clickSaveChanges() {
    await this.saveButton.click();
    await this.page.waitForSelector('button:has-text("Edit")', { timeout: 10000 });
  }

  /**
   * Click delete button and confirm deletion
   */
  async clickDeleteAndConfirm() {
    // Mock the confirm dialog
    this.page.on('dialog', async dialog => {
      await dialog.accept();
    });

    await this.deleteButton.click();
    await this.page.waitForURL(/.*\/(|memory-blocks)$/, { timeout: 10000 });
  }

  /**
   * Test copy functionality for a specific field
   */
  async testCopyFunctionality(fieldName) {
    // Verify the copy button exists for the field
    const copyButton = this.page.locator(`.detail-item:has(.detail-label:has-text("${fieldName}")) .copy-button`);
    return await copyButton.isVisible();
  }

  /**
   * Click copy button for a specific field
   */
  async clickCopyButton(fieldName) {
    const copyButton = this.page.locator(`.detail-item:has(.detail-label:has-text("${fieldName}")) .copy-button`);
    if (await copyButton.isVisible()) {
      await copyButton.click();
      return true;
    }
    return false;
  }

  /**
   * Navigate to next memory block (if navigation exists)
   */
  async navigateToNextBlock() {
    const nextButton = this.page.locator('button:has-text("Next")');
    if (await nextButton.isVisible()) {
      await nextButton.click();
      await this.waitForDetailLoad();
      return true;
    }
    return false;
  }

  /**
   * Navigate to previous memory block (if navigation exists)
   */
  async navigateToPreviousBlock() {
    const prevButton = this.page.locator('button:has-text("Previous")');
    if (await prevButton.isVisible()) {
      await prevButton.click();
      await this.waitForDetailLoad();
      return true;
    }
    return false;
  }

  /**
   * Check if navigation buttons are present
   */
  async hasNavigationButtons() {
    const nextButton = this.page.locator('button:has-text("Next")');
    const prevButton = this.page.locator('button:has-text("Previous")');
    return (await nextButton.isVisible()) || (await prevButton.isVisible());
  }

  /**
   * Get all visible field labels
   */
  async getVisibleFieldLabels() {
    const labels = await this.page.locator('.detail-label').allTextContents();
    return labels;
  }

  /**
   * Verify page title contains memory block info
   */
  async verifyPageTitle() {
    const title = await this.page.title();
    return title.includes('Memory Block') || title.includes('Detail');
  }

  /**
   * Check for loading state
   */
  async isLoading() {
    const loadingText = this.page.locator('text=/Loading/');
    return await loadingText.isVisible();
  }

  /**
   * Check for error state
   */
  async hasError() {
    const errorText = this.page.locator('text=/Error/');
    return await errorText.isVisible();
  }

  /**
   * Get error message if present
   */
  async getErrorMessage() {
    const errorElement = this.page.locator('p:has-text("Error")');
    return await errorElement.textContent();
  }
}
