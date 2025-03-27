FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR /app

COPY . /app

RUN apt update && apt install -y ca-certificates && rm -rf /var/lib/apt/lists/*

RUN ["uv", "sync", "--no-dev"]


CMD ["uv", "run", "--color", "auto", "--no-cache", "main.py" ]