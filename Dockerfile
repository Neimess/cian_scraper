FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR /app

COPY . /app

RUN ["uv", "sync", "--no-dev"]

CMD ["uv", "run", "--color", "auto", "--no-cache", "main.py" ]