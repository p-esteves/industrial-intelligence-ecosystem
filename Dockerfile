# ============================================================
# Industrial Multi-Agent Ecosystem — Backend Dockerfile
# ============================================================

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY config.py .
COPY events.py .
COPY api/ ./api/
COPY core/ ./core/
COPY agents/ ./agents/
COPY workflow/ ./workflow/

RUN mkdir -p /app/data/docs /app/data/.faiss_index

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
