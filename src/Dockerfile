FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

WORKDIR /app

# Install runtime deps only (dev deps stay out of the runtime image)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "agent-framework>=0.1.0,<0.2.0" \
        "azure-ai-projects>=1.0.0,<2.0.0" \
        "azure-ai-agents>=1.0.0,<2.0.0" \
        "azure-identity>=1.17.0,<2.0.0" \
        "azure-monitor-opentelemetry>=1.6.0,<2.0.0" \
        "azure-search-documents>=11.5.0,<12.0.0" \
        "fastapi>=0.115.0,<0.116.0" \
        "pydantic>=2.9.0,<3.0.0" \
        "httpx>=0.27.0,<1.0.0" \
        "uvicorn[standard]>=0.30.0,<0.31.0"

COPY src ./src

EXPOSE 8000

# Workload-identity friendly: no secrets baked in; env vars come from Container App
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
