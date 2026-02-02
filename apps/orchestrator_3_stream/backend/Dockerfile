# Orchestrator 3 Stream Backend - Production Dockerfile
# Uses Astral UV for fast, reliable dependency management

FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies (no dev dependencies for production)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# ---- Production Stage ----
FROM python:3.12-slim AS production

# Install runtime dependencies for asyncpg and Node.js for Claude CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app .

# Note: .mcp.json.alpaca is gitignored (contains credentials)
# The application will use ALPACA_API_KEY and ALPACA_SECRET_KEY env vars
# set in Railway to configure the Alpaca MCP server at runtime

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add venv to PATH and ensure node modules are accessible
ENV PATH="/app/.venv/bin:/usr/lib/node_modules/.bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory for Claude SDK agents to /app
# This ensures .mcp.json.alpaca is found
ENV ORCHESTRATOR_WORKING_DIR=/app

# Railway injects PORT env var automatically
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8002}/health')" || exit 1

# Start command - Railway sets $PORT automatically
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
