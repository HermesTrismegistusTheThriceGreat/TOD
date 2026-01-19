# Better Auth Integration Guide

This guide explains how to complete the Better Auth integration for the Orchestrator 3 Stream frontend.

## Prerequisites

The following files have been created:
- `/src/services/authClient.ts` - Better Auth client
- `/src/stores/authStore.ts` - Pinia authentication store
- `/src/components/auth/LoginForm.vue` - Login form component
- `/src/components/auth/SignupForm.vue` - Signup form component
- `/src/views/LoginView.vue` - Login page view
- `/src/views/SignupView.vue` - Signup page view
- `/src/router/index.ts` - Vue Router with auth guards
- `/.env` - Environment variables

## Installation Steps

### 1. Install Dependencies

```bash
npm install better-auth vue-router
```

### 2. Update main.ts

Replace the contents of `src/main.ts` with:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/global.css'
import 'highlight.js/styles/github-dark.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)  // Add router
app.use(ElementPlus)
app.mount('#app')
```

### 3. Update App.vue

Since the router is now managing views, you need to add a `<router-view>` to App.vue.

**Option A: Simple Approach (Recommended)**
Keep the existing App.vue as-is for the main application view, and the router will handle login/signup separately. The router is configured to show App.vue at the root path `/`.

**Option B: Full Router Integration**
If you want full routing integration, replace App.vue content with:

```vue
<template>
  <router-view />
</template>

<script setup lang="ts">
// No script needed for simple router view
</script>
```

Then move the existing App.vue content to a new `src/views/HomeView.vue` and update the router to use it:

```typescript
// In src/router/index.ts, change the Home route to:
{
  path: "/",
  name: "Home",
  component: () => import("@/views/HomeView.vue"),
  meta: { requiresAuth: false }, // Set to true to require authentication
}
```

### 4. Environment Variables

The `.env` file has been created with:

```env
VITE_AUTH_URL=http://localhost:9404
```

Ensure the auth service is running on port 9404.

### 5. Enable Authentication (Optional)

To require authentication for the main app:

1. Open `src/router/index.ts`
2. Change the Home route meta to `requiresAuth: true`:

```typescript
{
  path: "/",
  name: "Home",
  component: () => import("@/App.vue"),
  meta: { requiresAuth: true }, // Changed from false to true
}
```

### 6. Add Sign Out Button (Optional)

Add a sign-out button to your app header or user menu:

```vue
<script setup lang="ts">
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

async function handleSignOut() {
  await authStore.signOut()
  router.push('/login')
}
</script>

<template>
  <button v-if="authStore.isAuthenticated" @click="handleSignOut">
    Sign Out
  </button>
</template>
```

## Usage

### Auth Store

Access authentication state anywhere in your app:

```vue
<script setup lang="ts">
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()

// Check if user is authenticated
console.log(authStore.isAuthenticated)

// Get current user
console.log(authStore.user)

// Sign in
await authStore.signIn(email, password)

// Sign up
await authStore.signUp(name, email, password)

// Sign out
await authStore.signOut()
</script>
```

### Protecting Components

Check authentication status in any component:

```vue
<template>
  <div v-if="authStore.isAuthenticated">
    <p>Welcome, {{ authStore.user?.name }}!</p>
  </div>
  <div v-else>
    <p>Please sign in</p>
  </div>
</template>
```

### Navigation

Users can navigate to:
- `/login` - Sign in page
- `/signup` - Sign up page
- `/` - Main application (requires auth if enabled)

## Testing

1. Start the auth service:
```bash
cd apps/orchestrator_3_stream/auth-service
npm run dev
```

2. Start the frontend:
```bash
cd apps/orchestrator_3_stream/frontend
npm run dev
```

3. Navigate to `http://localhost:5175/signup` to create an account
4. Navigate to `http://localhost:5175/login` to sign in
5. Navigate to `http://localhost:5175/` to access the main app

## Troubleshooting

### "Cannot find module 'better-auth/vue'"
Run `npm install better-auth`

### "Cannot find module 'vue-router'"
Run `npm install vue-router`

### CORS Errors
Ensure the auth service is running and configured with the correct FRONTEND_URL in its `.env` file.

### Session Not Persisting
Check that cookies are enabled in your browser and that the auth service and frontend are running on the same domain (or configured for cross-domain cookies).
