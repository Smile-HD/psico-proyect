/**
 * TestPsico — browser session helpers.
 *
 * The token lives in localStorage so client pages can call the API directly.
 * Roles are read from the JWT payload for UI gating only (usability); the
 * server remains the authority for every permission decision.
 */

import { apiBase, apiFetch, ApiError } from "./api";

const TOKEN_KEY = "psico_token";
const USER_KEY = "psico_user";

export type SessionUser = {
  username: string;
  roles: string[];
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getSessionUser(): SessionUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionUser;
  } catch {
    return null;
  }
}

export function hasRole(role: string): boolean {
  return getSessionUser()?.roles.includes(role) ?? false;
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

function decodeRoles(accessToken: string): string[] {
  try {
    const payload = accessToken.split(".")[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    const roles = decoded.roles ?? decoded.role ?? [];
    return Array.isArray(roles) ? roles.map(String) : [String(roles)];
  } catch {
    return [];
  }
}

export async function login(username: string, password: string): Promise<SessionUser> {
  const result = await apiFetch<{ access_token: string }>("/api/v1/auth/login", {
    method: "POST",
    token: "", // login is public
    body: { username, password },
  });
  const user: SessionUser = {
    username,
    roles: decodeRoles(result.access_token),
  };
  window.localStorage.setItem(TOKEN_KEY, result.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

export { apiBase };

// Re-exported so UI pages can surface server errors uniformly.
export { ApiError };
