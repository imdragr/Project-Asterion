FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=dotenv/dotenvx:latest /usr/local/bin/dotenvx /bin/dotenvx
# Keep the venv OUTSIDE /code so the bind-mount can't shadow it with the host's .venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy
WORKDIR /code
COPY pyproject.toml uv.lock ./

FROM base AS dev
RUN uv sync --frozen
COPY . .
# dotenvx decrypts .env using the key injected at RUNTIME (never baked in)
CMD ["dotenvx", "run", "--", "uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
RUN uv sync --frozen --no-dev
COPY . .
CMD ["dotenvx", "run", "-f", ".env.production", "--", "uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]