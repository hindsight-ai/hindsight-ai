import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import authService from '../api/authService';

const AuthContext = createContext({
  user: null,
  loading: true,
  refresh: async () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const info = await authService.getCurrentUser();
      setUser(info);
    } catch (err) {
      // In dev, unauthenticated is acceptable; keep user null
      console.error('Auth refresh error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // Optionally revalidate when tab becomes visible again
    const onVisibility = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);

  const value = useMemo(() => ({ user, loading, refresh }), [user, loading]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

