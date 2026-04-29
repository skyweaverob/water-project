FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# The worker shares the api/ codebase. Railway should be configured with the repo root
# as the build context and `worker/Dockerfile` as the dockerfile path.
COPY api/pyproject.toml ./
RUN pip install --upgrade pip && pip install .
COPY api/ ./

CMD ["arq", "app.worker.WorkerSettings"]
