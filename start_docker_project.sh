#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")" || exit 1

# Stop and remove existing containers
docker-compose down

# force rebuild
if [ "$1" == "--force" ]; then
    docker-compose build
fi

# Start Docker Compose
docker-compose up -d

docker compose exec api python -m scripts.seed
docker compose exec api python -m scripts.seed_plans
docker compose exec api python -m scripts.seed_feature_finance
docker compose exec api python -m scripts.seed_feature_relationships

docker compose --profile tools up -d pgadmin