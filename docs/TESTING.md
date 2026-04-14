# Testing & Quality Assurance

## 📊 Übersicht

CampusNow nutzt ein umfassendes Testing- und Quality-Assurance-Framework, um hohe Codequalität zu sichern.

## 🧪 Testing Framework

### Tools
- **pytest** - Test Runner
- **pytest-cov** - Coverage Tracking
- **pytest-asyncio** - Async Test Support
- **httpx** - HTTP Client für API Tests

### Test Struktur

```
scraper-service/
├── test_scraper.py          # Integration Tests
├── scraper/
│   ├── starplan_scraper.py
│   └── ical_parser.py
└── requirements.txt

api-service/
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_models.py
│   └── conftest.py
├── app/
│   ├── main.py
│   ├── models/
│   └── routers/
└── requirements.txt
```

---

## ✍️ Tests Schreiben

### Basic Test Pattern

```python
import pytest
from scraper.starplan_scraper import StarPlanScraper

class TestStarPlanScraper:
    """Tests für StarPlan Scraper"""
    
    @pytest.fixture
    def scraper(self):
        """Setup Scraper Instance"""
        return StarPlanScraper("https://splan.hs-aalen.de")
    
    def test_discover_runtime_config(self, scraper):
        """Test Runtime Config Discovery"""
        config = scraper._discover_runtime_config()
        
        assert config is not None
        assert "path" in config
        assert "lang" in config
        assert config["lang"] in ["de", "en"]
    
    def test_construct_ical_url(self, scraper):
        """Test iCal URL Construction"""
        url = scraper._construct_ical_url("room", "123")
        
        assert url is not None
        assert "/ical" in url
        assert "roomid=123" in url
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async operations"""
    result = await some_async_function()
    assert result is not None
```

### Fixtures & Mocks

```python
@pytest.fixture
def mock_response(monkeypatch):
    """Mock HTTP Response"""
    def mock_get(*args, **kwargs):
        return {"status_code": 200, "json": lambda: {"data": []}}
    
    monkeypatch.setattr("requests.get", mock_get)

def test_with_mock(mock_response):
    """Test mit Mock"""
    pass
```

---

## 📈 Code Coverage

### Coverage Target
```
Gesamtes Projekt: ≥ 80%
Kritische Module: ≥ 90%
```

### Coverage anschauen

```bash
# Terminal Report
make test-cov

# HTML Report (öffne im Browser)
open api-service/htmlcov/index.html
# oder
xdg-open api-service/htmlcov/index.html  # Linux
start api-service/htmlcov/index.html      # Windows
```

### Coverage Rules

```python
# Skip in Coverage (nicht für alle nutzen!)
def not_implemented():  # pragma: no cover
    """Still under development"""
    raise NotImplementedError()

@pytest.mark.skip(reason="TODO")
def test_future_feature():
    pass
```

---

## 🧬 Test Execution

### Lokal

```bash
# Alle Tests
pytest

# Specific Test
pytest scraper-service/test_scraper.py::test_name

# Mit Verbosity
pytest -v

# Stop bei erstem Fehler
pytest -x

# Only Failed Tests
pytest --lf

# Mit Markers
pytest -m "not slow"
```

### CI/CD

```bash
# In GitHub Actions
pytest --cov=scraper-service --cov=api-service \
       --cov-report=xml --cov-report=term-missing
```

---

## 🎯 Test Categories

### Unit Tests
```python
# Test einzelner Funktionen/Methoden
def test_extract_room_id():
    result = extract_room_id("Raum 123")
    assert result == "123"
```

### Integration Tests
```python
# Test anhand echter APIs
def test_scraper_live():
    scraper = StarPlanScraper("https://splan.hs-aalen.de")
    rooms = scraper._scrape_rooms()
    assert len(rooms) > 0
```

### Performance Tests
```python
@pytest.mark.performance
def test_scraper_performance():
    start = time.time()
    results = scraper.scrape_ical_links()
    duration = time.time() - start
    
    assert duration < 30  # Max 30 Sekunden
```

---

## ✅ Quality Gates

### Lint Check
```bash
make lint
# Ruff + Flake8
```

### Format Check
```bash
make format-check
# Black Format Validation
```

### Security Scan
```bash
make security
# Bandit + Safety
```

### Complexity Analysis
```bash
make complexity
# Radon Code Metrics
```

---

## 🐛 Debugging Tests

### Mit pytest

```bash
# Verbose + Show Prints
pytest -v -s

# Debugger einsteigen (breakpoint)
# Füge in Code: breakpoint()
# Oder: pytest --pdb

# Show Local Variables
pytest -l

# Traceback verbosity
pytest --tb=long
```

### Mit VSCode

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["-v", "${file}"],
            "console": "integratedTerminal"
        }
    ]
}
```

---

## 📊 Coverage Limits

```ini
[tool.coverage.report]
# Mindest-Coverage Prozentätze
fail_under = 80

# Exclude Lines
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

## 🔄 Test-driven Development (TDD)

### Red-Green-Refactor Zykus

1. **🔴 Red** - Write failing test
```python
def test_new_feature():
    result = new_feature()
    assert result == expected_value
```

2. **🟢 Green** - Write minimal code to pass
```python
def new_feature():
    return expected_value
```

3. **🔵 Refactor** - Improve code quality
```python
def new_feature():
    """Better implementation"""
    # Optimized code
    return expected_value
```

---

## 📚 Weitere Ressourcen

- [Pytest Dokumentation](https://docs.pytest.org/)
- [Coverage.py Docs](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [pytest Plugins](https://docs.pytest.org/en/latest/how-to.html#plugins)

---

## 🎓 Tipps & Tricks

1. **Tests lokal vor dem Push ausführen**
   ```bash
   make ci-local
   ```

2. **Coverage Report analysieren**
   - Öffne `htmlcov/index.html`
   - Suche nach roten Zeilen (nicht abgedeckt)
   - Schreibe Tests dafür

3. **Test isolation**
   - Keine Test-Abhängigkeiten
   - Fixtures für Setup/Teardown
   - Mock externe Services

4. **Aussagekräftige Assertions**
   ```python
   # ❌ Schlecht
   assert result
   
   # ✅ Gut
   assert len(result) > 0, "Expected non-empty list"
   assert result["status"] == "success"
   ```

---

## 🚀 Performance

Langsame Tests?

```bash
# Find slowest tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"

# Run in parallel (pytest-xdist)
pytest -n auto
```

---

**Viel Erfolg beim Testen! 🧪✨**
