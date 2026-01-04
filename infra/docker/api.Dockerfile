FROM python:3.12-slim
WORKDIR /app

# API code
COPY apps/api/src/ /app/
# API contract (OpenAPI yaml) for runtime docs
COPY docs/02_api/openapi.yaml /app/openapi.yaml

RUN pip install --no-cache-dir fastapi uvicorn pyyaml

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
