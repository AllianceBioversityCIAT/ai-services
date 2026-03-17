import axios from 'axios';
import { AuthResponse, LoginCredentials } from '../types/auth.types';

const AUTH_API_URL = 'https://clarisatest-back.ciat.cgiar.org/auth';

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await axios.post<AuthResponse>(
      `${AUTH_API_URL}/login`,
      {
        login: credentials.email,
        password: credentials.password,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  },

  formatErrorMessage(err: any): string {
    let errorMsg = 'Unable to sign in. Please try again.';

    if (err.response) {
      const status = err.response.status;

      if (status === 401 || status === 403) {
        errorMsg = 'Invalid email or password. Please check your credentials.';
      } else if (status === 500) {
        errorMsg = 'Invalid credentials. Please verify your email and password.';
      } else if (status >= 500) {
        errorMsg = 'Authentication service is temporarily unavailable. Please try again later.';
      } else {
        const responseMsg = err.response.data?.message || err.response.data?.detail;
        if (responseMsg && responseMsg !== 'Http Exception' && !responseMsg.includes('Exception')) {
          errorMsg = responseMsg;
        }
      }
    } else if (err.request) {
      errorMsg = 'Unable to connect to authentication service. Please check your internet connection.';
    }

    return errorMsg;
  },
};
