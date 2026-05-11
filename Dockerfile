FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HOME=/tmp \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

ENTRYPOINT ["/app/.venv/bin/taid"]
