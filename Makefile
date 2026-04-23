.PHONY: help install install-dev lint format test coverage clean docker-up docker-down docker-logs docker-seed-mock security pre-commit ci-local quality complexity release release-check release-rc all

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
	@echo "  make quality       - Run all quality checks (lint + format + complexity)"
	@echo "  make complexity    - Analyze code complexity with Radon"
	@echo ""
	@echo "Security:"
	@echo "  make security      - Run security scan (bandit + safety)"
	@echo "  make pre-commit    - Install and run pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run pytest"
	@echo "  make test-cov      - Run pytest with coverage report"
	@echo "  make ci-local      - Run full CI pipeline locally"
	@echo ""
	@echo "Release & Deployment:"
	@echo "  make release-check - Verify ready for release"
	@echo "  make release       - Create release (VERSION=1.0.0)"
	@echo "  make release-rc    - Create RC release (VERSION=1.0.0)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     - Start all services (docker-compose up -d)"
	@echo "  make docker-down   - Stop all services (docker-compose down)"
	@echo "  make docker-logs   - Show service logs (docker-compose logs -f)"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-seed-mock - Run one-shot mock seeder (without timetable data)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Remove cache and build files"
	@echo "  make all           - Full pipeline: clean install-dev lint format test"

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

docker-seed-mock:
	@echo "🌱 Running mock seeder (excluding timetable collections)..."
	docker-compose --profile seed run --rm mock-seeder
	@echo "✅ Mock data seed complete!"

# Security scanning targets
security:
	@echo "🔒 Running security scans..."
	@if command -v bandit &> /dev/null; then \
		echo "🔐 Running Bandit..."; \
		bandit -r scraper-service api-service -f json -o bandit-report.json || true; \
		echo "✅ Bandit scan complete"; \
	else \
		echo "⚠️  Bandit not installed. Install it with: pip install bandit"; \
	fi
	@if command -v safety &> /dev/null; then \
		echo "🔐 Checking dependencies with Safety..."; \
		safety check --json || true; \
	else \
		echo "⚠️  Safety not installed. Install it with: pip install safety"; \
	fi
	@echo "✅ Security scan complete!"

# Code quality comprehensive check
quality: lint format-check complexity
	@echo "✅ All quality checks passed!"

# Code complexity analysis
complexity:
	@echo "📊 Analyzing code complexity..."
	@if command -v radon &> /dev/null; then \
		radon cc scraper-service api-service -a -nb || true; \
		radon metrics scraper-service api-service -nb || true; \
	else \
		echo "⚠️  Radon not installed. Install it with: pip install radon"; \
	fi

# Pre-commit hooks
pre-commit:
	@echo "🔧 Setting up pre-commit hooks..."
	@if command -v pre-commit &> /dev/null; then \
		pre-commit install; \
		pre-commit run --all-files; \
		@echo "✅ Pre-commit hooks installed and executed!"; \
	else \
		echo "⚠️  pre-commit not installed. Install it with: pip install pre-commit"; \
	fi

# Full CI pipeline locally
ci-local: clean install-dev lint format-check test security complexity
	@echo ""
	@echo "✅ ====================================="
	@echo "✅ FULL CI PIPELINE PASSED LOCALLY! ✅"
	@echo "✅ ====================================="
	@echo ""

# Release targets
release-check:
	@echo "🔍 Pre-release checks..."
	@echo ""
	@echo "1️⃣  Checking CHANGELOG.md..."
	@if [ ! -f CHANGELOG.md ]; then \
		echo "❌ CHANGELOG.md not found!"; \
		exit 1; \
	fi
	@echo "✅ CHANGELOG.md found"
	@echo ""
	@echo "2️⃣  Running full CI pipeline..."
	@$(MAKE) ci-local > /dev/null 2>&1 && echo "✅ CI pipeline passed" || (echo "❌ CI pipeline failed"; exit 1)
	@echo ""
	@echo "3️⃣  Current git status:"
	@git status --short || true
	@echo ""
	@echo "✅ All pre-release checks passed!"
	@echo ""
	@echo "📋 Next steps:"
	@echo "  1. Update CHANGELOG.md with your changes"
	@echo "  2. Commit: git add . && git commit -m 'chore: prepare release'"
	@echo "  3. Create tag: make release VERSION=1.0.0"

release: release-check
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION not specified!"; \
		echo "Usage: make release VERSION=1.0.0"; \
		exit 1; \
	fi
	@echo ""
	@echo "🏷️  Creating release tag v$(VERSION)..."
	@echo ""
	@git tag -a v$(VERSION) -m "Release version $(VERSION)" || (echo "❌ Tag already exists!"; exit 1)
	@echo "✅ Tag created: v$(VERSION)"
	@echo ""
	@echo "🚀 Pushing tag to GitHub (this will trigger Release workflow)..."
	@git push origin v$(VERSION)
	@echo ""
	@echo "✅ Tag pushed! Release workflow is running:"
	@echo "   👉 https://github.com/$$GITHUB_REPOSITORY/actions"
	@echo ""
	@echo "ℹ️  Release will include:"
	@echo "   • Final tests"
	@echo "   • Lint checks"
	@echo "   • GitHub Release with auto-generated notes"
	@echo "   • Docker images: campusnow:scraper-v$(VERSION)"
	@echo "   • Docker images: campusnow:api-v$(VERSION)"

release-rc: release-check
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION not specified!"; \
		echo "Usage: make release-rc VERSION=1.0.0"; \
		exit 1; \
	fi
	@echo ""
	@echo "🏷️  Creating release candidate tag v$(VERSION)-rc1..."
	@echo ""
	@git tag -a v$(VERSION)-rc1 -m "Release Candidate: v$(VERSION)-rc1" || (echo "❌ RC tag already exists!"; exit 1)
	@echo "✅ RC Tag created: v$(VERSION)-rc1"
	@echo ""
	@echo "🚀 Pushing RC tag to GitHub (this will trigger Release workflow)..."
	@git push origin v$(VERSION)-rc1
	@echo ""
	@echo "✅ RC Tag pushed! Release workflow is running..."
	@echo "   👉 https://github.com/$$GITHUB_REPOSITORY/actions"
	@echo ""
	@echo "ℹ️  This RC will be marked as 'pre-release' on GitHub"

all: clean install-dev lint format test
	@echo "✅ All checks passed!"
