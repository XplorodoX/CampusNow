# CampusNow - Development Guide

## 📋 Setup für Entwickler

### 1. Repository klonen
```bash
cd /home/flo/CampusNow
```

### 2. Python Environment aufsetzen
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install-dev
```

### 3. Pre-commit Hooks einrichten (optional aber empfohlen)
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Run once to check everything
```

---

## 🔍 Code Quality & Linting

### Ruff (Haupt-Linter)
```bash
# Check code
make lint

# Check + Fix automatically
ruff check --fix scraper-service api-service

# Format code
make format
```

### Flake8 (Ergänzungs-Linter)
```bash
# Run flake8
flake8 scraper-service api-service

# Show statistics
flake8 --statistics scraper-service api-service
```

### Formatierung mit Black
```bash
# Format code
black scraper-service api-service --line-length=100

# Check formatting (no changes)
black --check scraper-service api-service --line-length=100
```

### isort (Import Sorting)
```bash
# Sort imports
isort scraper-service api-service --profile black

# Check without changes
isort --check-only scraper-service api-service --profile black
```

### Alles auf einmal
```bash
# Run all quality checks
make all

# Docker-spezifisch
make docker-build
make docker-up
```

---

## 🧪 Testing

### Run Tests
```bash
# Simple test run
make test

# With coverage report
make test-cov

# Coverage HTML-Report öffnen
open htmlcov/index.html
```

### Test Structure
```
scraper-service/
├── tests/
│   ├── __init__.py
│   ├── test_starplan_scraper.py
│   ├── test_ical_parser.py
│   └── test_image_downloader.py

api-service/
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_lectures.py
│   └── test_rooms.py
```

---

## 📝 Code Style Richtlinien

### PEP 8 Standards
- Line length: **100 characters**
- Indentation: **4 spaces** (no tabs)
- Imports: **sorted with isort** (black-compatible)

### Naming Conventions
```python
# Classes: PascalCase
class StarplanScraper:
    pass

# Functions & variables: snake_case
def parse_ical_from_url(url):
    local_variable = None

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 10
```

### Import Order
```python
# 1. Standard library
import os
import logging
from datetime import datetime
from typing import List, Optional

# 2. Third-party packages
import requests
from pydantic import BaseModel

# 3. Local imports
from app.models import Lecture
from db.mongo_client import MongoDBClient
```

### Documentation
```python
def parse_ical_from_url(url: str, source_type: str = 'room') -> List[dict]:
    """
    Parse iCal file from URL and extract lecture data.

    Args:
        url: URL to the iCal file
        source_type: Either 'room' or 'course'

    Returns:
        List of lecture dictionaries

    Raises:
        requests.RequestException: If URL cannot be fetched
        icalendar.ParserError: If iCal format is invalid
    """
    pass
```

---

## 🔧 Common Development Tasks

### Adding a New Feature
1. Create feature branch: `git checkout -b feature/my-feature`
2. Write tests first (TDD approach)
3. Implement feature
4. Run `make all` to check everything
5. Commit: `git commit -m "feat: add my feature"`
6. Push and create Pull Request

### Debugging
```bash
# Run with logging
export LOG_LEVEL=DEBUG
python scraper-service/main.py

# Run specific test with verbose output
pytest -v tests/test_starplan_scraper.py::test_scrape_rooms -s

# Interactive debugger
pytest -v --pdb tests/test_starplan_scraper.py
```

### Performance Profiling
```bash
# Install profiler
pip install py-spy

# Profile script
py-spy record -o profile.svg -- python scraper-service/main.py

# View results
open profile.svg
```

---

## 🐳 Docker Development Workflow

### Building
```bash
# Build specific service
docker build -t campusnow-api:dev -f api-service/Dockerfile .
docker build -t campusnow-scraper:dev -f scraper-service/Dockerfile .

# Build all
make docker-build
```

### Running
```bash
# Start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

### Debugging in Container
```bash
# Shell into API container
docker-compose exec api bash

# Shell into Scraper
docker-compose exec scraper bash

# View MongoDB
docker-compose exec mongodb mongosh -u admin -p campusnow_secret_2025
```

---

## 🔐 Security Checks

### Dependency Scanning
```bash
# Check for known vulnerabilities
pip install safety
safety check

# Update dependencies
pip list --outdated
pip install --upgrade package_name
```

### Secret Detection
```bash
# Install detect-secrets
pip install detect-secrets

# Scan repository
detect-secrets scan

# Prevent secrets from being committed
detect-secrets install-hook .git/hooks/pre-commit
```

---

## 📊 Metrics

### Code Coverage Goals
- **Target**: > 80% coverage
- **Minimum**: > 70% coverage

```bash
make test-cov

# View coverage report
# See: htmlcov/index.html
```

### Complexity Metrics
```bash
# Install radon for metrics
pip install radon

# Check cyclomatic complexity
radon cc scraper-service api-service -a -s

# Check maintainability index
radon mi scraper-service api-service -s
```

---

## 🚀 Continuous Integration

### Local Pre-commit Validation
```bash
# Install
pip install pre-commit
pre-commit install

# Test
pre-commit run --all-files
```

### CI/CD Pipeline (Future)
Will be configured in `.github/workflows/` for:
- ✅ Linting (Ruff, Flake8, Black)
- ✅ Testing (Pytest)
- ✅ Coverage reports
- ✅ Dependency scanning

---

## 🐛 Troubleshooting

### "Ruff command not found"
```bash
pip install ruff
# or
pip install -r requirements.txt
```

### "Port already in use"
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Or docker
docker-compose down
```

### "MongoDB connection failed"
```bash
# Check if MongoDB is running
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb
```

### "Tests failing after changes"
```bash
# Clean cache
make clean

# Reinstall
make install-dev

# Run tests again
make test
```

---

## 📚 Resources

- **Ruff Docs**: https://docs.astral.sh/ruff/
- **Black Docs**: https://black.readthedocs.io/
- **Pytest Docs**: https://docs.pytest.org/
- **PEP 8**: https://pep8.org/
- **PEP 257**: https://peps.python.org/pep-0257/ (Docstrings)

---

## 💡 Best Practices

1. **Write tests first** (TDD approach)
2. **Keep functions small** (max 20-30 lines)
3. **Use type hints** for clarity
4. **Document public APIs** with docstrings
5. **Run linters before committing** (use pre-commit)
6. **Commit frequently** with clear messages
7. **Review your own code** before asking for review

---

## 👥 Code Review Checklist

Before submitting a PR:
- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Code is formatted (`make format`)
- [ ] No security issues
- [ ] Docstrings added/updated
- [ ] Type hints added
- [ ] Coverage >= 80%

---

**Last Updated**: 2025-03-20  
**Python Version**: 3.11+  
**Status**: 🟢 Ready for Development
