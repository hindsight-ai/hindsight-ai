// Use CommonJS require for setup to avoid mixing ESM/CJS in Jest setup
require('@testing-library/jest-dom');

// Default URL for JSDOM to avoid URL-related errors
if (typeof window !== 'undefined' && !window.location) {
  delete global.window;
}
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'location', {
    value: new URL('http://localhost/'),
    writable: true,
  });
}

// Provide a default fetch stub for tests that spy on it
if (typeof global.fetch === 'undefined') {
  // eslint-disable-next-line no-undef
  global.fetch = jest.fn();
}

// Polyfill TextEncoder/TextDecoder for react-router in Jest environment
try {
  // Destructure TextEncoder/TextDecoder from util if available (Node >= 11)
  const { TextEncoder, TextDecoder } = require('util');
  if (typeof global.TextEncoder === 'undefined' && typeof TextEncoder !== 'undefined') {
    global.TextEncoder = TextEncoder;
  }
  if (typeof global.TextDecoder === 'undefined' && typeof TextDecoder !== 'undefined') {
    global.TextDecoder = TextDecoder;
  }
} catch (e) {
  // ignore if util/TextEncoder not available
}

// Mock ESM-only packages that Jest cannot transform (e.g. react-resizable-panels)
// This creates a simple CommonJS-compatible stub so imports succeed during tests.
try {
  // Only set up mocks if Jest globals are available
  if (typeof jest !== 'undefined') {
    jest.mock('react-resizable-panels', () => ({
      PanelGroup: ({ children }) => children || null,
      Panel: ({ children }) => children || null,
      PanelResizeHandle: () => null,
    }));
    // Provide a predictable mock for our viteEnv wrapper used across components
    jest.mock('./src/lib/viteEnv', () => ({
      VITE_DEV_MODE: false,
      VITE_VERSION: 'test',
      VITE_BUILD_SHA: 'test-sha',
      VITE_BUILD_TIMESTAMP: 'test-ts',
      VITE_DASHBOARD_IMAGE_TAG: 'test-tag',
      rawImportMetaEnv: {},
    }));
  }
} catch (e) {
  // ignore in environments without jest
}
