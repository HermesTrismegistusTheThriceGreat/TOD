# Auth Service - Hono + Better Auth
# Node.js microservice for authentication

# ---- Build Stage ----
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies including devDependencies for build
RUN npm install --include=dev

# Copy source code
COPY . .

# Create tsconfig.json (since it may be excluded by .gitignore)
# Using Node16 module resolution for proper ESM support in Node.js
RUN echo '{ \
  "compilerOptions": { \
    "target": "ES2022", \
    "module": "Node16", \
    "moduleResolution": "Node16", \
    "esModuleInterop": true, \
    "strict": true, \
    "skipLibCheck": true, \
    "outDir": "./dist", \
    "rootDir": "./src" \
  }, \
  "include": ["src/**/*"] \
}' > tsconfig.json

# Build TypeScript
RUN npm run build

# ---- Production Stage ----
FROM node:20-alpine AS production

WORKDIR /app

# Copy package files and install production dependencies only
COPY package.json package-lock.json* ./
RUN npm install --omit=dev

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Railway injects PORT env var
ENV PORT=9404
EXPOSE 9404

# Set production environment
ENV NODE_ENV=production

# Start the server
CMD ["node", "dist/index.js"]
