# Backend image — serves both the API and the AI worker. They run as two
# separate services in production (different start commands, same image);
# the worker must never run inside the API process, so a slow or failing
# AI job can't affect request latency. See app/ai_jobs/main.py.
FROM python:3.11-slim

# libmagic is a *system* C library that python-magic wraps — pip/uv cannot
# install it, and app/utils/file_validation.py imports it at module load,
# so without this the API fails at startup rather than on first upload.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, in their own layer: they only re-resolve when the
# lockfile actually changes, so ordinary code edits get a fast rebuild.
# --frozen fails loudly if uv.lock is out of date rather than quietly
# resolving something different from what was tested locally.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Use the venv's interpreter directly — no `uv run` needed at runtime.
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Default command = the API. Migrations run here (not in the worker) so two
# services starting at once can't race each other applying the same
# revision. $PORT is injected by the host; 8000 is the local fallback.
# 0.0.0.0 (not the default 127.0.0.1) is required or the host's proxy
# can't reach the container.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
