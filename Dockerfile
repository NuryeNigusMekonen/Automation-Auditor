FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && python -m pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set entry point and default command
ENTRYPOINT ["python", "-m", "src.run"]
CMD ["--help"]