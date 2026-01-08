.PHONY: help install dev test lint format clean run migrate seed

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Install dev dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean temporary files"
	@echo "  make run        - Run the application"
	@echo "  make migrate    - Migrate Database"
	@echo "  make seed       - Seed the database"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install pytest-watch

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-watch:
	pytest-watch tests/ -- -v

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/ scripts/
	isort src/ tests/ scripts/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

run:
	python -m src.main

migrate:
	python -m scripts.migrate

seed:
	python -m scripts.seed

shell:
	python -i -c "from src.utils import get_db; from src.repositories import *; from src.services import *; db = get_db()"


