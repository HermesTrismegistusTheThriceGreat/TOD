/**
 * Auth Service - Hono Server Entry Point
 *
 * Lightweight authentication microservice using Hono framework and Better Auth.
 * Provides authentication endpoints for the Orchestrator 3 Stream application.
 *
 * Endpoints:
 * - GET/POST /api/auth/* - Better Auth endpoints (sign in, sign up, sign out, session)
 * - GET /health - Health check endpoint
 */

import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { cors } from "hono/cors";
import { auth } from "./auth.js";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

const app = new Hono();

// CORS middleware for frontend communication
app.use("/*", cors({
  origin: [
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "https://cash-dash.com",  // Production frontend
    process.env.FRONTEND_URL || "",
  ].filter(Boolean),
  credentials: true,
}));

// Mount Better Auth handler on /api/auth/*
// This handles all authentication requests (sign in, sign up, sign out, session management)
app.on(["GET", "POST"], "/api/auth/*", (c) => auth.handler(c.req.raw));

// Health check endpoint
app.get("/health", (c) => c.json({
  status: "ok",
  service: "orchestrator-auth-service",
  timestamp: new Date().toISOString()
}));

// Start server
// Railway injects PORT, fallback to AUTH_PORT or 9404
const port = parseInt(process.env.PORT || process.env.AUTH_PORT || "9404");
console.log(`\n🔐 Auth service running on port ${port}`);
console.log(`📍 Base URL: ${process.env.AUTH_BASE_URL || `http://localhost:${port}`}`);
console.log(`🌐 Environment: ${process.env.NODE_ENV || "development"}\n`);

serve({ fetch: app.fetch, port });
