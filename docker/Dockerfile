# syntax=docker/dockerfile:1

ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION:?} as base

LABEL PYTHON_VERSION=${PYTHON_VERSION}


RUN --mount=type=cache,target=/root/.cache \
    python -m pip install -U pip

RUN --mount=type=cache,target=/var/cache/apt \
        apt-get update && apt-get install -y \
            curl \
            siege

RUN --mount=type=cache,target=/root/.cache \
    pip install \
        guppy3 \
        objgraph \
        requests


ARG UVICORN_VERSION=0.18.3
LABEL UVICORN_VERSION=${UVICORN_VERSION:?}
RUN --mount=type=cache,target=/root/.cache \
    pip install uvicorn==${UVICORN_VERSION}


WORKDIR /home/root/leak
COPY client.py client.py
COPY server.py server.py

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]


FROM base
ARG STARLETTE_VERSION
LABEL STARLETTE_VERSION=${STARLETTE_VERSION:?}
RUN echo "installing starlette ${STARLETTE_VERSION}"
RUN --mount=type=cache,target=/root/.cache \
    pip install STARLETTE==${STARLETTE_VERSION}


