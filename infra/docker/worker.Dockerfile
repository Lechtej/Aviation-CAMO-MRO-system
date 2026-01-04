FROM python:3.12-slim
WORKDIR /app
COPY apps/worker/src/ /app/
RUN pip install --no-cache-dir celery redis
CMD ["python", "worker.py"]
