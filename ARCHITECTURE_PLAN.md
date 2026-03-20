# CampusNow - Microservice Architektur Plan

## 📋 Übersicht

**Projekt**: Intelligenter Stundenplan für HS Aalen (100-200 Räume, 60 Studiengänge)  
**Tech Stack**: Python (FastAPI) + MongoDB + Flutter  
**Deployment**: Docker Compose  
**Update-Intervall**: Täglich morgens (z.B. 6:00 Uhr)  

---

## 🏗️ Architektur-Komponenten

### 1. **Scraper Service** (Python)
- **Funktion**: Sammelt iCal-Links dynamisch, parsed Vorlesungen, lädt 360°-Bilder herunter
- **Scheduler**: APScheduler (täglich 6:00 Uhr)
- **Input**: Starplan HS Aalen Website scrapen für alle Räume/Studiengänge
- **Output**: Insertet/Updated MongoDB + speichert Bilder

### 2. **API Service** (Python FastAPI)
- **Funktion**: REST API für Flutter App mit Swagger-Dokumentation
- **Port**: 8000
- **Dokumentation**: Auto-generated Swagger UI auf `/docs`

### 3. **MongoDB Service**
- **Port**: 27017
- **Volume**: Persistent `/data/db`
- **Indizes**: Auf Raum, Studiengang, Zeit-Intervalle für schnelle Abfragen

### 4. **Image Storage** (Dateisystem)
- **Path**: `/data/images/360/`
- **Struktur**: `/data/images/360/{room_id}/{timestamp}.jpg`
- **Format**: JPEG für 360°-Bilder (Street-View optimiert)

---

## 💾 MongoDB-Schema

### Collections:

#### 1. **lectures** (Vorlesungen)
```json
{
  "_id": ObjectId,
  "lecture_id": "unique_string",
  "room_id": "ObjectId",
  "studiengang_id": "ObjectId",
  "professor": "Name",
  "module_name": "Modulname",
  "start_time": ISODate,
  "end_time": ISODate,
  "day_of_week": "Monday",
  "duration_minutes": 90,
  "room_floor": 1,
  "ical_url": "https://...",
  "last_updated": ISODate,
  "created_at": ISODate,
  "semester": "WS2025"
}
```

#### 2. **rooms** (Räume)
```json
{
  "_id": ObjectId,
  "room_number": "H1.12",
  "floor": 1,
  "capacity": 150,
  "building": "Hörsaalgebäude",
  "room_image_360": {
    "image_paths": ["2025-03-20-120000.jpg"],
    "latest_update": ISODate,
    "url_prefix": "/api/images/rooms/{room_id}/"
  },
  "has_video": true,
  "has_projector": true,
  "coordinates": { "lat": 48.12, "lng": 9.98 },
  "street_view_enabled": true,
  "ical_links": ["https://..."],
  "created_at": ISODate
}
```

#### 3. **studiengänge** (Studiengänge)
```json
{
  "_id": ObjectId,
  "name": "Informatik (B.Sc.)",
  "code": "BAINF",
  "semester": "1-6",
  "ical_url": "https://stundenplan.hs-aalen.de/ical/...",
  "lecture_count": 125,
  "last_scraped": ISODate,
  "created_at": ISODate
}
```

#### 4. **image_metadata** (Bilder-Verwaltung)
```json
{
  "_id": ObjectId,
  "room_id": "ObjectId",
  "image_filename": "2025-03-20-120000.jpg",
  "image_path": "/data/images/360/room_123/2025-03-20-120000.jpg",
  "file_size_mb": 2.5,
  "image_type": "360_panoramic",
  "uploaded_at": ISODate,
  "image_url_api": "/api/v1/images/rooms/room_123/2025-03-20-120000.jpg"
}
```

---

## 🔌 REST API Endpoints (Swagger dokumentiert)

### Base URL: `http://localhost:8000/api/v1`

#### Lectures (Vorlesungen)
```
GET    /lectures                    # Alle Vorlesungen
GET    /lectures?room_id=xxx        # Nach Raum filtern
GET    /lectures?studiengang=xxx    # Nach Studiengang filtern
GET    /lectures?date_from=2025-03-20&date_to=2025-03-27
GET    /lectures/{lecture_id}       # Details einer Vorlesung
```

#### Rooms (Räume)
```
GET    /rooms                       # Alle Räume
GET    /rooms/{room_id}             # Details eines Raums
GET    /rooms/{room_id}/schedule    # Stundenplan für Raum
GET    /rooms?filter=floor:1        # Nach Floor filtern
GET    /rooms?search=H1             # Suche nach Raumnummer
```

#### Studiengänge
```
GET    /studiengaenge              # Alle Studienänge
GET    /studiengaenge/{id}         # Details Studiengang
GET    /studiengaenge/{id}/lectures # Vorlesungen eines Studiengangs
```

#### Images (360° Bilder für Street-View)
```
GET    /images/rooms/{room_id}           # Liste aller Bilder eines Raums
GET    /images/rooms/{room_id}/latest    # Letztes Bild eines Raums
GET    /images/rooms/{room_id}/{filename}  # Spezifisches Bild herunterladen
POST   /images/rooms/{room_id}/upload    # Neues Bild hochladen (Admin)
DELETE /images/rooms/{room_id}/{filename} # Bild löschen (Admin)
```

#### Scheduler-Info
```
GET    /scheduler/status           # Scraper-Status & nächster Run
GET    /scheduler/logs             # Scraper-Logs
POST   /scheduler/trigger          # Manueller Scraper-Trigger (Admin)
```

---

## 📦 Projektstruktur

```
campusnow/
│
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE_PLAN.md
│
├── scraper-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── starplan_scraper.py    # Sammelt iCal-Links dynamisch
│   │   ├── ical_parser.py         # Parsed Vorlesungen aus iCal
│   │   └── image_downloader.py    # Downloaded 360°-Bilder
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── mongo_client.py        # MongoDB Connection
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── tasks.py               # APScheduler Tasks
│   │
│   └── config.py
│
├── api-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── lectures.py
│   │   │   ├── rooms.py
│   │   │   ├── studiengaenge.py
│   │   │   ├── images.py
│   │   │   └── scheduler.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── lecture.py
│   │   │   ├── room.py
│   │   │   ├── studiengang.py
│   │   │   └── image.py
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── mongo_client.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── lecture_service.py
│   │   │   ├── room_service.py
│   │   │   └── image_service.py
│   │   │
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth.py
│   │
│   └── tests/
│       └── test_api.py
│
├── data/
│   ├── images/
│   │   └── 360/
│   │       └── {room_id}/
│   │           └── *.jpg
│   │
│   └── db/
│       └── (MongoDB Volume)
│
└── scripts/
    ├── init_db.py          # Initialform für MongoDB
    └── seed_data.py        # Test-Daten laden
```

---

## 🐳 Docker-Setup (docker-compose.yml)

```yaml
version: '3.8'

services:
  # MongoDB Datenbank
  mongodb:
    image: mongo:7.0
    container_name: campusnow-mongo
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: securepassword
      MONGO_INITDB_DATABASE: campusnow
    volumes:
      - ./data/db:/data/db
      - ./scripts/init_db.js:/docker-entrypoint-initdb.d/init.js
    networks:
      - campusnow-net
    healthcheck:
      test: echo 'db.adminCommand("ping")' | mongosh -u admin -p securepassword
      interval: 10s
      timeout: 5s
      retries: 3

  # Scraper Service
  scraper:
    build:
      context: ./scraper-service
      dockerfile: Dockerfile
    container_name: campusnow-scraper
    environment:
      MONGO_URI: mongodb://admin:securepassword@mongodb:27017/campusnow
      LOG_LEVEL: INFO
      TZ: Europe/Berlin
    depends_on:
      mongodb:
        condition: service_healthy
    volumes:
      - ./data/images/360:/app/data/images/360
      - ./scraper-service:/app
    networks:
      - campusnow-net
    restart: unless-stopped

  # REST API Service
  api:
    build:
      context: ./api-service
      dockerfile: Dockerfile
    container_name: campusnow-api
    ports:
      - "8000:8000"
    environment:
      MONGO_URI: mongodb://admin:securepassword@mongodb:27017/campusnow
      API_TITLE: "CampusNow API"
      API_VERSION: "1.0.0"
      CORS_ORIGINS: "http://localhost:3000,http://localhost:3001"
    depends_on:
      mongodb:
        condition: service_healthy
    volumes:
      - ./data/images/360:/app/data/images/360
      - ./api-service:/app
    networks:
      - campusnow-net
    restart: unless-stopped

networks:
  campusnow-net:
    driver: bridge

volumes:
  mongo_data:
    driver: local
```

---

## 🚀 Start-Kommandos

```bash
# 1. Umgebung vorbereiten
cp .env.example .env

# 2. Services starten
docker-compose up -d

# 3. Logs anschauen
docker-compose logs -f api
docker-compose logs -f scraper
docker-compose logs -f mongodb

# 4. API Swagger UI öffnen
# http://localhost:8000/docs

# 5. Services stoppen
docker-compose down
```

---

## 📸 360° Bilder - Storage-Strategie für Street-View

### Dateistruktur:
```
/data/images/360/
├── room_507c9f646e0000000000a1/
│   ├── 2025-03-20-060000.jpg    # Morgens (für Street-View)
│   ├── 2025-03-20-120000.jpg    # Mittags
│   ├── 2025-03-20-160000.jpg    # Nachmittags
│   └── metadata.json
│
├── room_507c9f646e0000000000a2/
│   ├── 2025-03-20-060000.jpg
│   └── metadata.json
```

### Optimierungen für Street-View-App (Flutter):
1. **Thumbnails generieren**: 320x240px Vorschaubilder für schnelleres Laden
2. **Responsive Sizes**: Original (Full HD), Medium (HD), Thumbnail (SD)
3. **Lazy Loading**: Bilder nur bei Bedarf laden
4. **Caching**: Flutter Image-Cache nutzen
5. **WebP-Konvertierung** (optional später): Für kleinere Dateigröße

### API-Response für Bilder:
```json
{
  "room_id": "507c9f646e0000000000a1",
  "images": [
    {
      "id": "2025-03-20-060000",
      "filename": "2025-03-20-060000.jpg",
      "uploaded_at": "2025-03-20T06:00:00Z",
      "urls": {
        "original": "/api/v1/images/rooms/507c9f646e0000000000a1/2025-03-20-060000.jpg?size=original",
        "medium": "/api/v1/images/rooms/507c9f646e0000000000a1/2025-03-20-060000.jpg?size=medium",
        "thumbnail": "/api/v1/images/rooms/507c9f646e0000000000a1/2025-03-20-060000.jpg?size=thumbnail"
      },
      "file_size_bytes": 2500000,
      "image_type": "360_panoramic"
    }
  ]
}
```

---

## ✅ Nächste Schritte

1. **Projektstruktur** erstellen
2. **MongoDB-Schema** initialisieren
3. **Scraper-Service** entwickeln (Starplan-Links sammeln + Parsing)
4. **API-Service** entwickeln (FastAPI + Swagger)
5. **Docker-Compose** konfigurieren
6. **Flutter-App** integrieren
7. **Tests** schreiben
8. **Deployment** vorbereiten

---

## 📊 Performance-Erwartungen

| Metrik | Wert |
|--------|------|
| Rooms | 100-200 |
| Studiengänge | 60 |
| Durchschn. Vorlesungen/Tag | ~5000 |
| API-Response-Zeit | <100ms |
| Scraper-Laufzeit | ~30-60 Min (täglich morgens) |
| Image Storage/Raum | ~25-30 MB/Tag (3 Bilder à 8-10 MB) |
| Gesamtspeicher/Monat | ~80-100 GB (ohne Archivierung) |

---

**Erstellt**: 2025-03-20  
**Status**: Ready for Implementation
