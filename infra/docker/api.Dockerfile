FROM python:3.12-slim
WORKDIR /app
COPY apps/api/ /app/apps/api/
RUN pip install --no-cache-dir fastapi uvicorn
EXPOSE 8000
CMD ["uvicorn", "apps.api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
