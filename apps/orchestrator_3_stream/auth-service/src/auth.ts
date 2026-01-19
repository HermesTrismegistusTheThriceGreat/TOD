/**
 * Better Auth Configuration
 *
 * Configures Better Auth with PostgreSQL database and email/password authentication.
 * Uses environment variables for database connection and security settings.
 */

import { betterAuth } from "better-auth";
import { Pool } from "pg";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Validate required environment variables
if (!process.env.BETTER_AUTH_SECRET) {
  throw new Error('BETTER_AUTH_SECRET environment variable is required');
}

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

/**
 * Better Auth instance configured with:
 * - PostgreSQL database connection
 * - Email and password authentication
 * - Session management with 7-day expiry
 * - Cookie-based sessions with httpOnly security
 * - CORS support for trusted origins
 */
export const auth = betterAuth({
  database: pool,
  baseURL: process.env.AUTH_BASE_URL || "http://localhost:9404",
  secret: process.env.BETTER_AUTH_SECRET,

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
    process.env.FRONTEND_URL,
  ].filter((origin): origin is string => !!origin && origin.length > 0),
});
