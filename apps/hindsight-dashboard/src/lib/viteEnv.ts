// Wrapper for Vite `import.meta.env` values to make usage testable and safe in Jest.
// Use this module instead of referencing `import.meta.env` directly.

export const VITE_DEV_MODE = typeof import.meta !== 'undefined' && typeof import.meta.env !== 'undefined'
  ? (import.meta.env.VITE_DEV_MODE === 'true' || Boolean((import.meta.env as any).DEV))
  : false;

export const VITE_VERSION = typeof import.meta !== 'undefined' && typeof import.meta.env !== 'undefined'
  ? (import.meta.env.VITE_VERSION ?? 'unknown')
  : 'unknown';

export const VITE_BUILD_SHA = typeof import.meta !== 'undefined' && typeof import.meta.env !== 'undefined'
  ? (import.meta.env.VITE_BUILD_SHA ?? 'unknown')
  : 'unknown';

export const VITE_BUILD_TIMESTAMP = typeof import.meta !== 'undefined' && typeof import.meta.env !== 'undefined'
  ? (import.meta.env.VITE_BUILD_TIMESTAMP ?? 'unknown')
  : 'unknown';

export const VITE_DASHBOARD_IMAGE_TAG = typeof import.meta !== 'undefined' && typeof import.meta.env !== 'undefined'
  ? (import.meta.env.VITE_DASHBOARD_IMAGE_TAG ?? 'unknown')
  : 'unknown';

// Generic accessor to raw env if necessary
export const rawImportMetaEnv = typeof import.meta !== 'undefined' && typeof import.meta.env !== 'undefined'
  ? import.meta.env
  : {};

export default {
  VITE_DEV_MODE,
  VITE_VERSION,
  VITE_BUILD_SHA,
  VITE_BUILD_TIMESTAMP,
  VITE_DASHBOARD_IMAGE_TAG,
  rawImportMetaEnv,
};
