# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.23 AS uv

FROM python:3.14-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY streamlit_app.py ./
COPY .streamlit ./.streamlit

RUN uv sync --locked --no-dev

FROM runtime AS backend

EXPOSE 8010

CMD ["uvicorn", "supportflow.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1", "--no-proxy-headers", "--no-access-log"]

FROM runtime AS frontend

EXPOSE 8510

CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8510", "--server.headless", "true"]
