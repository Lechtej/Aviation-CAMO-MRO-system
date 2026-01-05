FROM python:3.12-slim
WORKDIR /app

COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# API code
COPY apps/api/src/ /app/
# API contract (OpenAPI yaml) for runtime docs
COPY docs/02_api/openapi.yaml /app/openapi.yaml

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
