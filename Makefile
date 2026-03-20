.PHONY: help install install-dev lint format test coverage clean docker-up docker-down docker-logs

help:
	@echo "CampusNow - Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install production dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run ruff and flake8 linter"
	@echo "  make format        - Format code with ruff/black"
	@echo "  make format-check  - Check code formatting (no changes)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run pytest"
	@echo "  make test-cov      - Run pytest with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     - Start all services (docker-compose up -d)"
	@echo "  make docker-down   - Stop all services (docker-compose down)"
	@echo "  make docker-logs   - Show service logs (docker-compose logs -f)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Remove cache and build files"

install:
	pip install --upgrade pip
	cd scraper-service && pip install -r requirements.txt
	cd api-service && pip install -r requirements.txt

install-dev:
	pip install --upgrade pip
	cd scraper-service && pip install -r requirements.txt
	cd api-service && pip install -r requirements.txt
	pip install ruff flake8 black pytest pytest-asyncio pytest-cov

lint:
	@echo "🔍 Running Ruff linter..."
	ruff check scraper-service api-service
	@echo ""
	@echo "🔍 Running Flake8 linter..."
	python3 -m flake8 scraper-service api-service
	@echo "✅ Lint check passed!"

format:
	@echo "🎨 Formatting code with Ruff..."
	ruff format scraper-service api-service
	@echo "🎨 Formatting code with Black..."
	black scraper-service api-service --line-length=100
	@echo "✅ Code formatted!"

format-check:
	@echo "🔍 Checking code format..."
	ruff format --check scraper-service api-service
	black --check scraper-service api-service --line-length=100
	@echo "✅ Format check passed!"

test:
	@echo "🧪 Running tests..."
	pytest -v --cov=scraper-service --cov=api-service --cov-report=term-missing

test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest -v --cov=scraper-service --cov=api-service --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report generated: htmlcov/index.html"

clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'dist' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'build' -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d
	@echo "✅ Services started!"
	docker-compose ps

docker-down:
	@echo "🛑 Stopping Docker services..."
	docker-compose down
	@echo "✅ Services stopped!"

docker-logs:
	docker-compose logs -f

docker-build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Images built!"

all: clean install-dev lint format test
	@echo "✅ All checks passed!"
