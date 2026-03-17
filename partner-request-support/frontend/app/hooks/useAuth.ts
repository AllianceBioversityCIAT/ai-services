'use client';

import { useState } from 'react';
import { authService } from '../services/authService';
import { AuthUser, LoginCredentials } from '../types/auth.types';

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setLoginError(null);

    try {
      const { access_token, user } = await authService.login(credentials);
      setAuthToken(access_token);
      setAuthUser(user);
      setIsAuthenticated(true);
      return true;
    } catch (err: any) {
      const errorMessage = authService.formatErrorMessage(err);
      setLoginError(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setAuthUser(null);
    setAuthToken(null);
  };

  return {
    isAuthenticated,
    authUser,
    authToken,
    loginError,
    isLoading,
    login,
    logout,
  };
};
