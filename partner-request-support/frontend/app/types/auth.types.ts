export interface AuthUser {
  id: number;
  username: string;
  name: string;
  email: string;
  permissions: string[];
}

export interface AuthResponse {
  access_token: string;
  user: AuthUser;
}

export interface LoginCredentials {
  email: string;
  password: string;
}
