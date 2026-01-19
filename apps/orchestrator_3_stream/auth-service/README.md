# Auth Service

Better Auth authentication microservice for Orchestrator 3 Stream.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

3. Update `.env` with your configuration:
- `DATABASE_URL`: Your Neon PostgreSQL connection string
- `BETTER_AUTH_SECRET`: Generate with `openssl rand -base64 32`
- `FRONTEND_URL`: Your frontend URL (for CORS)

## Development

```bash
npm run dev
```

Server runs on port 9404 by default.

## Production

```bash
npm run build
npm start
```

## Endpoints

- `GET/POST /api/auth/*` - Better Auth endpoints (sign in, sign up, sign out, session)
- `GET /health` - Health check

## Database Tables

Ensure the Better Auth tables exist in your database:
- `user` - User accounts
- `session` - Active sessions
- `account` - Authentication providers (email/password, OAuth)
- `verification` - Email verification tokens

See `apps/orchestrator_db/migrations/13_better_auth_tables.sql` for table schemas.
