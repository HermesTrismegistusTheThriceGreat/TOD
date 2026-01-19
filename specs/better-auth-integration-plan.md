# Better Auth Integration Plan for Orchestrator 3 Stream

## Overview

This plan integrates Better Auth into the Orchestrator 3 Stream application with:
- **Vue.js Frontend** - Better Auth client for sign in/up/out
- **FastAPI Backend** - Session validation via shared database
- **Neon PostgreSQL** - Shared database for auth and app data

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Vue.js App    │────▶│  Auth Service    │────▶│   Neon DB       │
│   (Frontend)    │     │  (Hono/Node.js)  │     │   (PostgreSQL)  │
└────────┬────────┘     └──────────────────┘     └────────┬────────┘
         │                                                 │
         │              ┌──────────────────┐               │
         └─────────────▶│  FastAPI Backend │◀──────────────┘
                        │  (Orchestrator)  │
                        └──────────────────┘
```

**Key Design Decisions:**
1. Better Auth runs as a separate Node.js microservice (using Hono)
2. FastAPI validates sessions by reading cookies + querying shared DB
3. All services share the same Neon database
4. Cookie-based sessions with httpOnly for security

---

## Phase 1: Database Schema

### New Tables (Better Auth)

Add these tables to your Neon database alongside existing tables:

```sql
-- Migration: 13_better_auth_tables.sql

-- Users table
CREATE TABLE IF NOT EXISTS "user" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE,
    image TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_email ON "user"(email);

-- Sessions table
CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_session_token ON session(token);
CREATE INDEX idx_session_user_id ON session(user_id);
CREATE INDEX idx_session_expires_at ON session(expires_at);

-- Accounts table (for OAuth and password auth)
CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    access_token_expires_at TIMESTAMPTZ,
    refresh_token_expires_at TIMESTAMPTZ,
    scope TEXT,
    id_token TEXT,
    password TEXT,  -- hashed password for email/password auth
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_account_user_id ON account(user_id);
CREATE UNIQUE INDEX idx_account_provider ON account(provider_id, account_id);

-- Verification table (for email verification, password reset)
CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_verification_identifier ON verification(identifier);
```

---

## Phase 2: Auth Service (Hono/Node.js)

Create a lightweight auth microservice using Hono:

### File Structure

```
apps/orchestrator_3_stream/auth-service/
├── package.json
├── tsconfig.json
├── .env
└── src/
    ├── index.ts          # Hono server entry
    ├── auth.ts           # Better Auth configuration
    └── db.ts             # Database connection
```

### package.json

```json
{
  "name": "orchestrator-auth-service",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "better-auth": "^1.4.6",
    "hono": "^4.0.0",
    "pg": "^8.11.0",
    "@hono/node-server": "^1.8.0"
  },
  "devDependencies": {
    "tsx": "^4.0.0",
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }
}
```

### src/auth.ts

```typescript
import { betterAuth } from "better-auth";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export const auth = betterAuth({
  database: pool,
  baseURL: process.env.AUTH_BASE_URL || "http://localhost:9404",

  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Set true for production
  },

  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24,     // Refresh daily
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // 5 min cache
    },
  },

  advanced: {
    crossSubDomainCookies: {
      enabled: false, // Enable if frontend/backend on different subdomains
    },
    defaultCookieAttributes: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
    },
  },

  trustedOrigins: [
    "http://localhost:5175",      // Vue dev server
    "http://127.0.0.1:5175",
    process.env.FRONTEND_URL || "",
  ],
});
```

### src/index.ts

```typescript
import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { cors } from "hono/cors";
import { auth } from "./auth";

const app = new Hono();

// CORS for frontend
app.use("/*", cors({
  origin: [
    "http://localhost:5175",
    "http://127.0.0.1:5175",
  ],
  credentials: true,
}));

// Mount Better Auth
app.on(["GET", "POST"], "/api/auth/*", (c) => auth.handler(c.req.raw));

// Health check
app.get("/health", (c) => c.json({ status: "ok" }));

const port = parseInt(process.env.AUTH_PORT || "9404");
console.log(`Auth service running on port ${port}`);
serve({ fetch: app.fetch, port });
```

### .env

```env
DATABASE_URL=postgresql://neondb_owner:npg_bQz8vcI7sEuK@ep-noisy-dream-ahzuq2ep-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
AUTH_BASE_URL=http://localhost:9404
AUTH_PORT=9404
BETTER_AUTH_SECRET=<generate-with-openssl-rand-base64-32>
FRONTEND_URL=http://localhost:5175
NODE_ENV=development
```

---

## Phase 3: FastAPI Session Validation

### New Pydantic Models

Add to `apps/orchestrator_db/models.py`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AuthUser(BaseModel):
    id: str
    name: str
    email: str
    email_verified: bool = False
    image: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AuthSession(BaseModel):
    id: str
    user_id: str
    token: str
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

### Auth Middleware

Create `apps/orchestrator_3_stream/backend/modules/auth_middleware.py`:

```python
from fastapi import Request, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import asyncpg

from .database import get_connection
from apps.orchestrator_db.models import AuthUser, AuthSession

SESSION_COOKIE_NAME = "better-auth.session_token"


async def get_session_from_cookie(request: Request) -> Optional[str]:
    """Extract session token from cookie."""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def validate_session(token: str) -> Optional[tuple[AuthSession, AuthUser]]:
    """Validate session token and return session + user if valid."""
    async with get_connection() as conn:
        # Query session with user join
        row = await conn.fetchrow("""
            SELECT
                s.id as session_id,
                s.user_id,
                s.token,
                s.expires_at,
                s.ip_address,
                s.user_agent,
                s.created_at as session_created_at,
                s.updated_at as session_updated_at,
                u.id as user_id,
                u.name,
                u.email,
                u.email_verified,
                u.image,
                u.created_at as user_created_at,
                u.updated_at as user_updated_at
            FROM session s
            JOIN "user" u ON s.user_id = u.id
            WHERE s.token = $1
              AND s.expires_at > $2
        """, token, datetime.now(timezone.utc))

        if not row:
            return None

        session = AuthSession(
            id=row["session_id"],
            user_id=row["user_id"],
            token=row["token"],
            expires_at=row["expires_at"],
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
            created_at=row["session_created_at"],
            updated_at=row["session_updated_at"],
        )

        user = AuthUser(
            id=row["user_id"],
            name=row["name"],
            email=row["email"],
            email_verified=row["email_verified"],
            image=row["image"],
            created_at=row["user_created_at"],
            updated_at=row["user_updated_at"],
        )

        return session, user


async def get_current_user(request: Request) -> AuthUser:
    """Dependency to get current authenticated user. Raises 401 if not authenticated."""
    token = await get_session_from_cookie(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await validate_session(token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    _, user = result
    return user


async def get_optional_user(request: Request) -> Optional[AuthUser]:
    """Dependency to get current user if authenticated, None otherwise."""
    token = await get_session_from_cookie(request)
    if not token:
        return None

    result = await validate_session(token)
    if not result:
        return None

    _, user = result
    return user
```

### Using Auth in Endpoints

Update `apps/orchestrator_3_stream/backend/main.py`:

```python
from modules.auth_middleware import get_current_user, get_optional_user, AuthUser

# Protected endpoint example
@app.get("/api/me")
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    return {"user": user.model_dump()}

# Optional auth endpoint
@app.get("/get_orchestrator")
async def get_orchestrator(user: Optional[AuthUser] = Depends(get_optional_user)):
    # user is None if not authenticated
    # Existing logic continues to work
    ...
```

### WebSocket Auth

Update WebSocket to validate session:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Get session cookie from WebSocket headers
    cookies = websocket.cookies
    token = cookies.get(SESSION_COOKIE_NAME)

    user = None
    if token:
        result = await validate_session(token)
        if result:
            _, user = result

    # Optional: reject unauthenticated connections
    # if not user:
    #     await websocket.close(code=4001)
    #     return

    await ws_manager.connect(websocket)
    # ... rest of websocket logic
```

---

## Phase 4: Vue.js Frontend Integration

### Install Better Auth Client

```bash
cd apps/orchestrator_3_stream/frontend
npm install better-auth
```

### Create Auth Client

Create `src/services/authClient.ts`:

```typescript
import { createAuthClient } from "better-auth/vue";

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
```

### Environment Variables

Add to `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:9403
VITE_WEBSOCKET_URL=ws://127.0.0.1:9403/ws
VITE_AUTH_URL=http://localhost:9404
```

### Auth Store (Pinia)

Create `src/stores/authStore.ts`:

```typescript
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authClient, useSession } from "@/services/authClient";

export const useAuthStore = defineStore("auth", () => {
  // Use Better Auth's reactive session
  const session = useSession();

  // Computed properties
  const isAuthenticated = computed(() => !!session.value.data?.user);
  const user = computed(() => session.value.data?.user || null);
  const isLoading = computed(() => session.value.isPending);

  // Actions
  async function signIn(email: string, password: string) {
    const { data, error } = await authClient.signIn.email({
      email,
      password,
    });

    if (error) {
      throw new Error(error.message);
    }

    return data;
  }

  async function signUp(name: string, email: string, password: string) {
    const { data, error } = await authClient.signUp.email({
      name,
      email,
      password,
    });

    if (error) {
      throw new Error(error.message);
    }

    return data;
  }

  async function signOut() {
    await authClient.signOut();
  }

  return {
    session,
    isAuthenticated,
    user,
    isLoading,
    signIn,
    signUp,
    signOut,
  };
});
```

### Login Component

Create `src/components/auth/LoginForm.vue`:

```vue
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
  } catch (e: any) {
    error.value = e.message || "Login failed";
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="login-form">
    <h2>Sign In</h2>

    <form @submit.prevent="handleSubmit">
      <div class="field">
        <label for="email">Email</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          autocomplete="email"
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
        />
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Signing in..." : "Sign In" }}
      </button>
    </form>

    <p>
      Don't have an account?
      <router-link to="/signup">Sign up</router-link>
    </p>
  </div>
</template>
```

### Auth Guard (Router)

Update `src/router/index.ts`:

```typescript
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/authStore";

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
      meta: { requiresAuth: true },
    },
    // ... other routes
  ],
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Wait for session to load
  if (authStore.isLoading) {
    await new Promise((resolve) => {
      const unwatch = watch(
        () => authStore.isLoading,
        (loading) => {
          if (!loading) {
            unwatch();
            resolve(true);
          }
        }
      );
    });
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next({ name: "Home" });
  } else {
    next();
  }
});

export default router;
```

---

## Phase 5: Running the Stack

### Start Script Updates

Update the orchestrator start script to include auth service:

```bash
# Start auth service (new)
cd apps/orchestrator_3_stream/auth-service && npm run dev &

# Start backend (existing)
cd apps/orchestrator_3_stream/backend && uv run python -m uvicorn main:app --port 9403 &

# Start frontend (existing)
cd apps/orchestrator_3_stream/frontend && npm run dev &
```

### Port Allocation

| Service | Port | Description |
|---------|------|-------------|
| Auth Service | 9404 | Better Auth (Hono) |
| FastAPI Backend | 9403 | Orchestrator API |
| Vue.js Frontend | 5175 | Dev server |

---

## Phase 6: Migration from Stack Auth (Optional)

If you want to migrate existing Stack Auth users:

```sql
-- Migrate users from neon_auth.users_sync to new user table
INSERT INTO "user" (id, name, email, email_verified, created_at, updated_at)
SELECT
    id,
    COALESCE(name, email),
    email,
    TRUE,  -- Assume verified
    COALESCE(created_at, NOW()),
    COALESCE(updated_at, NOW())
FROM neon_auth.users_sync
WHERE deleted_at IS NULL
ON CONFLICT (id) DO NOTHING;
```

---

## Security Checklist

- [ ] Set strong `BETTER_AUTH_SECRET` (32+ chars)
- [ ] Enable `secure: true` for cookies in production
- [ ] Configure CORS origins for production domains
- [ ] Enable email verification for production
- [ ] Set up rate limiting on auth endpoints
- [ ] Configure password requirements (min length, complexity)
- [ ] Enable HTTPS for all services in production

---

## Files to Create/Modify

### New Files
1. `apps/orchestrator_db/migrations/13_better_auth_tables.sql`
2. `apps/orchestrator_3_stream/auth-service/` (entire directory)
3. `apps/orchestrator_3_stream/backend/modules/auth_middleware.py`
4. `apps/orchestrator_3_stream/frontend/src/services/authClient.ts`
5. `apps/orchestrator_3_stream/frontend/src/stores/authStore.ts`
6. `apps/orchestrator_3_stream/frontend/src/components/auth/LoginForm.vue`
7. `apps/orchestrator_3_stream/frontend/src/components/auth/SignupForm.vue`
8. `apps/orchestrator_3_stream/frontend/src/views/LoginView.vue`
9. `apps/orchestrator_3_stream/frontend/src/views/SignupView.vue`

### Modified Files
1. `apps/orchestrator_db/models.py` - Add AuthUser, AuthSession models
2. `apps/orchestrator_3_stream/backend/main.py` - Add auth dependencies
3. `apps/orchestrator_3_stream/frontend/src/router/index.ts` - Auth guards
4. `apps/orchestrator_3_stream/frontend/.env` - Add VITE_AUTH_URL
