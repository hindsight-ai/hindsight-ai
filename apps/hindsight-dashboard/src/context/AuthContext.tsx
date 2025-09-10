import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import authService, { CurrentUserInfo } from '../api/authService';

interface AuthContextValue {
  user: CurrentUserInfo | null;
  loading: boolean;
  guest: boolean;
  enterGuestMode: () => void;
  exitGuestMode: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<CurrentUserInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [guest, setGuest] = useState<boolean>(false);

  const refresh = async () => {
    const info = await authService.getCurrentUser();
    setUser(info);
    if (info?.authenticated) {
      setGuest(false);
      try { sessionStorage.removeItem('GUEST_MODE'); } catch {}
    }
    setLoading(false);
  };

  useEffect(() => {
    const storedGuest = sessionStorage.getItem('GUEST_MODE');
    if (storedGuest === 'true') setGuest(true);
    refresh();
    const onVisibility = () => { if (document.visibilityState === 'visible') refresh(); };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);

  const enterGuestMode = () => { setGuest(true); sessionStorage.setItem('GUEST_MODE', 'true'); };
  const exitGuestMode = () => { setGuest(false); sessionStorage.removeItem('GUEST_MODE'); };

  const value = useMemo<AuthContextValue>(() => ({ user, loading, guest, enterGuestMode, exitGuestMode, refresh }), [user, loading, guest]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
