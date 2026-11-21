import React, { createContext, useContext, useState, useEffect } from "react";
import { api, session, onUnauthorized } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(session.user);
  const [token, setToken] = useState(session.token);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Listen for 401 unauthorized
    const unsubscribe = onUnauthorized(() => {
      setUser(null);
      setToken(null);
    });

    // Check token and verify user profile
    if (session.token) {
      api.auth
        .profile()
        .then((profile) => {
          setUser(profile);
          session.user = profile;
        })
        .catch(() => {
          // Token expired or invalid
          session.clear();
          setUser(null);
          setToken(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }

    return () => unsubscribe();
  }, []);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const res = await api.auth.login(email, password);
      setToken(res.access_token);
      const profile = session.user;
      setUser(profile);
      return profile;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email, password) => {
    setIsLoading(true);
    try {
      await api.auth.register(email, password);
      return await login(email, password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // ignore logout network errors
    } finally {
      session.clear();
      setUser(null);
      setToken(null);
    }
  };

  const quickDemoLogin = async () => {
    return login("demo@example.com", "DemoPass123");
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token,
    isLoading,
    login,
    register,
    logout,
    quickDemoLogin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
