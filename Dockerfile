FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server.py ./server.py

ENV HOST=0.0.0.0

CMD ["python3", "server.py"]
