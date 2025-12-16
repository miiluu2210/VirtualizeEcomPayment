# Dockerfile for Cart Events Transformation Worker
# Optimized for processing large datasets with minimal image size

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy transformation scripts
COPY transformation/*.py ./

# Create directories for data
RUN mkdir -p /data/input /data/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command - can be overridden
CMD ["python", "transform_cart_events_extreme.py", \
     "--input", "/data/input/cart_events.json.gz", \
     "--output", "/data/output", \
     "--chunk-size", "100000"]
