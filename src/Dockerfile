FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

WORKDIR /app

# Install runtime deps from pyproject.toml — single source of truth.
# Version pins live in pyproject.toml + ga-versions.yaml and are gated by
# scripts/accelerator-lint.py::sdks_pinned_to_ga. The image therefore ships
# exactly the SDK matrix that CI enforces; drift is impossible.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

EXPOSE 8000

# Workload-identity friendly: no secrets baked in; env vars come from Container App
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
