FROM python:3.12-slim

WORKDIR /app

COPY apps/web/ /app/

EXPOSE 3000

CMD ["python", "-m", "http.server", "3000", "--bind", "0.0.0.0"]
