import { SignJWT, jwtVerify } from "jose";
import bcrypt from "bcryptjs";
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import { env } from "process";

export interface JWTPayload {
  email: string;
  role: string;
  iat: number;
  exp: number;
}

// Hash password
export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 12);
}

// Verify password
export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// Create JWT token
export async function createToken(
  email: string,
  role: string
): Promise<string> {
  const secret = new TextEncoder().encode(env.JWT_SECRET);

  return await new SignJWT({ email, role })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("7d")
    .sign(secret);
}

// Verify JWT token
export async function verifyToken(token: string): Promise<JWTPayload | null> {
  try {
    const secret = new TextEncoder().encode(env.JWT_SECRET);
    const { payload } = await jwtVerify(token, secret);
    return {
      email: payload.email as string,
      role: payload.role as string,
      iat: payload.iat as number,
      exp: payload.exp as number,
    };
  } catch {
    return null;
  }
}

// Set session cookie
export function setSessionCookie(token: string) {
  const cookieStore = cookies();
  const isProduction = process.env.NODE_ENV === "production";

  cookieStore.set("session", token, {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 60 * 60, // 7 days
  });
}

// Clear session cookie
export function clearSessionCookie() {
  const cookieStore = cookies();
  cookieStore.delete("session");
}

// Get session from cookies
export async function getSession(): Promise<JWTPayload | null> {
  const cookieStore = cookies();
  const sessionCookie = cookieStore.get("session");

  if (!sessionCookie) {
    return null;
  }

  return await verifyToken(sessionCookie.value);
}

// Get session from request (for middleware)
export async function getSessionFromRequest(
  request: NextRequest
): Promise<JWTPayload | null> {
  const sessionCookie = request.cookies.get("session");

  if (!sessionCookie) {
    return null;
  }

  return await verifyToken(sessionCookie.value);
}
