/**
 * Vue Router Configuration
 *
 * Defines application routes and authentication guards.
 * Routes marked with requiresAuth need authentication to access.
 * Routes marked with requiresGuest redirect authenticated users away.
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/authStore";
import { watch } from "vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/LoginView.vue"),
    meta: { requiresGuest: true },
  },
  {
    path: "/signup",
    name: "Signup",
    component: () => import("@/views/SignupView.vue"),
    meta: { requiresGuest: true },
  },
  {
    path: "/",
    name: "Home",
    component: () => import("@/views/HomeView.vue"),
    meta: { requiresAuth: true }, // Set to true to require authentication
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

/**
 * Global navigation guard
 * - Redirects unauthenticated users to login for protected routes
 * - Redirects authenticated users away from guest-only pages (login/signup)
 */
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Always wait for session to finish loading before making auth decisions
  // This prevents race conditions where we check auth before session is resolved
  if (authStore.isLoading) {
    await new Promise<void>((resolve) => {
      const unwatch = watch(
        () => authStore.isLoading,
        (loading) => {
          if (!loading) {
            unwatch();
            resolve();
          }
        },
        { immediate: true } // Check current value immediately
      );

      // Safety timeout to prevent infinite waiting
      setTimeout(() => {
        unwatch();
        resolve();
      }, 3000);
    });
  }

  // Check if route requires authentication
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  }
  // Check if route is guest-only (login/signup)
  else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next({ name: "Home" });
  }
  // Allow navigation
  else {
    next();
  }
});

export default router;
