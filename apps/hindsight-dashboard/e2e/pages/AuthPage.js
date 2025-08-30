/**
 * Authentication Page Object for Hindsight Dashboard
 *
 * This page object encapsulates authentication-related UI interactions
 * and provides reusable methods for authentication testing.
 */

export class AuthPage {
  constructor(page) {
    this.page = page;
  }

  /**
   * Navigate to the dashboard
   */
  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Perform login/authentication flow
   * This method handles the authentication process for testing
   */
  async login() {
    // For testing purposes, we'll simulate a successful authentication
    // by mocking the user info response
    const mockUserInfo = {
      email: 'test@example.com',
      user: 'testuser',
      authenticated: true
    };

    // Mock the user info API response
    await this.page.route('**/user-info', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUserInfo)
      });
    });

    // Navigate to trigger authentication check
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');

    // Wait for authentication to complete
    await this.waitForAuthState();
  }

  /**
   * Clear authentication state (cookies, permissions)
   */
  async clearAuthState() {
    await this.page.context().clearCookies();
    await this.page.context().clearPermissions();
  }

  /**
   * Check if user is authenticated by looking for user info elements
   * @returns {boolean} True if authenticated
   */
  async isAuthenticated() {
    const userInfo = this.page.locator('.user-info, .user-email').first();
    return await userInfo.isVisible();
  }

  /**
   * Get user information from the UI
   * @returns {string} User email or username
   */
  async getUserInfo() {
    const userInfo = this.page.locator('.user-info, .user-email').first();
    if (await userInfo.isVisible()) {
      return await userInfo.textContent();
    }
    return null;
  }

  /**
   * Check if authentication is required (auth UI is shown)
   * @returns {boolean} True if auth is required
   */
  async isAuthRequired() {
    const authRequired = this.page.locator('text=/Authentication Required|Please sign in|Login/i');
    const signInButton = this.page.locator('button:has-text("Sign In"), a:has-text("Sign In")');
    return (await authRequired.count() > 0) || (await signInButton.count() > 0);
  }

  /**
   * Find and click sign in button
   * @returns {boolean} True if sign in button was found and clicked
   */
  async clickSignIn() {
    const signInButton = this.page.locator('button:has-text("Sign In"), a:has-text("Sign In")').first();
    if (await signInButton.isVisible()) {
      await signInButton.click();
      return true;
    }
    return false;
  }

  /**
   * Find and click logout button
   * @returns {boolean} True if logout button was found and clicked
   */
  async clickLogout() {
    const logoutButton = this.page.locator('button:has-text("Logout"), a:has-text("Logout"), button:has-text("Sign Out")').first();
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      return true;
    }
    return false;
  }

  /**
   * Check if logout was successful
   * @returns {boolean} True if logged out
   */
  async isLoggedOut() {
    const userInfo = this.page.locator('.user-info, .user-email').first();
    const logoutMessage = this.page.locator('text=/logged out|Logged out|signed out/i');
    const currentUrl = this.page.url();

    return !await userInfo.isVisible() ||
           await logoutMessage.isVisible() ||
           currentUrl.includes('login') ||
           currentUrl.includes('auth');
  }

  /**
   * Check for authentication errors
   * @returns {Array} Array of error messages found
   */
  async getAuthErrors() {
    const errorMessages = this.page.locator('text=/error|Error|failed|Failed/i');
    const errors = [];

    const count = await errorMessages.count();
    for (let i = 0; i < count; i++) {
      const errorText = await errorMessages.nth(i).textContent();
      // Filter out technical errors, only include user-friendly ones
      if (!errorText.match(/undefined|null|500|404|exception/i)) {
        errors.push(errorText);
      }
    }

    return errors;
  }

  /**
   * Check for session expired messages
   * @returns {boolean} True if session expired message found
   */
  async hasSessionExpired() {
    const sessionExpired = this.page.locator('text=/session expired|Session expired|login again/i');
    return await sessionExpired.count() > 0;
  }

  /**
   * Get authentication-related cookies
   * @returns {Array} Array of auth-related cookies
   */
  async getAuthCookies() {
    const cookies = await this.page.context().cookies();
    return cookies.filter(cookie =>
      cookie.name.toLowerCase().includes('auth') ||
      cookie.name.toLowerCase().includes('token') ||
      cookie.name.toLowerCase().includes('session')
    );
  }

  /**
   * Get authentication-related localStorage keys
   * @returns {Array} Array of auth-related localStorage keys
   */
  async getAuthLocalStorage() {
    const localStorage = await this.page.evaluate(() => {
      return Object.keys(localStorage);
    });

    return localStorage.filter(key =>
      key.toLowerCase().includes('auth') ||
      key.toLowerCase().includes('token') ||
      key.toLowerCase().includes('session')
    );
  }

  /**
   * Get authentication-related sessionStorage keys
   * @returns {Array} Array of auth-related sessionStorage keys
   */
  async getAuthSessionStorage() {
    const sessionStorage = await this.page.evaluate(() => {
      return Object.keys(sessionStorage);
    });

    return sessionStorage.filter(key =>
      key.toLowerCase().includes('auth') ||
      key.toLowerCase().includes('token') ||
      key.toLowerCase().includes('session')
    );
  }

  /**
   * Mock OAuth response for testing
   * @param {Object} userInfo User information to mock
   */
  async mockOAuthResponse(userInfo = { email: 'test@example.com', authenticated: true }) {
    await this.page.route('**/user-info', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(userInfo)
      });
    });
  }

  /**
   * Mock failed OAuth response for testing
   * @param {number} status HTTP status code
   * @param {Object} errorResponse Error response body
   */
  async mockFailedOAuthResponse(status = 401, errorResponse = { error: 'Authentication failed' }) {
    await this.page.route('**/user-info', async route => {
      await route.fulfill({
        status: status,
        contentType: 'application/json',
        body: JSON.stringify(errorResponse)
      });
    });
  }

  /**
   * Simulate OAuth login flow
   * @param {Object} userInfo User information for mock response
   */
  async simulateOAuthLogin(userInfo = { email: 'test@example.com', authenticated: true }) {
    await this.mockOAuthResponse(userInfo);
    await this.goto();
  }

  /**
   * Wait for authentication state to stabilize
   */
  async waitForAuthState() {
    await this.page.waitForLoadState('networkidle');
    // Wait a bit more for any authentication checks to complete
    await this.page.waitForTimeout(1000);
  }

  /**
   * Navigate to different pages while maintaining auth state
   * @param {string} path Path to navigate to
   */
  async navigateAuthenticated(path) {
    await this.page.goto(path);
    await this.waitForAuthState();
  }

  /**
   * Test session persistence across page refresh
   * @returns {boolean} True if session persisted
   */
  async testSessionPersistence() {
    const initialUserInfo = await this.getUserInfo();
    if (!initialUserInfo) return false;

    await this.page.reload();
    await this.waitForAuthState();

    const refreshedUserInfo = await this.getUserInfo();
    return refreshedUserInfo === initialUserInfo;
  }

  /**
   * Test session persistence across navigation
   * @param {string} path Path to navigate to
   * @returns {boolean} True if session persisted
   */
  async testSessionPersistenceAcrossNavigation(path) {
    const initialUserInfo = await this.getUserInfo();
    if (!initialUserInfo) return false;

    await this.navigateAuthenticated(path);
    const navigatedUserInfo = await this.getUserInfo();

    if (navigatedUserInfo !== initialUserInfo) return false;

    // Navigate back
    await this.page.goto('/');
    await this.waitForAuthState();

    const finalUserInfo = await this.getUserInfo();
    return finalUserInfo === initialUserInfo;
  }

  /**
   * Test multiple tab session synchronization
   * @param {BrowserContext} context Browser context for new tabs
   * @returns {boolean} True if sessions are synchronized
   */
  async testMultiTabSynchronization(context) {
    const initialUserInfo = await this.getUserInfo();
    if (!initialUserInfo) return false;

    // Open new tab
    const newPage = await context.newPage();
    const newAuthPage = new AuthPage(newPage);
    await newAuthPage.goto();

    const newTabUserInfo = await newAuthPage.getUserInfo();

    // Clean up
    await newPage.close();

    return newTabUserInfo === initialUserInfo;
  }

  /**
   * Test concurrent session handling
   * @param {BrowserContext} context Browser context for new tabs
   * @param {number} numTabs Number of concurrent tabs to test
   * @returns {boolean} True if all sessions are consistent
   */
  async testConcurrentSessions(context, numTabs = 3) {
    const initialUserInfo = await this.getUserInfo();
    if (!initialUserInfo) return false;

    const tabs = [];
    const authPages = [];

    // Open multiple tabs
    for (let i = 0; i < numTabs; i++) {
      const newPage = await context.newPage();
      const newAuthPage = new AuthPage(newPage);
      await newAuthPage.goto();
      tabs.push(newPage);
      authPages.push(newAuthPage);
    }

    // Check all tabs have consistent auth state
    let allConsistent = true;
    for (const authPage of authPages) {
      const userInfo = await authPage.getUserInfo();
      if (userInfo !== initialUserInfo) {
        allConsistent = false;
        break;
      }
    }

    // Clean up
    for (const tab of tabs) {
      await tab.close();
    }

    return allConsistent;
  }
}
