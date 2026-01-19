# Orchestrator 3 Stream Frontend - Production Dockerfile
# Vue 3 + Vite build served by nginx

# ---- Build Stage ----
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build args for Vite (injected at build time)
ARG VITE_API_BASE_URL
ARG VITE_WEBSOCKET_URL

# Set env vars for build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WEBSOCKET_URL=$VITE_WEBSOCKET_URL

# Build the app
RUN npm run build

# ---- Production Stage ----
FROM nginx:alpine AS production

# Copy custom nginx config template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Railway injects PORT env var - nginx will substitute it
ENV PORT=80
EXPOSE 80

# Use envsubst to replace PORT in nginx config, then start nginx
CMD sh -c "envsubst '\$PORT' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
