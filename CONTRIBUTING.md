# Contributing Guide

Danke, dass du zu CampusNow beitragen möchtest! 🎉

Diese Richtlinien helfen uns, eine hohe Codequalität und einen guten Zusammenhalt in der Community zu bewahren.

## 📋 Inhaltsverzeichnis

1. [Code of Conduct](#code-of-conduct)
2. [Wie man beiträgt](#wie-man-beiträgt)
3. [Development Setup](#development-setup)
4. [Commit Standards](#commit-standards)
5. [Pull Request Prozess](#pull-request-prozess)
6. [Code Style Guide](#code-style-guide)

---

## Code of Conduct

- Respekt vor allen Beitragenden
- Konstruktives Feedback geben und annehmen
- Fokus auf das Projekt und nicht auf die Person
- Jeder verdient einen respektvollen Umgang

---

## Wie man beiträgt

### Bug Reports
1. Prüfe, ob der Bug bereits gemeldet wurde
2. Erstelle ein Issue mit:
   - Klarer Beschreibung des Problems
   - Schritte zum Reproduzieren
   - Erwartetes vs. aktuelles Verhalten
   - Python-Version, OS, etc.

### Feature Requests
1. Beschreibe den Anwendungsfall
2. Erkläre, warum dies nötig ist
3. Gib mögliche Implementierungsideen

### Code Changes
1. Fork das Repository
2. Erstelle einen Feature Branch: `git checkout -b feature/my-feature`
3. Committen mit aussagekräftigen Messages
4. Push zu deinem Fork
5. Erstelle einen Pull Request

---

## Development Setup

### 1. Environment vorbereiten
```bash
# Repository klonen
git clone https://github.com/YOUR_USERNAME/CampusNow.git
cd CampusNow

# Virtual Environment erstellen (Optional)
python -m venv venv
source venv/bin/activate  # Unix/macOS
# oder
venv\Scripts\activate  # Windows

# Dependencies installieren
make install-dev
```

### 2. Pre-commit Hooks einrichten
```bash
make pre-commit
```

Das installiert automatische Checks vor jedem Commit:
- Ruff Linting
- Black Code Formatting
- Whitespace Fixes

### 3. Local Tests ausführen
```bash
# Alle Checks lokal
make ci-local

# Oder einzeln:
make lint           # Linting
make format-check   # Format validation
make test           # Unit Tests
make security       # Security Scan
```

---

## Commit Standards

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: Neue Funktion
- **fix**: Bug Fix
- **refactor**: Code Umstrukturierung
- **perf**: Performance Verbesserung
- **test**: Tests hinzufügen/aktualisieren
- **docs**: Dokumentation
- **style**: Code Style (Linting, Formatierung)
- **chore**: Dependencies, Build, etc.
- **ci**: CI/CD Konfiguration

### Beispiele
```
feat(scraper): add HS Aalen integration

- Implement JSON endpoint discovery
- Add iCal URL validation
- Add lecture data parsing

Closes #123
```

```
fix(api): resolve MongoDB connection timeout

- Increase connection timeout to 30s
- Add retry logic with exponential backoff

Fixes #456
```

### Regeln
- ✅ Aussagekräftige Messages
- ✅ Imperative Formen ("add", nicht "added")
- ✅ Kleine, fokussierte Commits
- ❌ Keine WIP Commits in main/develop
- ❌ Keine Merge Commits (rebase stattdessen)

---

## Pull Request Prozess

### Vor dem PR
1. **Branch aktualisieren**
   ```bash
   git fetch origin
   git rebase origin/develop
   ```

2. **Alle Tests lokal bestehen**
   ```bash
   make ci-local
   ```

3. **Code Review selbst machen**
   - Logische Struktur?
   - Fehlerbehandlung?
   - Tests vorhanden?
   - Dokumentation vollständig?

### PR Checklist
- [ ] Tests schreiben/aktualisieren
- [ ] Dokumentation aktualisiert
- [ ] CHANGELOG.md updated
- [ ] Keine Breaking Changes ohne Diskussion
- [ ] Code folgt Style Guides
- [ ] Alle Lint Checks bestehen
- [ ] Coverage nicht reduziert

### PR Beschreibung Template
```markdown
## 📝 Beschreibung
Kurze Zusammenfassung der Änderungen

## 🎯 Motivation und Kontext
Warum sind diese Änderungen nötig?

## 🔄 Wie wurde getestet?
Beschreibe die Tests, die du durchgeführt hast

## 📚 Checkliste
- [ ] Meine Änderungen folgen den Code Style
- [ ] Ich habe meine Änderungen lokal getestet
- [ ] Ich habe neue Tests für neue Features geschrieben
- [ ] Ich habe die Dokumentation aktualisiert
- [ ] Keine neuen Warnungen in Lint/Tests

## 📸 Screenshots (optional)
Falls UI-Änderungen
```

### Nach Review
- Auf Feedback antworten
- Änderungen committen (keine Force Push!)
- Rebase wenn nötig: `git rebase origin/develop`
- Approval abwarten

---

## Code Style Guide

### Python Style
- **PEP 8** mit Line-Length: 100
- **Black** für Formatierung
- **Ruff** für Linting

### Naming Conventions
```python
# Functions & Variables - snake_case
def get_user_data():
    local_variable = True

# Classes - PascalCase
class UserService:
    pass

# Constants - UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private - Leading underscore
def _internal_method():
    pass
```

### Docstrings
```python
def scrape_ical_links(self, base_url: str) -> List[str]:
    """
    Scrape iCal links from HS Aalen StarPlan.
    
    Args:
        base_url: The base URL of the StarPlan system
        
    Returns:
        List of iCal URLs for rooms and courses
        
    Raises:
        ValueError: If base_url is invalid
        ConnectionError: If unable to connect to StarPlan
    """
```

### Type Hints
```python
from typing import Optional, List, Dict

def process_data(
    items: List[str],
    timeout: int = 30,
    force: bool = False
) -> Dict[str, any]:
    """Process items with type hints."""
    pass
```

### Error Handling
```python
try:
    result = some_operation()
except SpecificError as e:
    logger.error(f"Failed to process: {e}")
    raise
except Exception as e:
    logger.warning(f"Unexpected error: {e}")
    return None
```

---

## 📊 Qualitätsmetriken

Diese Projekt nutzt folgende Tools:

- **Ruff** - Fast Python Linter
- **Flake8** - Code Quality
- **Black** - Code Formatter
- **Pytest** - Unit Tests
- **Coverage** - Code Coverage Tracking
- **Bandit** - Security Scanning

**Ziele:**
- ✅ 0 Lint Errors
- ✅ ≥ 80% Code Coverage
- ✅ 0 Critical Security Issues
- ✅ Alle Tests grün

---

## Fragen?

- 📖 Siehe [CI_CD_SETUP.md](CI_CD_SETUP.md) für Details zur Pipeline
- 📚 Siehe [DEVELOPMENT.md](DEVELOPMENT.md) für Setup Infos
- 💬 Erstelle ein Issue für Fragen
- 🐛 Melde Bugs über Issues

---

## 🙏 Danke!

Dein Beitrag wird die Community bereichern. Danke, dass du Zeit in dieses Projekt investierst! 💪
