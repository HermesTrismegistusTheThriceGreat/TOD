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

// Create auth client with base URL from environment
export const authClient = createAuthClient({
  baseURL: import.meta.env.VITE_AUTH_URL || "http://localhost:9404",
});

// Export typed methods for convenience
export const {
  signIn,
  signUp,
  signOut,
  useSession,
  getSession,
} = authClient;
