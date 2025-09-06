import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import authService from '../api/authService';

const AuthContext = createContext({
  user: null,
  loading: true,
  guest: false,
  enterGuestMode: () => {},
  exitGuestMode: () => {},
  refresh: async () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [guest, setGuest] = useState(false);

  const refresh = async () => {
    const info = await authService.getCurrentUser();
    setUser(info);
    // If user is authenticated, automatically exit guest mode
    if (info && info.authenticated) {
      setGuest(false);
      try { sessionStorage.removeItem('GUEST_MODE'); } catch {}
    }
    setLoading(false);
  };

  useEffect(() => {
    // Restore guest mode from session storage
    const storedGuest = sessionStorage.getItem('GUEST_MODE');
    if (storedGuest === 'true') {
      setGuest(true);
    }
    refresh();
    // Optionally revalidate when tab becomes visible again
    const onVisibility = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);

  const enterGuestMode = () => {
    setGuest(true);
    sessionStorage.setItem('GUEST_MODE', 'true');
  };
  const exitGuestMode = () => {
    setGuest(false);
    sessionStorage.removeItem('GUEST_MODE');
  };

  const value = useMemo(() => ({ user, loading, guest, enterGuestMode, exitGuestMode, refresh }), [user, loading, guest]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
