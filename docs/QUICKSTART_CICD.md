# Quick Start Guide - CI/CD

## 🚀 In 5 Minuten einsatzbereit

### 1️⃣ Erste Schritte (einmalig)

```bash
cd /home/flo/CampusNow

# Setup
make install-dev

# Pre-commit Hooks installieren
make pre-commit
```

### 2️⃣ Vor jedem Commit

```bash
# Code formatieren (auto-fixes)
make format

# Prüfen ob alles OK ist
make lint
make test
```

### 3️⃣ Vollständiger Check (vor Push)

```bash
# Alles lokal testen wie in CI
make ci-local
```

---

## 📋 Häufige Befehle

| Befehl | Beschreibung | Wann |
|--------|-------------|------|
| `make install-dev` | Development Dependencies installieren | Einmalig nach Clone |
| `make format` | Code auto-formatieren | Vor jedem Commit |
| `make lint` | Linting prüfen | Vor jedem Commit |
| `make test` | Unit Tests ausführen | Vor jedem Commit |
| `make test-cov` | Tests mit Coverage Report | Nach Feature Implementation |
| `make security` | Security Scan | Vor jedem Release |
| `make quality` | Alle Quality Checks | Vor jedem Push |
| `make ci-local` | Komplette CI Pipeline lokal | Vor Pull Request |
| `make docker-up` | Services starten | Für lokale Entwicklung |
| `make docker-down` | Services stoppen | Nach Tests |
| `make clean` | Cache/Build-Files löschen | Bei Problemen |

---

## 🔄 Git Workflow

### Feature entwickeln
```bash
# Branch erstellen
git checkout -b feature/my-feature

# Entwickeln, testen
make format
make lint
make test

# Committen
git add .
git commit -m "feat(scraper): add new feature"

# Vor Push aktualisieren
git fetch origin
git rebase origin/develop

# Pushen
git push origin feature/my-feature
```

### Pull Request erstellen
1. Gehe zu GitHub
2. Erstelle PR gegen `develop` Branch
3. Auf CI Pipeline warten (siehe Green Checkmarks)
4. Code Review erhalten
5. Merge nach Approval

---

## 🎯 Qualitätsziele

```
Ziel              | Target  | Check
-----------------|---------|------------------
Code Coverage     | ≥ 80%   | make test-cov
Lint Issues       | 0       | make lint
Security Issues   | 0       | make security
Tests             | ✅ Pass | make test
Format            | ✅ OK   | make format-check
```

---

## ✅ Checkliste für Pull Request

Bevor dein Code reviewt wird:

- [ ] `make format` - Code formatieren
- [ ] `make lint` - Keine Linting Fehler
- [ ] `make test` - Alle Tests grün
- [ ] `make test-cov` - Coverage ≥ 80%
- [ ] `make security` - Keine Security Issues
- [ ] `make ci-local` - Vollständige Pipeline erfolgreich
- [ ] CHANGELOG.md aktualisiert
- [ ] Docs/Comments aktualisiert
- [ ] Aussagekräftige Commit Messages
- [ ] Kein Force Push zu shared Branches

---

## 🐛 Fehlerbehandlung

### Lint Fehler
```bash
# Auto-fix mit Ruff
ruff check scraper-service api-service --fix

# Auto-fix mit Black
black scraper-service api-service

# Dann wieder checken
make lint
```

### Test Fehler
```bash
# Verbose output
pytest -v -s

# Spezifischen Test debuggen
pytest scraper-service/test_scraper.py::test_name -v

# Mit Debugger
pytest --pdb scraper-service/test_scraper.py
```

### Import Fehler
```bash
# Dependencies aktualisieren
make install-dev

# Python Cache löschen
make clean

# Venv neustarten
source venv/bin/activate
```

---

## 📚 Weitere Dokumentation

- 📖 [CI/CD Setup Vollständig](CI_CD_SETUP.md)
- 🧪 [Testing Guide](TESTING.md)
- 🤝 [Contributing Guide](CONTRIBUTING.md)
- 🔒 [Security Policy](SECURITY.md)
- 🏗️ [Architecture](ARCHITECTURE_PLAN.md)

---

## 💡 Pro Tips

1. **Alias erstellen für häufige Befehle**
   ```bash
   alias cdnow="cd /home/flo/CampusNow"
   alias cilocal="make ci-local"
   ```

2. **VSCode Integration**
   - Python Extension installieren
   - Linting aktivieren
   - Tests in VSCode runnen mit Test Explorer

3. **Pre-commit in IDE aktivieren**
   - VSCode: Husky Extension
   - PyCharm: Built-in Git Hooks Support
   - Vim: Use pre-commit CLI

4. **Watch Mode**
   ```bash
   # Nur geänderte Tests
   pytest --lf -v
   
   # Auto-run bei Datei-Änderungen
   ptw  # (benötigt pytest-watch)
   ```

---

## 🆘 Support

Probleme? Schau hier:

1. **Makefile Help**
   ```bash
   make help
   ```

2. **GitHub Actions Logs**
   - GitHub → Actions → [Failed Workflow]
   - Logs expandieren → Debug Info

3. **Issue erstellen**
   - Beschreibung + Fehler Message
   - Output von `make ci-local`
   - Python Version

---

**Glückwunsch! Du kannst jetzt mit CI/CD arbeiten! 🎉**

> *Fang klein an, teste oft, committen regelmäßig.*
