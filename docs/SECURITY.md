# Security Policy

## 🔒 Reporting Security Issues

**Bitte melden Sie Sicherheitsprobleme NICHT über den öffentlichen Issue Tracker.**

### Sicherheitslücke melden
1. Mailen Sie an: **security@campusnow.local** (oder maintainer@github)
2. Betreffzeile: `[SECURITY] Brief description`
3. Beschreiben Sie:
   - Art der Sicherheitslücke
   - Betroffene Komponente(n)
   - Schritte zum Reproduzieren
   - Mögliche Auswirkungen
   - Vorgeschlagene Lösung (optional)

### Response Time
- Initial Response: 24 Stunden
- Security Fix Release: So schnell wie möglich
- Public Disclosure: Nach Fix veröffentlicht

---

## 🛡️ Security Measures

### In der CI/CD Pipeline

#### 1. **Security Scanning**
- 🔍 **Bandit** - Python Security Issues
  ```bash
  bandit -r scraper-service api-service
  ```

- 🔐 **Safety** - Known Vulnerabilities
  ```bash
  safety check
  ```

- 📋 **pip-audit** - Dependency Vulnerabilities
  ```bash
  pip-audit
  ```

#### 2. **Dependency Management**
- GitHub Dependabot für automatische Updates
- Weekly dependency scanning
- Coverage für vulnerable packages

#### 3. **Code Quality**
- Type hints für bessere Fehlerprävention
- 80%+ Code Coverage
- Static Analysis mit Pylint/Ruff

### Best Practices

#### Authentication & Secrets
```python
# ❌ NICHT
DB_PASSWORD = "secret123"
API_KEY = "sk_live_..."

# ✅ JA
import os
DB_PASSWORD = os.getenv("DB_PASSWORD")
API_KEY = os.getenv("API_KEY")
```

#### Secrets Management
- Nutze `.env` (in .gitignore)
- GitHub Secrets für CI/CD
- Environment-spezifische Configs
- Keine Secrets in Logs

#### Database Security
```python
# Connection mit Authentifizierung
mongodb://user:password@host:27017/db
# Mit Verschlüsselung
mongodb+srv://user:password@cluster.mongodb.net/db
```

#### API Security
- Input Validation
- Rate Limiting
- CORS Policy
- HTTPS Only (Production)
- SQL Injection Prevention

#### Error Handling
```python
# ❌ NICHT - Sensitive Info exposed
try:
    query()
except Exception as e:
    logger.error(f"Query failed: {e}")  # Stack trace!

# ✅ JA - Generic message
except Exception as e:
    logger.error("Database query failed", exc_info=True)
    raise ValueError("Unable to process request")
```

---

## 🔐 Supported Versions

| Version | Status | Support Ends |
|---------|--------|-------------|
| 1.x     | ✅ Active | TBD |
| 0.x     | ❌ End of Life | 2024-01-01 |

---

## 🐍 Python Version Support

- ✅ Python 3.9+
- ✅ Python 3.10+
- ✅ Python 3.11+
- ✅ Python 3.12+

Sicherheits-Updates für veraltete Python-Versionen werden nicht gewährt.

---

## 🚨 Security Incident Response

### Kritische Sicherheitslücke gefunden?

1. **Sofortmaßnahmen**
   - Code lokalisieren
   - Workaround mit Issue dokumentieren
   - Betroffene User benachrichtigen

2. **Patch Development**
   - Feature Branch erstellen
   - Patch implementieren
   - Vollständigkeits-Tests
   - Security Review

3. **Release**
   - Version bump (Security Release)
   - CHANGELOG.md aktualisieren
   - Release Notes mit Details
   - Alte Versionen deprecaten

4. **Post-Incident**
   - Security Audit durchführen
   - Code Review Prozess verbessern
   - Monitoring erweitern

---

## 📋 Security Checklist

Vor jedem Production Release:

- [ ] Alle Dependencies aktuell und sicher
- [ ] Bandit Scan: 0 Issues
- [ ] Safety Check: 0 Vulnerabilities
- [ ] Code Review completed
- [ ] Security Tests bestanden
- [ ] OWASP Top 10 geprüft
- [ ] Logging zeigt keine Secrets
- [ ] Rate Limiting konfiguriert
- [ ] CORS Policy gesetzt
- [ ] Documentation aktualisiert

---

## 🔗 Externe Ressourcen

- [OWASP Top 10](https://owasp.org/www-project-top-10/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Python Security](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [MongoDB Security](https://docs.mongodb.com/manual/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## 📞 Contact

**Security Team:** security@campusnow.local

**Danke für deine Geduld und Diskretion bei der Meldung von Sicherheitslücken!** 🙏
