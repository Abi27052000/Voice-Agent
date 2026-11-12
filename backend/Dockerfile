# Backend API for the hosted demo (Google Cloud Run).
# Build context: backend/.  Cloud Run provides $PORT (default 8080).

FROM python:3.11-slim

# uv, pinned to the version used to create uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.8.12 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

# Demo defaults. The SQLite file lives in /tmp (Cloud Run's writable, in-memory
# filesystem), so each new instance starts fresh and re-seeds fictional data.
ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL="sqlite:////tmp/app.db" \
    PUBLIC_DEMO=true \
    SEED_DEMO_DATA=true \
    PORT=8080

RUN useradd --create-home --uid 10001 app
USER app

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
