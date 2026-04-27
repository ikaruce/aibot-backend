FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Copy source and templates
COPY src/ src/
COPY templates/ templates/

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "aibot.main:app", "--host", "0.0.0.0", "--port", "8000"]
