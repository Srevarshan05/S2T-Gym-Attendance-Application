import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { setTokens, clearTokens, setTokenRefreshCallback, auth as authApi } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("s2t_user");
    try {
      return saved ? JSON.parse(saved) : null;
    } catch (_) {
      return null;
    }
  });
  const [accessToken, setAccessToken] = useState(() => {
    return localStorage.getItem("s2t_access_token") || null;
  });
  const [refreshToken, setRefreshToken] = useState(() => {
    return localStorage.getItem("s2t_refresh_token") || null;
  });
  const [loading, setLoading] = useState(!!localStorage.getItem("s2t_refresh_token"));

  // Called after successful login or register→login
  const login = useCallback((tokenResponse) => {
    const { access_token, refresh_token, user: userData } = tokenResponse;
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    setUser(userData);
    setTokens(access_token, refresh_token);
    
    // Save to localStorage
    localStorage.setItem("s2t_access_token", access_token);
    localStorage.setItem("s2t_refresh_token", refresh_token);
    localStorage.setItem("s2t_user", JSON.stringify(userData));
  }, []);

  // Called on auto-refresh (update tokens in context)
  const handleTokenRefresh = useCallback((tokenResponse) => {
    const { access_token, refresh_token, user: userData } = tokenResponse;
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    setTokens(access_token, refresh_token);
    
    localStorage.setItem("s2t_access_token", access_token);
    localStorage.setItem("s2t_refresh_token", refresh_token);
    
    if (userData) {
      setUser(userData);
      localStorage.setItem("s2t_user", JSON.stringify(userData));
    }
  }, []);

  // Register the refresh callback so api.js can call back into context
  setTokenRefreshCallback(handleTokenRefresh);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    
    // Clear from localStorage
    localStorage.removeItem("s2t_access_token");
    localStorage.removeItem("s2t_refresh_token");
    localStorage.removeItem("s2t_user");
  }, []);

  // Silent refresh on app mount to restore session
  useEffect(() => {
    const savedAccess = localStorage.getItem("s2t_access_token");
    const savedRefresh = localStorage.getItem("s2t_refresh_token");
    
    if (savedRefresh) {
      setTokens(savedAccess, savedRefresh);
      authApi.refresh(savedRefresh)
        .then((data) => {
          handleTokenRefresh(data);
        })
        .catch(() => {
          // If refresh token is expired/revoked, force logout
          logout();
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [handleTokenRefresh, logout]);

  const value = {
    user,
    accessToken,
    refreshToken,
    isAuthenticated: !!user,
    isAdmin: user?.role === "admin",
    isMember: user?.role === "member",
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
