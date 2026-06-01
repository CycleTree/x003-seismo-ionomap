FROM python:3.12-slim

ARG RINGO_VERSION=v0.9.6

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    tar \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL -o /tmp/ringo.tgz https://terras.gsi.go.jp/software/ringo/dist/${RINGO_VERSION}/ringo-${RINGO_VERSION}-linux64.tgz \
    && tar -xzf /tmp/ringo.tgz -C /tmp \
    && install -m 0755 /tmp/ringo-${RINGO_VERSION}-linux64/ringo /usr/local/bin/ringo \
    && rm -rf /tmp/ringo.tgz /tmp/ringo-${RINGO_VERSION}-linux64

COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000
