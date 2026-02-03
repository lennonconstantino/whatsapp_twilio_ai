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
	@echo "  make obs-up           - Start observability stack (Prometheus, Grafana, OTel)"
	@echo "  make obs-down         - Stop observability stack"

check-env:
	@python scripts/check_env.py

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
	@echo "Starting worker in background (logs -> worker.log)..."
	FORCE_COLOR=true python -m src.core.queue.worker >> worker.log 2>&1 &

run-scheduler:
	@echo "Starting scheduler in background (logs -> scheduler.log)..."
	FORCE_COLOR=true python -m src.modules.conversation.workers.scheduler >> scheduler.log 2>&1 &
	@echo "✅ Scheduler is running."

check-worker:
	@if ! pgrep -f "src.core.queue.worker" > /dev/null; then \
		echo "❌ Error: Worker is not running!"; \
		echo "👉 Please run 'make run-worker' first."; \
		exit 1; \
	else \
		echo "✅ Worker is running."; \
	fi

run: check-worker
	@echo "Starting application in background (logs -> app.log)..."
	FORCE_COLOR=true python -m src.main >> app.log 2>&1 &
	@echo "✅ Application is running."
	@echo "-> see logs: tail -f app.log worker.log scheduler.log"

stop:
	@echo "Stopping application and workers..."
	@-pkill -f "src.main" || echo "Application was not running."
	@-pkill -f "src.core.queue.worker" || echo "Worker was not running."
	@-pkill -f "src.modules.conversation.workers.scheduler" || echo "Scheduler was not running."
	@echo "Stopped."

restart: stop run-worker run-scheduler run
	@echo "✅ Application restarted."

migrate:
	@DATABASE_BACKEND=$$(grep DATABASE_BACKEND .env | cut -d '=' -f2 | cut -d '#' -f1 | xargs); \
	echo "Database backend detectado: [$$DATABASE_BACKEND]"; \
	case "$$DATABASE_BACKEND" in \
		supabase) \
			echo "Usando banco supabase"; \
			echo ""; echo "--CORE--"; echo ""; \
			python -m scripts.migrate; \
			echo ""; echo "--FEATURES--"; echo ""; \
			python -m scripts.migrate migrations/feature/; \
			echo "✅ Database migrated." ;; \
		postgres) \
			echo "Usando banco local"; \
			./scripts/migrate_postgres.sh; \
			echo "✅ Database migrated." ;; \
		*) \
			echo "❌ Error: Invalid DATABASE_BACKEND value. Must be 'postgres' or 'supabase'."; \
			exit 1 ;; \
	esac

seed:
	@echo "Seeding database..."
	python -m scripts.seed
	@echo "\n---\n"
	python -m scripts.seed_plans
	@echo "\n---\n"
	python -m scripts.seed_feature_finance
	@echo "\n---\n"
	python -m scripts.seed_feature_relationships
	@echo "\n---\n"	

obs-up:
	@echo "Starting Observability Stack..."
	docker-compose up -d otel-collector prometheus grafana zipkin
	@echo "✅ Observability Stack is running."
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "📈 Prometheus: http://localhost:9090"
	@echo "🔍 Zipkin: http://localhost:9411"

obs-down:
	@echo "Stopping Observability Stack..."
	docker-compose stop otel-collector prometheus grafana zipkin
	@echo "Stopped."


shell:
	python -i -c "from src.utils import get_db; from src.repositories import *; from src.services import *; db = get_db()"


