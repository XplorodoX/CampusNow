# GitHub Actions Optimization & Skip Guide

## 🚀 Optimierte Workflow Triggers

Diese Dokumentation zeigt, wie die GitHub Actions Workflows optimiert wurden, um sinnlos Ressourcen zu verschwenden.

---

## 📊 Workflow Übersicht

### 1️⃣ CI Pipeline (`ci.yml`)

**Läuft nur wenn:**
- ✅ Code-Änderungen gepusht (zu main/develop)
- ✅ Pull Request zu main/develop erstellt
- ✅ Manuell via `workflow_dispatch`

**Ignoriert (skipped automatisch):**
- ❌ Reine Markdown-Änderungen (`*.md`)
- ❌ `.editorconfig`, `.gitignore`, `LICENSE`
- ❌ `docs/` Verzeichnis

```yaml
on:
  push:
    branches: [main, develop]
    paths-ignore:
      - '**.md'
      - '.editorconfig'
      - '.gitignore'
      - 'LICENSE'
      - 'docs/**'
```

**Warum?** Typos in README oder `.gitignore` Changes brauchen keine Python Tests! 💰

---

### 2️⃣ Code Quality Analysis (`code-quality.yml`)

**Läuft nur wenn:**
- ✅ CI Pipeline erfolgreich war
- ✅ Auf main oder develop
- ✅ Manuell via `workflow_dispatch`

```yaml
on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main, develop]
  workflow_dispatch:
```

**Was war vorher:** Täglich um 2 AM UTC (unnötig! ⚠️)

**Warum die Änderung?** Tägliche Runs verschwenden Azure Credits. Besser: Nach jedem erfolgreichen CI! ✅

---

### 3️⃣ Dependency Audit (`dependencies.yml`)

**Läuft nur wenn:**
- ✅ Montag 2 AM UTC (wöchentlich)
- ✅ Nach Release erfolgreich
- ✅ Manuell via `workflow_dispatch`

```yaml
on:
  schedule:
    - cron: '0 2 * * MON'  # Monday 2 AM UTC
  workflow_run:
    workflows: ["Release & Deployment"]
    types: [completed]
  workflow_dispatch:
```

**Warum?** Dependency Checks täglich nötig? Nein! Wöchentlich reicht + nach Release. 🛡️

### 4️⃣️ Tag Validation (`tag-validation.yml`)

**Läuft nur wenn:**
- ✅ Neuer Tag gepusht wird
- ✅ Tag matcht Pattern: `v*`
- ✅ Manuell via `workflow_dispatch`

```yaml
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
```

**Feature:** Validiert Semantic Versioning Format
- ✅ Akzeptiert: `v1.0.0`, `v1.0.0-rc1`
- ❌ Lehnt ab: `v1.0.0.0`, `release-1.0`, `latest`

---

### 5️⃣ Release & Deployment (`release.yml`)

**Läuft nur wenn:**
- ✅ Gültiger Version-Tag gepusht (`v1.0.0`)
- ✅ Manuell via `workflow_dispatch`

```yaml
on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'        # v1.0.0
      - 'v[0-9]+.[0-9]+.[0-9]+-rc*'    # v1.0.0-rc1
  workflow_dispatch:
```

**Features:**
1. Validiert Tag Format (regex)
2. Runs Tests nur wenn Tag valid
3. Erstellt Release nur wenn Tests pass
4. Baut Docker Images mit version tag
5. Markiert RC automatisch als "Pre-release"

---

## 🎯 Skip-Szenarien

### Scenario 1: Nur Dokumentation geändert

```bash
# User edited nur README.md
git add README.md
git commit -m "docs: update README"
git push origin main
```

**Result:** ✅ CI Pipeline **SKIPPED** (sparte 2-3 min, 💰 credits)

### Scenario 2: EditorConfig angepasst

```bash
# User changed nur .editorconfig
git add .editorconfig
git commit -m "chore: update editor config"
git push origin develop
```

**Result:** ✅ CI Pipeline **SKIPPED** (Python Tests nicht nötig!)

### Scenario 3: Release durchführen

```bash
# Nach Tests: Tag erstellen
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

**Result:**
1. ✅ Tag Validation startet
2. ✅ Bei Valid: Release & Deployment startet
3. ✅ Tests, Linting, Docker Images
4. ❌ Code Quality nicht (weil kein Code Push)

---

## 💾 Geschätzte Kredit-Ersparnisse

**Pro Woche:**

| Scenario | Normal | Optimiert | Ersparnis |
|----------|--------|-----------|-----------|
| 5x Docs-only Changes | 5 x 3 min | 0 min | 15 min |
| 2x Dependency Checks | 2 x 3 min | 0 min | 6 min  |
| 1x Daily Quality | 1 x 5 min | 0 min | 5 min  |
| **Total** | **28 min** | **9 min** | **19 min** |

**Pro Jahr:** ~16 Stunden GitHub Actions sparen! 💰

---

## ✅ Best Practices zum Sparen

### 1. Docs-only: Nutze [skip ci]

```bash
git commit -m "docs: update guide [skip ci]"
```

**Hinweis:** Unsere Konfiguration macht das automatisch via `paths-ignore`! 

### 2. Releases: Nutze Tags sinnvoll

```bash
# ❌ NICHT: Pro Tag testen
git tag -a v0.0.1
git tag -a v0.0.2
git tag -a v0.0.3
git push --all origin  # Mehrere Runs!

# ✅ JA: Ein Test, mehrere Releases
git tag v1.0.0
git push origin v1.0.0  # Ein Run
```

### 3. Parallelisierung nutzen

```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11']
```

**Result:** 3 Python Versionen getestet in ~parallel Zeit! ✅

### 4. Smart Caching

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

**Result:** Erste Run: 2 min, Zweite Run: 30 Sekunden ⚡

---

## 🔧 Workflow Kommandie

### CI lokal testen (vor Push)

```bash
make ci-local
```

Diese simuliert EXAKT die GitHub Actions CI Pipeline lokal!

### Release vorbereiten

```bash
# Prüfe ob alles ready ist
make release-check

# Erstelle Release
make release VERSION=1.0.0
```

### Dependency Audit manuell triggern

Gehe zu: GitHub → Actions → "Dependency & Security Audit" → "Run workflow"

---

## 📋 Workflow Konfiguration Review

### Achte auf diese Konzepte:

```yaml
# 1. Nur relevante Branch triggern
on:
  push:
    branches: [main, develop]  ← Nicht alle branches

# 2. Path Filter nutzen
    paths-ignore:
      - '**.md'               ← Skip Docs

# 3. Workflow Dependencies
jobs:
  job2:
    needs: job1              ← Nur wenn job1 success

# 4. Conditionals
    if: matrix.python-version == '3.11'  ← Selektives Run
```

---

## 🚨 Monitoring

### GitHub Actions Dashboard

```
https://github.com/YOUR_REPO/actions
```

**Schau auf:**
- 🟢 Erfolgreich
- 🔴 Fehlgeschlagen
- ⏭️ Skipped
- ⏱️ Laufzeit

**Ziel:** Meiste "Skipped", fewest unnötige Runs ✅

---

## 🎓 Zusammenfassung

| Optimierung | Effekt | Ersparnis |
|------------|--------|-----------|
| Path Filters | Docs skipped | ~15 min/Woche |
| Schedule reduziert | Weniger Daily | ~5 min/Woche |
| Tag Validation | Fehler früh erkannt | Kein Wasted Run |
| Caching | Schnellere Installs | 60% Zeit |
| Matrix Parallelization | Multi-Python | 3x Speed-up |

**Resultat:** ⚡ Schneller, 💰 Billiger, 🎯 Zuverlässiger

---

## 📚 Weitere Ressourcen

- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Actions Pricing](https://github.com/pricing)
- [Workflow Best Practices](https://docs.github.com/en/actions/guides)

---

**Optimierte Workflows sind glückliche Wallets! 💚**
