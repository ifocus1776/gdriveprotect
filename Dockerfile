# Multi-stage build for production-ready container
FROM python:3.11-slim as builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=src.main
ENV FLASK_ENV=production
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/.config/gcloud/application_default_credentials.json

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

# Create app user
RUN adduser --disabled-password --gecos '' appuser

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser README.md .
COPY --chown=appuser:appuser LICENSE .
COPY --chown=appuser:appuser HYBRID_VAULT_SETUP.md .

# Create necessary directories
RUN mkdir -p /app/.config/gcloud \
    && mkdir -p /app/logs \
    && mkdir -p /app/temp \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check with proper timeout
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/vault/health || exit 1

# Run the application with proper signal handling
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

# Development stage (optional)
FROM production as development

USER root

# Install development dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        vim \
        && rm -rf /var/lib/apt/lists/*

# Switch back to app user
USER appuser

# Development command with auto-reload
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000", "--debug"]
