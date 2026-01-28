.PHONY: help install dev test lint format clean run run-worker stop migrate seed

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make dev              - Install dev dependencies"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "  make clean            - Clean temporary files"
	@echo "  make run              - Run the application (requires worker running)"
	@echo "  make run-worker       - Run the background worker"
	@echo "  make run-scheduler    - Run the scheduler"
	@echo "  make stop             - Stop application and workers"
	@echo "  make migrate          - Migrate Database"
	@echo "  make seed             - Seed the database"

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
	rm -f worker.log scheduler.log app.log

run-worker:
	python -m src.core.queue.worker >> worker.log 2>&1 &

run-scheduler:
	python -m src.modules.conversation.workers.scheduler >> scheduler.log 2>&1 &
	@echo "✅ Scheduler is running."

check-worker:
	@if ! pgrep -f "src.core.queue.worker" > /dev/null; then \
		echo "❌ Error: Worker is not running!"; \
		echo "👉 Please run 'make run-worker' in a separate terminal first."; \
		exit 1; \
	else \
		echo "✅ Worker is running."; \
	fi

run: check-worker
	python -m src.main >> app.log 2>&1 &
	@echo "✅ Application is running."
	@echo "-> see app.log for more details."

stop:
	@echo "Stopping application and workers..."
	@-pkill -f "src.main" || echo "Application was not running."
	@-pkill -f "src.core.queue.worker" || echo "Worker was not running."
	@-pkill -f "src.modules.conversation.workers.scheduler" || echo "Scheduler was not running."
	@echo "Stopped."

migrate:
	python -m scripts.migrate

seed:
	@echo "Seeding database..."
	python -m scripts.seed
	@echo "\n---\n"
	python -m scripts.seed_feature_finance
	@echo "\n---\n"
	python -m scripts.seed_feature_relationships
	@echo "\n---\n"

shell:
	python -i -c "from src.utils import get_db; from src.repositories import *; from src.services import *; db = get_db()"


