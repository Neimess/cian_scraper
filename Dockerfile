FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR /app

COPY . /app

RUN ["uv", "sync", "--no-dev"]

ENV PYTHONPATH="/app"

CMD ["uv", "run", "main.py"]