# Plan: Auth Redirect and Route Protection

## Task Description
Implement two authentication requirements for the Orchestrator 3 Stream app:
1. When a user logs out, redirect them to the `/login` page
2. Require authentication to access all app pages - unauthenticated users should be redirected to `/login`

## Objective
Complete the authentication flow so that:
- Users must be logged in to access the main application
- After logout, users are redirected to the login page
- After login, users are redirected to their originally requested page (or home if direct login)

## Problem Statement
The authentication infrastructure is already implemented but not fully enabled:
- The logout redirect to `/login` is **already working** (implemented in `AppHeader.vue`)
- Route protection exists but the Home route has `requiresAuth: false` (disabled)
- The login form doesn't use the redirect query parameter passed by the router guard

## Solution Approach
Minimal changes required - enable existing infrastructure and add redirect parameter handling:
1. Enable route protection by changing one boolean flag
2. Update LoginForm to honor the redirect query parameter after successful login
3. (Optional) Apply same redirect handling to SignupForm for consistency

## Relevant Files
Use these files to complete the task:

- **`apps/orchestrator_3_stream/frontend/src/router/index.ts`** - Contains route definitions and navigation guards. Line 30 has `requiresAuth: false` that needs to change to `true`

- **`apps/orchestrator_3_stream/frontend/src/components/auth/LoginForm.vue`** - Login form component. Line 70 always redirects to `/` after login - needs to use redirect query parameter

- **`apps/orchestrator_3_stream/frontend/src/components/auth/SignupForm.vue`** - Signup form component. Line 86 always redirects to `/` after signup - should also use redirect query parameter for consistency

- **`apps/orchestrator_3_stream/frontend/src/components/AppHeader.vue`** - Contains logout handler at lines 140-147. **Already works correctly** - redirects to `/login` after signOut

- **`apps/orchestrator_3_stream/frontend/src/stores/authStore.ts`** - Auth state management with Better Auth. No changes needed.

### Files That Already Work (No Changes Needed)
- `AppHeader.vue` logout handler - already redirects to `/login`
- `router/index.ts` navigation guard - already handles `requiresAuth` and `requiresGuest` meta
- `authStore.ts` - properly manages session state with `isAuthenticated`, `isLoading`

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Enable Route Protection for Home Route
- Open `apps/orchestrator_3_stream/frontend/src/router/index.ts`
- Locate line 30: `meta: { requiresAuth: false }`
- Change to: `meta: { requiresAuth: true }`
- This enables the existing navigation guard to protect the Home route

### 2. Update LoginForm to Use Redirect Query Parameter
- Open `apps/orchestrator_3_stream/frontend/src/components/auth/LoginForm.vue`
- Import `useRoute` from `vue-router` (add to existing import)
- Create route instance: `const route = useRoute();`
- In the `handleSubmit()` function (around line 70), change:
  ```typescript
  // FROM:
  router.push("/");

  // TO:
  const redirectPath = (route.query.redirect as string) || "/";
  router.push(redirectPath);
  ```

### 3. Update SignupForm to Use Redirect Query Parameter (Consistency)
- Open `apps/orchestrator_3_stream/frontend/src/components/auth/SignupForm.vue`
- Import `useRoute` from `vue-router` (add to existing import)
- Create route instance: `const route = useRoute();`
- In the success handler (around line 86), change:
  ```typescript
  // FROM:
  router.push("/");

  // TO:
  const redirectPath = (route.query.redirect as string) || "/";
  router.push(redirectPath);
  ```

### 4. Verify Logout Redirect (Already Working)
- Confirm `AppHeader.vue` lines 140-147 contain:
  ```typescript
  async function handleLogout() {
    try {
      await authStore.signOut();
      router.push("/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  }
  ```
- No changes needed - logout redirect is already implemented

### 5. Validate the Implementation
- Start the frontend development server
- Test the complete authentication flow (see Validation Commands)

## Testing Strategy
Manual testing of the complete authentication flow:

1. **Route Protection Test**
   - Clear browser cookies/session
   - Navigate to `http://localhost:5175/` (Home)
   - Should redirect to `/login?redirect=%2F`

2. **Login Redirect Test**
   - From the login page (with redirect param), enter valid credentials
   - Should redirect to the originally requested page (`/`)

3. **Direct Login Test**
   - Navigate directly to `/login` (no redirect param)
   - After login, should redirect to `/`

4. **Logout Redirect Test**
   - While authenticated, click the LOGOUT button
   - Should redirect to `/login`
   - Should not be able to navigate back to `/` without re-authenticating

5. **Guest Route Protection Test**
   - While authenticated, try to navigate to `/login` or `/signup`
   - Should redirect back to `/`

## Acceptance Criteria
- [ ] Unauthenticated users visiting `/` are redirected to `/login`
- [ ] The redirect URL is preserved in query parameter (`?redirect=/`)
- [ ] After successful login, users are redirected to their originally requested page
- [ ] After logout, users are redirected to `/login`
- [ ] Authenticated users cannot access `/login` or `/signup` (redirected to `/`)
- [ ] Session state is properly checked before navigation decisions

## Validation Commands
Execute these commands to validate the task is complete:

1. **Start the application**
   ```bash
   cd apps/orchestrator_3_stream/frontend && npm run dev
   ```

2. **Manual browser testing** (in order):
   - Clear cookies for localhost:5175
   - Visit `http://localhost:5175/` → Should redirect to `/login?redirect=%2F`
   - Login with valid credentials → Should redirect to `/`
   - Click LOGOUT button → Should redirect to `/login`
   - Try visiting `/` again → Should redirect to `/login`

3. **Optional: Use Playwright validator agent** for automated UI testing

## Notes
- The authentication infrastructure using Better Auth is already well-implemented
- The navigation guard properly waits for session loading before making redirect decisions
- Cookie-based sessions work correctly through the Vite proxy in development
- Consider using `router.replace("/login")` instead of `router.push("/login")` in logout to prevent back-button issues (optional enhancement)
- Debug logging in `AppHeader.vue` (lines 131-137) can be removed in production
