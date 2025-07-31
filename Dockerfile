FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including git
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configure git globally
RUN git config --global user.email "XXXXXXX" \
    && git config --global user.name "XXXX" \
    && git config --global init.defaultBranch main

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd -m -u 1000 worker
USER worker

# Default command
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
