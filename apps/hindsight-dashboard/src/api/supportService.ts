import { apiFetch, isGuest } from './http';
import { ApiError } from './errors';

const guardGuest = (action: string) => { if (isGuest()) throw new Error(action); };

const jsonOrThrow = async (resp: Response) => resp.json();

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
