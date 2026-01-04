FROM node:20-alpine
WORKDIR /app
COPY apps/web/ /app/apps/web/
RUN echo "web skeleton - add build steps later"
CMD ["sh", "-c", "echo web skeleton; sleep 3600"]
