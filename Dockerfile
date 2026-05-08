# SpinAnalyzer v2 Backend
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps from pyproject.toml
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source
COPY src/ ./src/
COPY run_api.py .

RUN mkdir -p \
    dataset/phh_hands \
    dataset/decision_points \
    dataset/dps \
    dataset/villain_profiles \
    dataset/original_hands \
    dataset/uploads \
    indices

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v2/health')" || exit 1

CMD ["uvicorn", "src.api.v2.main:app", "--host", "0.0.0.0", "--port", "8000"]
