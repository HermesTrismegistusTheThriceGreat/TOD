# Neon Auth

Managed authentication that branches with your database

## Beta

The **Neon Auth with Better Auth** is in Beta. Share your feedback on Discord or via the Neon Console.

Neon Auth is a managed authentication service that stores users, sessions, and auth configuration directly in your Neon database. When you branch your database, your entire auth state branches with it. This lets you test real authentication workflows in preview environments.

## Before you start

Neon Auth is in active development. Check the roadmap to see what's supported and what's coming next.

## Why Neon Auth?

### Identity lives in your database

All authentication data is stored in the `neon_auth` schema. It's queryable with SQL and compatible with Row Level Security (RLS) policies.

### Zero server management

Neon Auth runs as a managed REST API service. Configure settings in the Console; use the SDK in your app. No infrastructure to maintain.

### Auth that branches with your data

Test sign-up, login, password reset, and OAuth flows in isolated branches without touching production data.

## Built on Better Auth

Neon Auth is powered by Better Auth, which means you get familiar APIs. You can use Better Auth UI components or call auth methods directly to build your own UI.

Neon Auth currently supports Better Auth version **1.4.6**.

### When to use Neon Auth vs. self-hosting Better Auth

Neon Auth is a managed authentication service that integrates seamlessly with Neon's architecture and offerings:

- **Branch-aware authentication** — Every Neon branch gets its own isolated auth environment, so you can test authentication features without affecting your production branch.

- **Built-in Data API integration** — JWT token validation for the Data API has native support for Neon Auth.

- **No infrastructure to manage** — Neon Auth is deployed in the same region as your database, reducing latency without requiring you to run auth infrastructure.

- **Shared OAuth credentials for testing** — Get started quickly with out-of-the-box Google OAuth credentials, eliminating the setup complexity for testing and prototyping.

Self-hosting Better Auth makes sense if you need:

- Flexibility in auth configuration—custom plugins, hooks, and options not yet supported by Neon Auth.

- Full control over your auth code and the ability to run it inside your own infrastructure.

For more details on the SDK differences between `@neondatabase/auth` and `better-auth/client`, see the Better Auth documentation.

As Neon Auth evolves, more Better Auth integrations and features will be added. Check the roadmap to see what's currently supported and what's coming next.

## Basic usage

Enable Auth in your Neon project, then add authentication to your app:

**src/auth.ts**

```typescript
import { createAuthClient } from '@neondatabase/neon-js/auth';

export const authClient = createAuthClient(import.meta.env.VITE_NEON_AUTH_URL);
```

**src/App.tsx**

```typescript
import { NeonAuthUIProvider, AuthView } from '@neondatabase/neon-js/auth/react/ui';
import { authClient } from './auth';

export default function App() {
  return (
    <NeonAuthUIProvider authClient={authClient}>
      <AuthView pathname="sign-in" />
    </NeonAuthUIProvider>
  );
}
```

## Use cases

### Production authentication

Use Neon Auth as the identity system for your app. Store users, sessions, and OAuth configuration directly in Postgres, and pair with RLS for secure, database-centric access control.

### Preview environments

Test full authentication flows in Vercel previews with real users and sessions

### Multi-tenant SaaS

Test complex org and role hierarchies safely in isolated branches

### CI/CD workflows

Run end-to-end auth tests without touching production. The Neon Create Branch GitHub Action supports retrieving branch-specific auth URLs for testing authentication flows in GitHub Actions workflows.

### Development workflows

Spin up complete environments instantly with database and auth together

See Branching authentication for details on how auth branches with your database.

## Quick start guides

Choose your framework to get started:

- **Next.js** — With UI components
- **React (API methods)** — Build your own auth UI
- **React** — With UI components
- **TanStack Router** — With UI components

## Availability

Neon Auth is currently available for AWS regions only. Azure support is not yet available.

## Pricing

Neon Auth is included in all Neon plans based on Monthly Active Users (MAU):

- **Free**: Up to 60,000 MAU
- **Launch**: Up to 1M MAU
- **Scale**: Up to 1M MAU

An MAU (Monthly Active User) is a unique user who authenticates at least once during a monthly billing period. If you need more than 1M MAU, contact Sales.

See Neon plans for more details.

## Migration from Stack Auth

If you're using the previous Neon Auth implementation via Stack Auth, your version will continue to work. When you're ready to migrate to the new Better Auth implementation, see the migration guide.

## Need help?

Join the Neon Discord Server to ask questions or see what others are doing with Neon. For paid plan support options, see Support.

---

Last updated on January 15, 2026
