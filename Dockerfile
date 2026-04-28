# FlowSight backend image — for Cloud Run.
# Slim Python image; pulls hmmlearn + numpy + scipy via wheels.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# System deps for scipy/hmmlearn wheels (BLAS) and curl for health checks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for cacheable layer.
COPY requirements.txt requirements-api.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt -r requirements-api.txt

# Copy source.
COPY src ./src
COPY pyproject.toml ./
RUN pip install -e .

# Cloud Run injects $PORT (default 8080); bind to 0.0.0.0.
EXPOSE 8080
CMD ["sh", "-c", "uvicorn flowsight.api.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
