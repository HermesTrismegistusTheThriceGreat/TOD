/**
 * Better Auth Client
 *
 * Vue.js client for Better Auth authentication service.
 * Provides reactive session management and authentication methods.
 *
 * Usage:
 *   import { signIn, signUp, signOut, useSession } from '@/services/authClient'
 */

import { createAuthClient } from "better-auth/vue";

// Create auth client
// In development, use relative URL so requests go through Vite proxy (same-origin cookies)
// In production, use the full auth URL
const isDev = import.meta.env.DEV;
const authBaseURL = isDev ? "" : (import.meta.env.VITE_AUTH_URL || "http://localhost:9404");

// Debug logging for auth configuration
console.log("[AuthClient] Environment:", isDev ? "development" : "production");
console.log("[AuthClient] VITE_AUTH_URL:", import.meta.env.VITE_AUTH_URL);
console.log("[AuthClient] Using baseURL:", authBaseURL || "(empty - using relative URLs)");

export const authClient = createAuthClient({
  baseURL: authBaseURL,
  fetchOptions: {
    credentials: "include", // Required for cookie handling
  },
});

// Export typed methods for convenience
export const {
  signIn,
  signUp,
  signOut,
  useSession,
  getSession,
} = authClient;
