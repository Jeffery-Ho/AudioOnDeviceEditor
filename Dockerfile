FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server.py index.html backend-config.js ./

ENV HOST=0.0.0.0
ENV PORT=7860
ENV MAX_UPLOAD_BYTES=104857600

EXPOSE 7860
CMD ["python3", "server.py"]
