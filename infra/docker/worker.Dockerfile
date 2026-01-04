FROM python:3.12-slim
WORKDIR /app
COPY apps/worker/ /app/apps/worker/
RUN pip install --no-cache-dir celery redis
CMD ["python", "-c", "print('worker skeleton: configure celery app here')"]
