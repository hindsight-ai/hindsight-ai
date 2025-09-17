export const devModeHeaders = (): Record<string, string> => {
  if (typeof process === 'undefined' || typeof window === 'undefined') return {};
  const devMode = (process as any).env?.VITE_DEV_MODE === 'true' || (process as any).env?.DEV === true;
  const devOverride = (window as any).__ENV__?.DEV_MODE === 'true';
  if (!devMode && !devOverride) return {};

  const email = (window as any).__ENV__?.DEV_LOCAL_EMAIL || (process as any).env?.VITE_DEV_LOCAL_EMAIL || 'dev@localhost';
  const name = (window as any).__ENV__?.DEV_LOCAL_NAME || (process as any).env?.VITE_DEV_LOCAL_NAME || 'Development User';
  return {
    'X-Auth-Request-Email': email,
    'X-Auth-Request-User': name,
  };
};
