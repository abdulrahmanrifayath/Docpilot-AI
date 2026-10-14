# =============================================================================
# DocPilot AI Backend Dockerfile
# Production-ready, secure, unprivileged container with healthcheck
# =============================================================================

FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in isolated wheels/layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime system packages (git is required for Git repository cloning)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python site-packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create unprivileged application user
RUN groupadd -r docpilot && useradd -r -g docpilot -d /app -s /sbin/nologin docpilot

# Create required persistent data and uploads storage
RUN mkdir -p /app/data /app/uploads /app/data/projects /app/data/vector_store && \
    chown -R docpilot:docpilot /app

# Copy application source code
COPY --chown=docpilot:docpilot app /app/app

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    DEBUG=false \
    HOST=0.0.0.0 \
    PORT=8000

# Switch to unprivileged user
USER docpilot

EXPOSE 8000

# Container healthcheck against /health endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
