FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f
RUN pip install --no-cache-dir uv==0.10.7
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen && useradd -m -u 10001 demo && mkdir -p /app/.local && chown demo:demo /app/.local
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER demo
CMD ["python", "-m", "p19.api"]
