# syntax=docker/dockerfile:1

# --- Stage 1: build the React app --------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /build
COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci
COPY apps/frontend/ ./
RUN npm run build


# --- Stage 2: Python API that also serves the built app ----------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CADENCE_DATA_DIR=/data/tcx \
    CADENCE_DB=/data/db/cadence.db \
    CADENCE_STATIC_DIR=/app/static

WORKDIR /app
COPY apps/backend/pyproject.toml ./
COPY apps/backend/src ./src
RUN pip install --no-cache-dir .

COPY --from=frontend /build/dist ./static

# Run as a normal user. Its uid should match the owner of the database folder
# on the host (1000 is the first user on Debian / Raspberry Pi OS).
ARG UID=1000
RUN useradd --uid ${UID} --create-home cadence \
    && mkdir -p /data/tcx /data/db \
    && chown cadence /data/db
USER cadence

EXPOSE 8000
HEALTHCHECK --interval=1m --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

CMD ["uvicorn", "cadence_ia.api:app", "--host", "0.0.0.0", "--port", "8000"]
