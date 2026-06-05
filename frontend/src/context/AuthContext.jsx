import React, { createContext, useContext, useState, useCallback } from "react";
import { setTokens, clearTokens, setTokenRefreshCallback } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);           // UserOut from API
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);

  // Called after successful login or register→login
  const login = useCallback((tokenResponse) => {
    const { access_token, refresh_token, user: userData } = tokenResponse;
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    setUser(userData);
    setTokens(access_token, refresh_token);
  }, []);

  // Called on auto-refresh (update tokens in context)
  const handleTokenRefresh = useCallback((tokenResponse) => {
    const { access_token, refresh_token, user: userData } = tokenResponse;
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    if (userData) setUser(userData);
    setTokens(access_token, refresh_token);
  }, []);

  // Register the refresh callback so api.js can call back into context
  setTokenRefreshCallback(handleTokenRefresh);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
  }, []);

  const value = {
    user,
    accessToken,
    refreshToken,
    isAuthenticated: !!user,
    isAdmin: user?.role === "admin",
    isMember: user?.role === "member",
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
