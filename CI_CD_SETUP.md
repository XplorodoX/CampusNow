# CI/CD Pipeline Dokumentation

Dieses Projekt verwendet **GitHub Actions** für eine umfassende CI/CD-Pipeline zur Gewährleistung von Softwarequalität.

## 🚀 Überblick

Die CI/CD-Pipeline wird automatisch bei jedem Push und Pull Request ausgelöst und führt folgende Checks durch:

### Pipelines

#### 1. **CI Pipeline** (`ci.yml`)
Läuft bei: Push zu `main`/`develop`, Pull Requests

**Stages:**
- **Lint & Test**
  - Python 3.9, 3.10, 3.11 Kompatibilität testen
  - Ruff und Flake8 Linting
  - Black Code Format Checks
  - Scraper & API Unit Tests
  - Coverage Report zu Codecov
  
- **Security Scan**
  - Bandit Security Scanning
  - Safety Dependency Checks
  
- **Docker Build**
  - Docker Images für Scraper Service
  - Docker Images für API Service

#### 2. **Code Quality Analysis** (`code-quality.yml`)
Läuft: Nach CI Pipeline erfolgreich, täglich um 2 Uhr UTC

**Features:**
- Radon Code Complexity Analysis
- Pylint Static Analysis
- Test Coverage Report (HTML)
- Vulnerable Dependency Check

#### 3. **Dependency Updates** (`dependencies.yml`)
Läuft: Jeden Montag um 9 Uhr UTC

**Features:**
- Automated dependency scanning
- Update notifications

#### 4. **Release & Deployment** (`release.yml`)
Läuft: Bei Tag Push (v*.*.*), manuell

**Features:**
- Final tests vor Release
- GitHub Release erstellen
- Docker Images bauen mit Version Tags

---

## 📋 Lokale Tests Vor Push

### Schnelle Checks
```bash
# Nur Linting
make lint

# Code Formatierung prüfen
make format-check

# Tests
make test

# Alles zusammen (lokal CI simulieren)
make ci-local
```

### Detaillierte Checks
```bash
# Code Komplexität
make complexity

# Security Scanning
make security

# Coverage Report
make test-cov
```

### Pre-commit Hooks (lokal)
```bash
# Einmalig installieren
make pre-commit

# Wird automatisch vor jedem Commit ausgeführt
```

---

## 🔐 Branch Protection Rules

Empfohlene Einstellungen für `main` Branch auf GitHub:

1. **Require status checks to pass before merging:**
   - ✅ CI Pipeline (lint-and-test)
   - ✅ Security Scan
   - ✅ Docker Build

2. **Require code reviews before merging:**
   - Mindestens 1 Approval

3. **Require branches to be up to date before merging:**
   - ✅ Enabled

4. **Include administrators:**
   - ✅ Emfohlen

### Einrichtung:
```
Settings → Branches → Branch Protection Rules → Add Rule
```

---

## 📊 Code Coverage

Coverage Reports:
- Wird automatisch zu [Codecov](https://codecov.io) hochgeladen
- Manual Coverage Report: `make test-cov` → `api-service/htmlcov/index.html`

**Ziel:** ≥ 80% Code Coverage

---

## 🔒 Security Best Practices

### Tools in der Pipeline:

1. **Bandit** - Python Security Issues
   ```bash
   make security
   ```

2. **Safety** - Vulnerable Dependencies
   ```bash
   pip install safety
   safety check
   ```

3. **Pre-commit Hooks** - Local Prevention
   ```bash
   make pre-commit
   ```

---

## 📦 Version & Release Workflow

### Vorbereitung
```bash
# Änderungen in CHANGELOG.md dokumentieren
vim CHANGELOG.md

# Alle Commits pushen
git push origin develop
```

### Release erstellen
```bash
# Tag erstellen (semantic versioning)
git tag -a v1.0.0 -m "Release version 1.0.0"

# Tag pushen → GitHub Actions Release Workflow startet
git push origin v1.0.0
```

### Nach Release
- GitHub Release wird automatisch auf GitHub erstellt
- Docker Images werden gebaut mit Version Tag
- Coverage Report wird aktualisiert

---

## 🐳 Docker Integration

### Lokal bauen
```bash
make docker-build
```

### In CI/CD
- Wird automatisch gebaut nach erfolgreichem Lint/Test
- Funktioniert nur auf `main` und `develop` Branches

---

## 📈 Monitoring & Status

### GitHub Actions Dashboard
```
https://github.com/YOUR_USERNAME/CampusNow/actions
```

### Status Badge im README
```markdown
![CI Pipeline](https://github.com/YOUR_USERNAME/CampusNow/workflows/CI%20Pipeline/badge.svg)
![Code Quality](https://github.com/YOUR_USERNAME/CampusNow/workflows/Code%20Quality%20Analysis/badge.svg)
```

---

## 🛠️ Fehlerbehebung

### Lint-Fehler lokal beheben
```bash
# Auto-formatieren
make format

# Dann wieder checken
make lint
```

### Tests lokal debuggen
```bash
# Mit verbose Output
pytest -v -s

# Specific Test
pytest scraper-service/test_scraper.py::test_name -v
```

### Docker Issues
```bash
# Logs anschauen
docker logs campusnow-mongo
docker logs campusnow-scraper
docker logs campusnow-api
```

---

## 📚 Weitere Ressourcen

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Pre-commit Framework](https://pre-commit.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Codecov Integration](https://codecov.io/github)

---

## ✅ Checkliste für neues Repository

- [ ] Repository auf GitHub erstellen
- [ ] GitHub Actions Secrets einrichten (falls nötig: CODECOV_TOKEN)
- [ ] Branch Protection Rules für `main` einrichten
- [ ] Codecov integrieren
- [ ] README mit Status Badges aktualisieren
- [ ] Pre-commit lokal mit `make pre-commit` einrichten
