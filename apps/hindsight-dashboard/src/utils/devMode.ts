const isLocalHost = (): boolean => {
  if (typeof window === 'undefined') return false;
  const hostname = window.location.hostname?.toLowerCase() || '';
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'host.docker.internal' || hostname === '::1';
};

export const devModeHeaders = (): Record<string, string> => {
  if (typeof window === 'undefined') return {};

  // Vite exposes import.meta.env with DEV and VITE_* flags
  let viteEnv: any;
  try {
    // eslint-disable-next-line no-eval
    viteEnv = (Function('return import.meta.env')()) as any;
  } catch {
    viteEnv = undefined;
  }

  const viteDevFlag = viteEnv?.DEV === true;
  const viteDevMode = viteEnv?.VITE_DEV_MODE === 'true';
  const runtimeDevMode = (window as any).__ENV__?.DEV_MODE === 'true';

  if (!isLocalHost()) {
    return {};
  }

  if (!viteDevFlag && !viteDevMode && !runtimeDevMode) {
    return {};
  }

  const email = (window as any).__ENV__?.DEV_LOCAL_EMAIL || viteEnv?.VITE_DEV_LOCAL_EMAIL || 'dev@localhost';
  const name = (window as any).__ENV__?.DEV_LOCAL_NAME || viteEnv?.VITE_DEV_LOCAL_NAME || 'Development User';

  if (typeof console !== 'undefined' && console.debug) {
    console.debug('[devModeHeaders] applying dev auth headers', { email, name, hostname: window.location.hostname });
  }

  return {
    'X-Auth-Request-Email': email,
    'X-Auth-Request-User': name,
  };
};
