<template>
  <div class="login-form">
    <div class="form-container">
      <h2 class="form-title">Sign In</h2>
      <p class="form-subtitle">Welcome back to Orchestrator</p>

      <form @submit.prevent="handleSubmit">
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
            autocomplete="current-password"
            placeholder="••••••••"
            :disabled="isLoading"
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          {{ isLoading ? "Signing in..." : "Sign In" }}
        </button>
      </form>

      <p class="auth-switch">
        Don't have an account?
        <router-link to="/signup" class="auth-link">Sign up</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "vue-router";

const authStore = useAuthStore();
const router = useRouter();

const email = ref("");
const password = ref("");
const error = ref("");
const isLoading = ref(false);

async function handleSubmit() {
  error.value = "";
  isLoading.value = true;

  try {
    await authStore.signIn(email.value, password.value);
    router.push("/");
  } catch (e: unknown) {
    const errorMessage = e instanceof Error ? e.message : 'Login failed. Please check your credentials.';
    error.value = errorMessage;
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.login-form {
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
