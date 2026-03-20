# Release Quick Reference

## 🚀 TL;DR - Releases in 3 Schritten

### 1️⃣ CHANGELOG.md vorbereiten
```bash
# Edit CHANGELOG.md - Move "Unreleased" to "[1.1.0]"
vim CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: prepare v1.1.0 release"
git push origin develop
```

### 2️⃣ Release vorbereiten
```bash
# Lokal testen
make release-check

# Alles OK? Release erstellen:
make release VERSION=1.1.0
```

### 3️⃣ GitHub Actions kümmert sich um Rest!
- ✅ Tests ausführen
- ✅ Linting prüfen
- ✅ GitHub Release erstellen
- ✅ Docker Images bauen
- 🎉 Fertig!

---

## 📋 Regular Release (v1.0.0)
```bash
make release VERSION=1.0.0
```
- GitHub markiert als normale Release
- Tags: `campusnow:scraper-v1.0.0`, `campusnow:scraper-latest`

## 📋 Release Candidate (v1.0.0-rc1)
```bash
make release-rc VERSION=1.0.0
```
- GitHub markiert als "Pre-release"
- Tags: `campusnow:scraper-v1.0.0-rc1`

---

## 🔍 Was passiert hinter den Kulissen?

```
make release VERSION=1.0.0
  │
  ├─ 1. release-check
  │     ├─ Prüft CHANGELOG.md
  │     ├─ Runts full CI pipeline
  │     └─ Zeigt Git status
  │
  ├─ 2. Git Tag erstellen
  │     └─ git tag -a v1.0.0 -m "..."
  │
  ├─ 3. Tag zu GitHub pushen
  │     └─ git push origin v1.0.0
  │
  └─ 4. GitHub Actions startet Release Workflow
        ├─ Tag Validation (5 sec)
        ├─ Final Tests (2 min)
        ├─ Linting (1 min)
        ├─ GitHub Release (30 sec)
        └─ Docker Build (3 min)
```

---

## 🎯 Häufige Befehle

```bash
# Pre-Release Checks
make release-check

# Release erstellen
make release VERSION=1.0.0

# RC Release erstellen
make release-rc VERSION=1.0.0

# GitHub Actions Log anschauen
xdg-open https://github.com/YOUR_USERNAME/CampusNow/actions
```

---

## ❌ Was kann schief gehen?

| Problem | Lösung |
|---------|--------|
| `CHANGELOG.md not found` | Erstelle/Update CHANGELOG.md |
| `CI pipeline failed` | Führe `make ci-local` aus, fixe Fehler |
| `Tag already exists` | Delete mit: `git tag -d v1.0.0 && git push origin --delete v1.0.0` |
| `Invalid tag format` | Nutze `vX.Y.Z` Format (z.B. `v1.0.0`) |

---

## 📚 Weitere Infos

- **Vollständiger Guide:** [TAG_AND_RELEASE.md](TAG_AND_RELEASE.md)
- **Workflow Optimierungen:** [WORKFLOW_OPTIMIZATION.md](WORKFLOW_OPTIMIZATION.md)
- **CI/CD Setup:** [CI_CD_SETUP.md](CI_CD_SETUP.md)

---

**Gut zu gehen! Die Pipelines laufen automatisch. 🤖✅**
