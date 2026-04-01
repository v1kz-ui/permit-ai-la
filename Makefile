.PHONY: dev test lint migrate seed dashboard mobile clean

# Start core services (postgres + redis) and API server
dev:
	docker compose up -d postgres redis
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start all services including Airflow
dev-full:
	docker compose --profile airflow --profile mail up -d
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests with coverage
test:
	cd backend && pytest --cov=app --cov-report=term-missing --cov-report=xml tests/

# Run linting
lint:
	cd backend && ruff check . && ruff format --check . && mypy app/

# Fix lint issues
lint-fix:
	cd backend && ruff check --fix . && ruff format .

# Run database migrations
migrate:
	cd backend && alembic upgrade head

# Create a new migration
migration:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Seed reference data
seed:
	cd backend && python -m scripts.seed_reference_data

# Start Next.js dashboard dev server
dashboard:
	cd dashboard && npm run dev

# Start Expo mobile dev server
mobile:
	cd mobile && npx expo start

# Install all dependencies
install:
	cd backend && pip install -e ".[dev,ml]"
	cd dashboard && npm install
	cd mobile && npm install

# Stop all Docker services
down:
	docker compose --profile airflow --profile mail down

# Clean up everything
clean:
	docker compose --profile airflow --profile mail down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
