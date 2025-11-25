FROM node:18 AS frontend-build

WORKDIR /app/client/procure2pay

COPY ./client/procure2pay/package*.json ./
RUN npm ci

COPY ./client/procure2pay/ ./
RUN npm run build

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./server/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy server source
COPY ./server/ /app/server/

# Create directories if needed
RUN mkdir -p /app/server/home/templates /app/server/static/assets /app/logs

# Copy built frontend
COPY --from=frontend-build /app/client/procure2pay/dist/index.html /app/server/home/templates/index.html
COPY --from=frontend-build /app/client/procure2pay/dist/assets /app/server/static/assets

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

WORKDIR /app/server

RUN python manage.py collectstatic --noinput || true

USER appuser

CMD ["gunicorn", "procure2pay.wsgi:application", "--bind", "0.0.0.0:8000"]
