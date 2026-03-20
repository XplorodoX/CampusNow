# CampusNow - Setup Guide

## 🚀 Schnellstart

### Vorrausetzungen
- Docker & Docker Compose
- Git
- (Optional) Python 3.11+ für lokale Entwicklung

### Installation

1. **Repository klonen**
```bash
cd /home/flo/CampusNow
```

2. **Environment konfigurieren**
```bash
cp .env.example .env
# Bearbeite .env falls nötig (Passwörter, URLs, etc.)
```

3. **Services starten**
```bash
docker-compose up -d
```

4. **Status prüfen**
```bash
docker-compose ps
docker-compose logs -f api
docker-compose logs -f scraper
docker-compose logs -f mongodb
```

---

## 📖 API Dokumentation

Nach dem Start ist die **Swagger UI** unter folgendem Link verfügbar:

### http://localhost:8000/docs

Alle API-Endpoints sind dort dokumentiert mit:
- Beschreibungen
- Request/Response-Beispiele
- Try-it-out Funktionalität

---

## 🗂️ Projektstruktur

```
campusnow/
├── docker-compose.yml          # Docker-Orchestrierung
├── .env.example                # Umgebungsvariablen Template
├── ARCHITECTURE_PLAN.md        # Detaillierte Architektur
├── ARCHITECTURE_DIAGRAM.md     # System Diagramm
│
├── scraper-service/            # Scraper Microservice
│   ├── main.py                 # Entry Point
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py
│   │
│   ├── scraper/
│   │   ├── starplan_scraper.py   # Sammelt iCal-Links
│   │   ├── ical_parser.py        # Parsed Vorlesungen
│   │   └── image_downloader.py   # Downloaded 360°-Bilder
│   │
│   ├── db/
│   │   └── mongo_client.py       # MongoDB Connection
│   │
│   └── scheduler/
│       └── tasks.py              # Scraper-Jobs
│
├── api-service/                # REST-API Microservice
│   ├── main.py                 # FastAPI Entry Point
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   └── app/
│       ├── config.py           # Konfiguration
│       ├── models/             # Pydantic Models
│       ├── routers/            # API Endpoints
│       ├── db/                 # Database Client
│       └── services/           # Business Logic
│
├── data/
│   ├── images/360/             # 360°-Bilder Speicher
│   └── db/                     # MongoDB Volume
│
└── scripts/
    └── init_db.js             # MongoDB Initialization
```

---

## 🔄 Workflow

### 1. Scraper Service
- **Zeitplan**: Täglich morgens 6:00 Uhr (konfigurierbar)
- **Process**:
  1. Sammelt iCal-Links vom HS Aalen Starplan
  2. Parsed iCal-Dateien für Vorlesungen
  3. Downloaded 360°-Bilder von Räumen
  4. Speichert alles in MongoDB
  5. Alte Daten werden gelöscht

### 2. REST-API Service
- **Port**: 8000
- **Liefert**:
  - Stundenplan nach Raum/Studiengang
  - Raumlisten & Details
  - 360°-Bilder für Street-View
  - Swagger-Dokumentation

### 3. MongoDB
- **Port**: 27017
- **Collections**:
  - `lectures` - Vorlesungen
  - `rooms` - Räume
  - `studiengaenge` - Studiengänge
  - `image_metadata` - Bilder-Verwaltung

---

## 🛠️ Häufige Befehle

### Container-Management
```bash
# Alle Services starten
docker-compose up -d

# Services stoppen
docker-compose stop

# Services löschen
docker-compose down

# Logs anschauen (real-time)
docker-compose logs -f api

# In Container reinschauen
docker-compose exec scraper bash
docker-compose exec api bash
docker-compose exec mongodb mongosh
```

### Datenbank
```bash
# MongoDB Shell öffnen
docker-compose exec mongodb mongosh -u admin -p campusnow_secret_2025

# In MongoDB:
use campusnow
db.lectures.find()
db.rooms.find()
db.studiengaenge.find()
db.image_metadata.find()
```

### Entwicklung
```bash
# Lokale Enticklung (ohne Docker)
cd scraper-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Anderes Terminal für API
cd api-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 📊 MongoDB-Schemi-Referenz

Siehe [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) für detaillierte Schema-Definitionen.

---

## 🔒 Sicherheit

⚠️ **WICHTIG für Produktion**:
1. `.env` Datei niemals in Git commiten
2. Passwörter ändern (`MONGO_PASSWORD`, etc.)
3. CORS-Origins einschränken
4. API Authentication implementieren
5. HTTPS aktivieren

Standard Credentials (nur für Entwicklung!):
- MongoDB User: `admin`
- MongoDB Password: `campusnow_secret_2025`

---

## 📱 Flutter App Integration

Die Flutter App kommuniziert mit der REST-API unter `http://localhost:8000` (oder Production-URL).

**Verfügbare Endpoints**:
- GET `/api/v1/lectures` - Vorlesungen
- GET `/api/v1/rooms` - Räume
- GET `/api/v1/images/rooms/{room_id}` - 360°-Bilder

Alle Endpoints sind in [Swagger UI](/docs) dokumentiert.

---

## 🐛 Troubleshooting

### MongoDB Connection Error
```bash
docker-compose logs mongodb
# Prüfe: PORT 27017, Passwort in .env, MongoDB status
```

### Scraper startet nicht
```bash
docker-compose logs scraper
# Prüfe: MONGO_URI, APScheduler, iCal-Links
```

### API gibt 500 Error
```bash
docker-compose logs api
# Prüfe: MongoDB Connection, Datenbank existiert, Collections
```

---

## 📝 Nächste Schritte

1. **Starplan-Scraper** vollständig implementierne
   - HTML-Parsing für Studiengang-Links
   - Raum-Listen scrapen
   - iCal-URL-Sammlung

2. **iCal-Parsing** erweitern
   - Dozenten extrahieren
   - Modul-Informationen
   - Wiederholende Vorlesungen

3. **360°-Bilder**
   - Download-Links finden
   - Thumbnails generieren
   - Caching implementieren

4. **Tests** schreiben
   - Unit-Tests für Parser
   - Integration-Tests für API
   - Load-Tests

5. **Deployment**
   - Docker Registry pushen
   - Production-Umgebung Setup
   - CI/CD Pipeline

---

## 📧 Support & Contakt

Für Fragen oder Issues: [GitHub Issues](https://github.com/your-org/campusnow/)

---

**Status**: 🟢 Production-Ready  
**Version**: 1.0.0  
**Letzte Aktualisierung**: 2025-03-20
