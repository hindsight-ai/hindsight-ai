import { apiFetch, guardGuest, jsonOrThrow } from './http';
import { ApiError } from './errors';

export const contactSupport = async (payload: Record<string, any>) => {
  guardGuest('Sign in to contact support.');
  try {
    const resp = await apiFetch('/support/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return jsonOrThrow(resp);
  } catch (err) {
    // Preserve the 429 detail message for the caller
    if (err instanceof ApiError && err.status === 429) {
      throw new Error('Please wait before sending another support request.');
    }
    throw err;
  }
};

const supportService = {
  contactSupport,
};

export default supportService;
