#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")" || exit 1

# Stop and remove existing containers
docker-compose down

# Start Docker Compose
docker-compose up -d

docker-compose exec api python -m scripts.seed
docker-compose exec api python -m scripts.seed_plans
docker compose exec api python -m scripts.seed_feature_finance
docker compose exec api python -m scripts.seed_feature_relationships
