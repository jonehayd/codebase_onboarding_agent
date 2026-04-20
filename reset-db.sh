#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Tearing down postgres..."
docker-compose down -v

echo "Starting postgres..."
docker-compose up -d db

echo "Waiting for postgres to be ready..."
until docker-compose exec db pg_isready -U postgres -q; do
  sleep 1
done

echo "Running migrations..."
cd backend
alembic upgrade head

echo "Database reset complete."
