# SpinAnalyzer Backend Dockerfile
# Multi-stage build for optimized image size

FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run_api.py .

# Create necessary directories
RUN mkdir -p dataset/phh_hands dataset/decision_points indices uploads/temp uploads/processed

# Copy dataset files if they exist (optional for fresh deployments)
COPY dataset/*.parquet ./dataset/ 2>/dev/null || echo "No parquet files found, will be generated on upload"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "run_api.py"]
