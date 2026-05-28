FROM node:24-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY src ./src
COPY --from=frontend-builder /src/tsuzuri/static ./src/tsuzuri/static
COPY settings.toml ./settings.toml

RUN mkdir -p outputs

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "tsuzuri.api:app", "--host", "0.0.0.0", "--port", "8000"]
