import '@testing-library/jest-dom';

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
  const util = require('util');
  if (typeof global.TextEncoder === 'undefined') {
    global.TextEncoder = util.TextEncoder;
  }
  if (typeof global.TextDecoder === 'undefined') {
    global.TextDecoder = util.TextDecoder;
  }
} catch {}
