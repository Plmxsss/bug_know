ARG PYTHON_BASE_IMAGE=python:3.11-slim
FROM ${PYTHON_BASE_IMAGE} AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts

RUN groupadd --gid 10001 agriguard \
    && useradd --uid 10001 --gid agriguard --create-home agriguard \
    && mkdir -p /app/storage/uploads/annotated /app/models/embeddings \
    && chown -R agriguard:agriguard /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime-base AS api

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[agent]"

USER agriguard

FROM api AS rag

USER root

RUN python -m pip install ".[rag]"

USER agriguard

FROM rag AS full

USER root

RUN python -m pip install ".[ml]"

USER agriguard

# A plain `docker build backend` stays lightweight. Compose can explicitly
# select `rag` or `full` when local model dependencies are required.
FROM api AS default
