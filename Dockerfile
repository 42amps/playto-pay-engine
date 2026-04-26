# Production Dockerfile: builds React frontend and bundles into Django

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: Django backend
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy built frontend assets into Django's static directory.
# Vite outputs to dist/assets/ and base: '/static/' makes index.html
# reference /static/assets/... so we preserve the assets/ folder.
RUN mkdir -p /app/static/assets /app/templates
COPY --from=frontend-builder /frontend/dist/assets/ /app/static/assets/
COPY --from=frontend-builder /frontend/dist/index.html /app/templates/index.html

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "playto.wsgi:application", "--bind", "0.0.0.0:8000"]
