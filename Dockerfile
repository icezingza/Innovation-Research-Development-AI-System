# =====================================================================
# NRE v5.0.0 Sovereign Edition — Multi-Stage Production Dockerfile
# Optimized for high-security, minimal footprint, and zero root usage
# =====================================================================

# Stage 1: Build Dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Enable compiler dependencies for security patches and native module optimization
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements to leverage build caching
COPY requirements.txt .

# Install dependencies into a separate, clean virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Production Environment
FROM python:3.12-slim AS production

# Enforce clean, non-buffering production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Copy the pre-built isolated virtual environment packages from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy system code, database migrations and startup configurations
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Establish restricted access non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose microservice port
EXPOSE 8000

# Custom production-grade container health check hitting the exempt health route
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Launch microservice
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
