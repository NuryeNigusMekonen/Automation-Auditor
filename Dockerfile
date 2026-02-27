FROM python:3.12.8-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    git \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appgroup \
 && useradd --system --create-home --gid appgroup appuser

# Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && python -m pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

RUN chown -R appuser:appgroup /app

COPY scripts/container-entrypoint.sh /usr/local/bin/container-entrypoint.sh
RUN chmod +x /usr/local/bin/container-entrypoint.sh

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -m src.run --help >/dev/null 2>&1 || exit 1

# Set entry point and default command
ENTRYPOINT ["/usr/local/bin/container-entrypoint.sh"]
CMD ["--help"]