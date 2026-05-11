# CampusNow – API-Dokumentation für Frontend-Entwickler

> **Base URL:** `http://<host>:6058`  
> **Interaktive Docs:** `http://<host>:6058/docs` (Swagger UI)  
> **Alle Endpunkte beginnen mit `/api/v1/`**

---

## Inhaltsverzeichnis

1. [Timetable](#1-timetable) ← **Hauptendpunkt für das Frontend**
2. [Settings](#2-settings)
3. [Street View Graph](#3-street-view-graph)
4. [Buildings](#4-buildings)
5. [Rooms](#5-rooms)
6. [Events](#6-events)
7. [Images (360°)](#7-images-360)
8. [Auth-Header](#auth-header)
9. [Fehler-Codes](#fehler-codes)
10. [Datenmodelle im Überblick](#datenmodelle-im-überblick)

---

## 1. Timetable

> Dieser eine Endpunkt liefert alles, was die Stundenplan-Ansicht braucht:  
> Studiengänge, Semester, Event-Gruppen, Vorlesungen und Events – in einem Call.

### `GET /api/v1/timetable`

**Ohne Filter:** gibt alles zurück (bis zu 200 Vorlesungen + 50 Events).  
**Mit Filtern:** beliebig kombinierbar.

#### Query-Parameter

| Parameter | Typ | Beispiel | Beschreibung |
|---|---|---|---|
| `course` | string | `IN` | Studiengang-Code (aus `courses_of_study[].id`). Mehrere mit Komma: `IN,ET` |
| `semester` | string | `sem_1` | Semester-ID. Mehrere: `sem_1,sem_2` |
| `event_group` | string | `sports` | Event-Gruppe. Mehrere: `sports,career` |
| `building` | string | `G2` | Exakter Gebäude-Code |
| `room` | string | `G2 1` | Partial-Match auf Raumnummer (case-insensitiv) |
| `professor` | string | `Müller` | Partial-Match auf Dozentenname |
| `date_from` | string | `2026-05-11` | Vorlesungen/Events ab diesem Datum (YYYY-MM-DD) |
| `date_to` | string | `2026-07-31` | Vorlesungen/Events bis zu diesem Datum (inkl.) |
| `recurrence` | string | `weekly` | `weekly` oder `once` |
| `public_only` | bool | `true` | Nur öffentliche Events (Gäste-Modus ohne Login) |
| `limit_lectures` | int | `200` | Max. Vorlesungen (1–1000, default 200) |
| `limit_events` | int | `50` | Max. Events (1–200, default 50) |

#### Beispiel-Request

```
GET /api/v1/timetable?course=IN&semester=sem_1&date_from=2026-05-11
```

#### Response-Struktur

```json
{
  "courses_of_study": [
    { "id": "IN",  "label": "Informatik" },
    { "id": "ET",  "label": "Elektrotechnik" },
    { "id": "ETI", "label": "Technische Informatik / Embedded Systems" }
  ],
  "semesters": [
    { "id": "sem_1", "label": "Semester 1" },
    { "id": "sem_2", "label": "Semester 2" },
    { "id": "sem_3", "label": "Semester 3" },
    { "id": "sem_4", "label": "Semester 4" },
    { "id": "sem_6", "label": "Semester 6" },
    { "id": "sem_7", "label": "Semester 7" }
  ],
  "event_groups": [
    { "id": "sports",  "label": "Sports & Fitness" },
    { "id": "culture", "label": "Culture & Arts" },
    { "id": "career",  "label": "Career & Networking" },
    { "id": "social",  "label": "Social Events" }
  ],
  "lectures": [ ... ],
  "events":   [ ... ]
}
```

#### Lecture-Objekt

```json
{
  "id":              "6643f1a2e4b0a1c2d3e4f5a6",
  "title":           "Rechnerarchitektur",
  "moduleId":        "31-57103",
  "courseOfStudyId": "IN",
  "semesterId":      "sem_1",
  "semesterIds":     ["sem_1"],
  "room":            "G2 1.44",
  "building":        "G2",
  "professor":       "Prof. Dr. Müller",
  "startTime":       "2026-05-11T08:00:00",
  "endTime":         "2026-05-11T09:30:00",
  "dayOfWeek":       "Monday",
  "durationMinutes": 90,
  "color":           "#4A90D9",
  "recurrence":      "weekly"
}
```

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | string | MongoDB-ID der Vorlesung |
| `title` | string | Modulname (bereinigt, ohne Modulnummer) |
| `moduleId` | string\|null | Modulnummer aus StarPlan, z. B. `"31-57103"` |
| `courseOfStudyId` | string | Studiengangs-Code, z. B. `"IN"` – passt zu `courses_of_study[].id` |
| `semesterId` | string | Primäres Semester, z. B. `"sem_1"` |
| `semesterIds` | string[] | Alle Semester dieser Vorlesung (z. B. `["sem_1","sem_2"]` bei gemeinsamen VL) |
| `room` | string | Raumnummer, z. B. `"G2 1.44"` |
| `building` | string | Gebäude-Code, z. B. `"G2"` – passt zu `buildings[].code` |
| `professor` | string | Dozent(in), kann leer sein |
| `startTime` | string (ISO 8601) | Startzeit |
| `endTime` | string (ISO 8601) | Endzeit |
| `dayOfWeek` | string | Englischer Wochentag: `"Monday"`, `"Tuesday"`, … |
| `durationMinutes` | int | Dauer in Minuten (meist 90) |
| `color` | string | Hex-Farbe pro Studiengang (deterministisch, z. B. `"#4A90D9"`) |
| `recurrence` | string | `"weekly"` – alle Vorlesungen aus StarPlan sind wöchentlich |

#### Event-Objekt

```json
{
  "id":        "6623a1f2e4b0a1c2d3e4f5a6",
  "title":     "Karrieremesse Aalen 2026",
  "groupId":   "career",
  "startTime": "2026-05-20T18:00:00",
  "endTime":   "2026-05-20T21:00:00",
  "color":     "#2ECC71",
  "is_public": true,
  "detail_url": "https://www.hs-aalen.de/aktuelles/veranstaltungen/karrieremesse-aalen-2026",

  "description":           "Über 80 Unternehmen stellen sich vor...",
  "organizer":             "Transferzentrum HS Aalen",
  "registration_url":      "https://www.hs-aalen.de/.../anmeldung",
  "registration_deadline": "15. Mai 2026"
}
```

> **Hinweis:** `description`, `organizer`, `registration_url` und `registration_deadline` sind **optional** –  
> sie sind nur vorhanden wenn der Scraper sie auf der Detail-Seite gefunden hat.  
> Das Frontend muss diese Felder mit null-check behandeln.

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | string | MongoDB-ID |
| `title` | string | Titel des Events |
| `groupId` | string | `"sports"`, `"culture"`, `"career"` oder `"social"` |
| `startTime` | string (ISO 8601) | Startzeit |
| `endTime` | string\|null | Endzeit (kann fehlen bei Ganztagsevents) |
| `color` | string | Hex-Farbe nach `groupId`: sports=`#F39C12`, culture=`#9B59B6`, career=`#2ECC71`, social=`#3498DB` |
| `is_public` | bool | `true` = ohne Login sichtbar |
| `detail_url` | string\|null | Link zur Event-Seite auf hs-aalen.de |
| `description` | string | (optional) Beschreibungstext von der Detail-Seite |
| `organizer` | string | (optional) Veranstalter / Trainer |
| `registration_url` | string | (optional) Anmeldelink |
| `registration_deadline` | string | (optional) Anmeldefrist als Text, z. B. `"28. Juli 2026"` |

#### Farben der Event-Gruppen

```dart
const eventGroupColors = {
  'sports':  '#F39C12',
  'culture': '#9B59B6',
  'career':  '#2ECC71',
  'social':  '#3498DB',
};
```

---

## 2. Settings

### `GET /api/v1/settings`

Gibt die gespeicherten Nutzereinstellungen zurück. Entspricht `settings.json`.

```json
{
  "notificationLeadMinutes": 15,
  "defaultCourseOfStudyIds": ["IN"],
  "defaultSemesterIds":      ["sem_1"],
  "defaultEventGroupIds":    ["career", "sports"],
  "savedLectureIds":         [],
  "savedEventIds":           [],
  "theme":                   "system"
}
```

| Feld | Typ | Beschreibung |
|---|---|---|
| `notificationLeadMinutes` | int | Vorlaufzeit für Push-Benachrichtigungen in Minuten |
| `defaultCourseOfStudyIds` | string[] | Standard-Studiengänge für die Timetable-Filterung |
| `defaultSemesterIds` | string[] | Standard-Semester |
| `defaultEventGroupIds` | string[] | Standard Event-Gruppen |
| `savedLectureIds` | string[] | Vom Nutzer gespeicherte Vorlesungs-IDs |
| `savedEventIds` | string[] | Vom Nutzer gespeicherte Event-IDs |
| `theme` | string | `"light"`, `"dark"` oder `"system"` |

---

### `PUT /api/v1/settings`

Speichert alle Einstellungen (vollständiges Überschreiben). Benötigt API-Key-Header.

**Request Body:** gleiche Struktur wie GET-Response.

```json
{
  "notificationLeadMinutes": 10,
  "defaultCourseOfStudyIds": ["IN"],
  "defaultSemesterIds": ["sem_2"],
  "defaultEventGroupIds": ["social"],
  "savedLectureIds": [],
  "savedEventIds": [],
  "theme": "dark"
}
```

**Response:** die gespeicherten Einstellungen (gleiche Struktur).

---

## 3. Street View Graph

### `GET /api/v1/streetview/graph`

Gibt den 360°-Navigationsgraphen zurück. Entspricht `street_view_graph.json`.

```json
{
  "startNode": "node0",
  "nodes": [
    {
      "id":      "node0",
      "image":   "/api/v1/images/rooms/G2-0.01/2026-04-15-083000-panorama.jpg",
      "building": "G2",
      "room":    "G2 0.01",
      "heading": 12,
      "exits": {
        "front": "node1",
        "right": "node2",
        "left":  null
      },
      "spots": [
        {
          "name":        "Hörsaal H1",
          "longitude":   45,
          "latitude":    0,
          "description": "Eingang Hörsaal H1"
        }
      ]
    },
    {
      "id":      "node1",
      "image":   "/api/v1/images/rooms/G2-1.44/2026-04-15-090000-panorama.jpg",
      "building": "G2",
      "room":    "G2 1.44",
      "heading": 0,
      "exits": {
        "back": "node0"
      },
      "spots": []
    }
  ]
}
```

| Feld | Typ | Beschreibung |
|---|---|---|
| `startNode` | string | ID des Einstiegs-Knotens |
| `nodes[].id` | string | Eindeutige Knoten-ID |
| `nodes[].image` | string | URL zum 360°-Bild (relativ, über `/api/v1/images/...` abrufbar) |
| `nodes[].building` | string | Gebäude-Code |
| `nodes[].room` | string | Raumnummer |
| `nodes[].heading` | int | Startausrichtung der Kamera in Grad (0–359) |
| `nodes[].exits` | object | Richtungs-Map → Knoten-ID (`"front"`, `"back"`, `"left"`, `"right"`) |
| `nodes[].spots` | array | Klickbare Informationspunkte im 360°-Bild |
| `spots[].longitude` | int | Horizontale Position im Panorama (0–360) |
| `spots[].latitude` | int | Vertikale Position (-90 bis 90) |

> **Navigation im Frontend:** Das Frontend traversiert den Graphen selbst.  
> `node.exits["front"]` liefert die ID des nächsten Knotens in dieser Richtung.  
> Es gibt keine server-seitige Routing-Berechnung.

---

## 4. Buildings

### `GET /api/v1/buildings`

```
GET /api/v1/buildings
GET /api/v1/buildings?campus=Burren
```

**Parameter:**

| Parameter | Typ | Beispiel | Beschreibung |
|---|---|---|---|
| `campus` | string | `Burren` oder `Main` | Filtert nach Campus-Standort |
| `skip` | int | `0` | Pagination |
| `limit` | int | `100` | Max. Ergebnisse (default 100) |

**Response:**

```json
[
  {
    "_id":                 "G2",
    "code":                "G2",
    "name":                "Gebäude G2",
    "description":         "Hier befinden sich die Räumlichkeiten der Fakultät Elektronik und Informatik.",
    "campus":              "Burren",
    "address":             "Anton-Huber-Straße 25",
    "floors":              [0, 1, 2],
    "room_count":          18,
    "street_view_enabled": true,
    "created_at":          "2026-01-01T00:00:00"
  }
]
```

**Verfügbare Gebäude (HS Aalen):**

| Code | Name | Campus |
|---|---|---|
| `G1` | Gebäude G1 (Optik & Mechatronik) | Burren |
| `G2` | Gebäude G2 (Elektronik & Informatik) | Burren |
| `G3` | Gebäude G3 (Bibliothek) | Burren |
| `G4` | Gebäude G4 (Augenoptik & Hörakustik) | Burren |
| `IZ` | Innovationszentrum | Burren |
| `M`  | Mensa | Burren |
| `E`  | Physikzentrum | Burren |
| `AH` | Anton-Huber-Straße (Aula) | Burren |
| `BS1` | Beethovenstraße 1 (Verwaltung) | Main |
| `S46` | Stuttgarter Straße 46 | Main |
| `WIN` | Wirtschaftswissenschaften | Main |
| `DIS` | Digital Innovation Space | Main |
| `NM` | Neue Mensa | Main |
| `SW` | Studentenwohnheim | Main |

---

## 5. Rooms

### `GET /api/v1/rooms`

```
GET /api/v1/rooms
GET /api/v1/rooms?building=G2
GET /api/v1/rooms?building=G2&floor=1
GET /api/v1/rooms?search=1.4
```

**Parameter:**

| Parameter | Typ | Beispiel | Beschreibung |
|---|---|---|---|
| `building` | string | `G2` | Filtert nach Gebäude-Code |
| `floor` | int | `1` | Filtert nach Stockwerk (0 = EG, 1 = 1. OG, …) |
| `search` | string | `G2 1` | Partial-Match auf Raumnummer |
| `skip` | int | `0` | Pagination |
| `limit` | int | `100` | Max. Ergebnisse (max. 1000) |

**Response:**

```json
[
  {
    "_id":                 "abc123",
    "room_number":         "G2 1.44",
    "room_id":             "42",
    "building":            "G2",
    "building_id":         "G2",
    "floor":               1,
    "capacity":            30,
    "has_video":           true,
    "has_projector":       true,
    "street_view_enabled": true,
    "ical_url":            "https://vorlesungen.htw-aalen.de/splan/ical?type=room&roomid=42",
    "last_scraped":        "2026-05-11T06:00:00",
    "created_at":          "2026-01-01T00:00:00"
  }
]
```

> **Tipp:** `room_number` aus dem Timetable-Endpunkt (z. B. `"G2 1.44"`) kann direkt  
> zum Lookup in dieser Liste verwendet werden.

---

## 6. Events

Die Events-Endpunkte liefern detailliertere Filter-Möglichkeiten als der Timetable-Endpunkt.  
Für die Stundenplan-Ansicht reicht der Timetable-Endpunkt. Diese Endpunkte sind für eine  
dedizierte Event-Übersichtsseite oder ein Event-Detail-View sinnvoll.

### `GET /api/v1/events`

```
GET /api/v1/events?public_only=true
GET /api/v1/events?date_from=2026-05-11T00:00:00&date_to=2026-05-31T23:59:59
```

**Parameter:**

| Parameter | Typ | Beschreibung |
|---|---|---|
| `category` | string | `Hochschule`, `Sport`, `Kultur`, `Mensa`, `Vortrag`, `Sonstiges` |
| `date_from` | string | ISO 8601, z. B. `2026-05-01T00:00:00` |
| `date_to` | string | ISO 8601 |
| `public_only` | bool | Nur öffentliche Events (default `false`) |
| `skip` / `limit` | int | Pagination (max. 200) |

**Response:** Array von Event-Objekten (gleiche Felder wie im Timetable-Endpunkt).

---

### `GET /api/v1/events/upcoming`

Gibt Events der nächsten N Tage zurück (sortiert nach Startzeit).

```
GET /api/v1/events/upcoming?days=7&public_only=true
```

| Parameter | Default | Beschreibung |
|---|---|---|
| `days` | 7 | Zeitraum ab heute (1–90) |
| `public_only` | false | Nur öffentliche Events |

---

### `GET /api/v1/events/{event_id}`

Gibt ein einzelnes Event anhand seiner MongoDB-ID zurück.

```
GET /api/v1/events/6623a1f2e4b0a1c2d3e4f5a6
```

**404** wenn nicht gefunden.

---

### `POST /api/v1/events` *(Admin)*

Legt ein neues Event an. Benötigt API-Key-Header.

```json
{
  "title":      "Workshop Flutter",
  "start_time": "2026-06-01T09:00:00",
  "end_time":   "2026-06-01T17:00:00",
  "category":   "Vortrag",
  "is_public":  true
}
```

**Response:** `{ "id": "6623a1f2e4b0a1c2d3e4f5a6" }`

---

### `PUT /api/v1/events/{event_id}` *(Admin)*

Vollständiges Ersetzen eines Events. Gleiche Felder wie POST.

---

### `DELETE /api/v1/events/{event_id}` *(Admin)*

```
DELETE /api/v1/events/6623a1f2e4b0a1c2d3e4f5a6
```

**Response:** `{ "message": "Event deleted successfully" }`

---

## 7. Images (360°)

### `GET /api/v1/images/rooms/{room_id}`

Liste aller 360°-Bilder für einen Raum.

```
GET /api/v1/images/rooms/G2-1.44
```

**Response:**

```json
{
  "room_id": "G2-1.44",
  "total_count": 2,
  "images": [
    {
      "_id":            "6623a1f2e4b0a1c2d3e4f5a6",
      "room_id":        "G2-1.44",
      "image_filename": "2026-04-15-083000-panorama.jpg",
      "file_size_mb":   4.2,
      "image_type":     "360_panoramic",
      "uploaded_at":    "2026-04-15T08:30:00",
      "image_url_api":  "/api/v1/images/rooms/G2-1.44/2026-04-15-083000-panorama.jpg"
    }
  ]
}
```

---

### `GET /api/v1/images/rooms/{room_id}/latest`

Gibt das neueste Bild eines Raums zurück (Metadaten-Objekt, kein Bild-Binary).

---

### `GET /api/v1/images/rooms/{room_id}/{filename}`

Liefert die Bilddatei selbst (JPEG/PNG/WEBP).

**Optionale Transform-Parameter:**

| Parameter | Beispiel | Beschreibung |
|---|---|---|
| `size` | `thumbnail` | `original`, `medium` (1600px), `thumbnail` (640px) |
| `width` | `800` | Zielbreite in Pixeln |
| `height` | `600` | Zielhöhe in Pixeln |
| `crop` | `100,200,400,300` | Ausschnitt: `x,y,width,height` oder `width,height` (zentriert) |

```
GET /api/v1/images/rooms/G2-1.44/2026-04-15-083000-panorama.jpg?size=thumbnail
GET /api/v1/images/rooms/G2-1.44/2026-04-15-083000-panorama.jpg?width=1600
GET /api/v1/images/rooms/G2-1.44/2026-04-15-083000-panorama.jpg?crop=50%,50%
```

> Diese URL kann direkt als `Image`-Source in Flutter verwendet werden.

---

### `POST /api/v1/images/rooms/{room_id}/upload` *(Admin)*

Upload eines 360°-Panoramabilds. `multipart/form-data`, Feld `file`.  
Max. 20 MB. Erlaubte Typen: JPEG, PNG, WEBP.

**Response:**

```json
{
  "message":  "Image uploaded successfully",
  "filename": "2026-04-15-083000-panorama.jpg"
}
```

---

### `DELETE /api/v1/images/rooms/{room_id}/{filename}` *(Admin)*

Löscht Bilddatei und Metadaten-Eintrag.

---

## Auth-Header

Einige Endpunkte sind mit *(Admin)* markiert und benötigen einen API-Key:

```
X-API-Key: <api_key>
```

Der Key wird über die Umgebungsvariable `API_KEY` gesetzt.  
**Lese-Endpunkte (GET) benötigen keinen Key.**

---

## Fehler-Codes

| HTTP Code | Bedeutung |
|---|---|
| `200` | OK |
| `400` | Ungültige Parameter (z. B. falsches Crop-Format) |
| `404` | Ressource nicht gefunden |
| `413` | Bild zu groß (> 20 MB) |
| `415` | Nicht unterstützter Dateityp |
| `422` | Fehlende Pflichtfelder im Request Body |
| `500` | Interner Fehler (DB nicht erreichbar o. Ä.) |

Alle Fehler haben den Body: `{ "detail": "<Fehlerbeschreibung>" }`

---

## Datenmodelle im Überblick

### Lecture (Vorlesung)

Wird **ausschließlich** vom Scraper aus StarPlan befüllt (täglich 06:00 Uhr).  
Jede Vorlesung ist einer Planungsgruppe zugeordnet (`course_code = "IN S1 AI"`)  
und einem Studiengang (`courseOfStudyId = "IN"`).

```
lecture_id       → iCal UID aus StarPlan (eindeutig)
module_name      → bereinigter Modulname
module_id        → Modulnummer aus StarPlan
room_number      → Raumnummer aus iCal LOCATION (z. B. "G2 1.44")
building         → Gebäude-Code (aus room_number extrahiert)
professor        → aus iCal DESCRIPTION geparst
start_time       → datetime (UTC)
end_time         → datetime (UTC)
day_of_week      → "Monday" … "Sunday"
duration_minutes → Dauer in Minuten
courseOfStudyId  → Studiengangs-Code (z. B. "IN")
semesterIds      → ["sem_1"] – Array, da VL für S1+S2 → ["sem_1","sem_2"]
color            → Hex-Farbe (deterministisch per MD5 des Studiengangs-Codes)
recurrence       → immer "weekly"
source_type      → immer "course"
```

### Event

Wird wöchentlich von der HS-Aalen-Website gescrapt.  
**Kein physischer Raum** – HS Aalen Events haben keine Raum-Angabe.

```
title                 → Titel
start_time            → ISO-String
end_time              → ISO-String (optional)
groupId               → "social" (alle HS-Aalen-Events)
is_public             → immer true
detail_url            → Link zur hs-aalen.de Seite
source_slug           → eindeutiger Slug aus der URL (Upsert-Key)
description           → optional, von Detailseite
organizer             → optional, von Detailseite
registration_url      → optional, Anmeldelink
registration_deadline → optional, Frist als Text
```

### Studiengang

```
_id      → Studiengangs-Code (z. B. "IN")
code     → gleich wie _id
name     → "Informatik"
semesters → [1,2,3,4,5,6,7]
color    → Hex-Farbe
```

### Building

```
_id                → Gebäude-Code (z. B. "G2")
code               → gleich wie _id
name               → "Gebäude G2"
campus             → "Burren" oder "Main"
address            → Straße
floors             → [0,1,2]
room_count         → Anzahl bekannter Räume
street_view_enabled → bool
```

### Settings (Singleton)

Aktuell **ein globales** Settings-Dokument – keine User-Authentifizierung.  
Im Produktivbetrieb müsste das pro Device-ID aufgeteilt werden.

---

## Typische Flutter-Flows

### App-Start

```
1. GET /api/v1/settings
   → defaultCourseOfStudyIds, defaultSemesterIds laden

2. GET /api/v1/timetable?course=IN&semester=sem_1
   → courses_of_study, semesters, lectures, events

3. Filter-UI mit courses_of_study[] und semesters[] befüllen
```

### Stundenplan-Filter ändern

```
GET /api/v1/timetable?course=IN,ET&semester=sem_2&date_from=2026-05-11
```

### Gebäude-Navigation öffnen

```
1. GET /api/v1/streetview/graph
   → startNode + nodes[] laden
   
2. nodes[startNode].image als 360°-Bild anzeigen
   → URL direkt als Image-Source nutzbar

3. Bei Tap auf Exit "front":
   → nextNodeId = nodes[currentId].exits["front"]
   → nodes[nextNodeId].image anzeigen
```

### Event-Detail anzeigen

```
GET /api/v1/events/{id}
→ description, organizer, registration_url, registration_deadline prüfen (können fehlen!)
→ detail_url als "Mehr auf hs-aalen.de" Link anzeigen
```

### 360°-Bild in bestimmter Auflösung laden

```dart
// Thumbnail für Raumvorschau
final thumbUrl = '/api/v1/images/rooms/$roomId/$filename?size=thumbnail';

// Vollbild für 360°-Viewer
final fullUrl  = '/api/v1/images/rooms/$roomId/$filename';
```
