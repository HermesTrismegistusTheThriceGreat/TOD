<template>
  <div class="signup-form">
    <div class="form-container">
      <h2 class="form-title">Create Account</h2>
      <p class="form-subtitle">Get started with Orchestrator</p>

      <form @submit.prevent="handleSubmit">
        <div class="field">
          <label for="name">Name</label>
          <input
            id="name"
            v-model="name"
            type="text"
            required
            autocomplete="name"
            placeholder="John Doe"
            :disabled="isLoading"
          />
        </div>

        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
            :disabled="isLoading"
          />
        </div>

        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            autocomplete="new-password"
            placeholder="••••••••"
            :disabled="isLoading"
            minlength="8"
          />
          <p class="field-hint">Must be at least 8 characters</p>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          {{ isLoading ? "Creating account..." : "Sign Up" }}
        </button>
      </form>

      <p class="auth-switch">
        Already have an account?
        <router-link to="/login" class="auth-link">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useAuthStore } from "@/stores/authStore";
import { useRouter, useRoute } from "vue-router";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const name = ref("");
const email = ref("");
const password = ref("");
const error = ref("");
const isLoading = ref(false);

async function handleSubmit() {
  error.value = "";
  isLoading.value = true;

  try {
    await authStore.signUp(name.value, email.value, password.value);

    // If already authenticated, navigate immediately
    if (authStore.isAuthenticated) {
      const redirectPath = (route.query.redirect as string) || "/";
      router.push(redirectPath);
      return;
    }

    // Wait for auth state to update (race condition fix)
    // The reactive session from Better Auth updates asynchronously
    await new Promise<void>((resolve) => {
      const unwatch = watch(
        () => authStore.isAuthenticated,
        (isAuth) => {
          if (isAuth) {
            unwatch();
            resolve();
          }
        },
        { immediate: true }
      );

      // Timeout after 2 seconds as safety measure
      setTimeout(() => {
        unwatch();
        resolve();
      }, 2000);
    });

    const redirectPath = (route.query.redirect as string) || "/";
    router.push(redirectPath);
  } catch (e: unknown) {
    const errorMessage = e instanceof Error ? e.message : 'Sign up failed. Please try again.';
    error.value = errorMessage;
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.signup-form {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg-primary);
  padding: var(--spacing-lg);
}

.form-container {
  width: 100%;
  max-width: 420px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-lg);
}

.form-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
  text-align: center;
}

.form-subtitle {
  color: var(--text-secondary);
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.field {
  margin-bottom: var(--spacing-lg);
}

.field label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.field input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.9375rem;
  transition: all 0.2s;
}

.field input:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
}

.field input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.field input::placeholder {
  color: var(--text-dim);
}

.field-hint {
  margin-top: var(--spacing-xs);
  font-size: 0.75rem;
  color: var(--text-dim);
}

.error-message {
  padding: 0.75rem 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--status-error);
  border-radius: 8px;
  color: var(--status-error);
  font-size: 0.875rem;
  margin-bottom: var(--spacing-lg);
}

.submit-btn {
  width: 100%;
  padding: 0.875rem 1.5rem;
  background: var(--accent-primary);
  color: white;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-switch {
  margin-top: var(--spacing-xl);
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.auth-link {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 500;
  margin-left: var(--spacing-xs);
  transition: color 0.2s;
}

.auth-link:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}
</style>
