# Better Auth

The most comprehensive authentication framework for TypeScript.

## Navigation
- Docs
- Examples
- Changelogs
- Blog
- Community
- Enterprise

---

## Introducing Better Auth Infrastructure

Join the waitlist for Better Auth Infrastructure

---

## Own Your Auth

**The most comprehensive authentication framework for TypeScript.**

### Quick Start

```bash
npm install better-auth
```

### Basic Setup Example

```typescript
export const auth = betterAuth({
  database: new Pool({
    connectionString: DATABASE_URL,
  }),
  emailAndPassword: {
    enabled: true,
  },
  plugins: [
    organization(),
    twoFactor(),
  ]
})
```

[Get Started](#) | [Create Sign in Box](#) | [View Demo](#)

---

## Core Features

### Framework Agnostic

Support for popular frameworks including:
- React
- Vue
- Svelte
- Astro
- Solid
- Next.js
- Nuxt
- Tanstack Start
- Hono
- And more

[Learn more](#)

### Email & Password Authentication

Built-in support for email and password authentication, with session and account management features.

[Learn more](#)

### Social Sign-on (OAuth)

Support multiple OAuth providers:
- GitHub
- Google
- Discord
- Twitter
- And more

Allow users to sign in with their accounts from popular platforms.

[Learn more](#)

### Two Factor Authentication

Multi Factor Authentication.

Secure your users' accounts with two factor authentication with just a few lines of code.

[Learn more](#)

### Multi Tenant Support

Organization, Members, and Invitation.

Multi tenant support with members, organization, teams and invitation with access control.

[Learn more](#)

### Plugin Ecosystem

A lot more features with plugins.

Improve your application experience with our official plugins and those created by the community.

[Learn more](#)

---

## Community Testimonials

> "I have been using better-auth for exon todo and it is like so fast, I set it up once and it just works."
>
> **Ryan Vogel** - Founder of exon

> "@better_auth exceeded all expectations, and it's just getting started."
>
> **Dagmawi Babi** - Developer

> "Using @better_auth with custom components feels like having someone hand you the remote while you're comfortably on the sofa. The ease I'm feeling rn is insane Auth done in under 5 minutes 🤌⚡️"
>
> **Tech Nerd** - Developer

> "If you're building a code project in 2025 use @better_auth. It has everything you need now and everything you'll need at scale. Don't take this suggestion lightly..."
>
> **Omar McAdam** - Creator of AugmentedHQ

> "Great project & maintainer."
>
> **Guillermo Rauch** - CEO of Vercel

> "I can't believe how easy @better_auth is compared to @authjs all I had to do was connect it to my drizzle schema and create a sign up page w the auth :)))"
>
> **Nizzy** - Co-founder of Zero

> "Better-auth is a work of art.."
>
> **Vybhav Bhargav** - Founding engineer @glyfspace

---

## Call to Action

**Roll your own auth with confidence in minutes!**

[Star on GitHub](#) - 25.3K+

---

*Source: https://www.better-auth.com/*
