/**
 * Authentication Store
 *
 * Pinia store for managing user authentication state using Better Auth.
 * Provides reactive session data, authentication status, and auth actions.
 *
 * State:
 * - session: Reactive Better Auth session object
 * - isAuthenticated: Whether user is logged in
 * - user: Current user object (null if not authenticated)
 * - isLoading: Whether session is being loaded
 *
 * Actions:
 * - signIn(email, password): Sign in with email and password
 * - signUp(name, email, password): Create new user account
 * - signOut(): Sign out current user
 */

import { defineStore } from "pinia";
import { computed } from "vue";
import { authClient, useSession } from "@/services/authClient";

export const useAuthStore = defineStore("auth", () => {
  // ═══════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════

  // Use Better Auth's reactive session
  const session = useSession();

  // ═══════════════════════════════════════════════════════════
  // COMPUTED
  // ═══════════════════════════════════════════════════════════

  /**
   * Whether the user is authenticated
   */
  const isAuthenticated = computed(() => !!session.value.data?.user);

  /**
   * Current user object (null if not authenticated)
   */
  const user = computed(() => session.value.data?.user || null);

  /**
   * Whether the session is being loaded
   */
  const isLoading = computed(() => session.value.isPending);

  // ═══════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════

  /**
   * Sign in with email and password
   *
   * @param email - User's email address
   * @param password - User's password
   * @throws Error if sign in fails
   * @returns User data on success
   */
  async function signIn(email: string, password: string) {
    const { data, error } = await authClient.signIn.email({
      email,
      password,
    });

    if (error) {
      throw new Error(error.message || "Sign in failed");
    }

    return data;
  }

  /**
   * Create a new user account
   *
   * @param name - User's display name
   * @param email - User's email address
   * @param password - User's password
   * @throws Error if sign up fails
   * @returns User data on success
   */
  async function signUp(name: string, email: string, password: string) {
    const { data, error } = await authClient.signUp.email({
      name,
      email,
      password,
    });

    if (error) {
      throw new Error(error.message || "Sign up failed");
    }

    return data;
  }

  /**
   * Sign out the current user
   */
  async function signOut() {
    await authClient.signOut();
  }

  // ═══════════════════════════════════════════════════════════
  // RETURN
  // ═══════════════════════════════════════════════════════════

  return {
    // State
    session,

    // Computed
    isAuthenticated,
    user,
    isLoading,

    // Actions
    signIn,
    signUp,
    signOut,
  };
});
