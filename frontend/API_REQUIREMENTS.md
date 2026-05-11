# Campus Now – API-Anforderungen (Backend-Spezifikation)

> **Für die KI / den Backend-Entwickler:** Diese Datei beschreibt exakt, welche Daten die Flutter-App vom Backend erwartet.  
> Die App lädt diese Daten aktuell noch aus lokalen JSON-Assets (`assets/data/`).  
> Der Einstiegspunkt ist `lib/app_data_service.dart` – dort müssen die Asset-Aufrufe durch HTTP-Calls ersetzt werden.

---

## Übersicht der Endpunkte

| # | Methode | Pfad                           | Beschreibung                                  |
|---|---------|--------------------------------|-----------------------------------------------|
| 1 | `GET`   | `/api/v1/timetable`            | Stundenplan + Campusevents (mit Filtern)      |
| 2 | `GET`   | `/api/v1/settings`             | Nutzereinstellungen laden                     |
| 3 | `PUT`   | `/api/v1/settings`             | Nutzereinstellungen speichern                 |
| 4 | `GET`   | `/api/v1/streetview/graph`     | 360°-Navigations-Graph des Campus             |
| 5 | `GET`   | `/api/v1/buildings`            | Alle Gebäude mit ihren Räumen                 |
| 6 | `GET`   | `/api/v1/rooms`                | Räume, optional gefiltert nach Gebäude        |

---

## 1. `GET /api/v1/timetable`

### Beschreibung
Liefert alle Daten für den Stundenplan-Screen: Studiengänge, Semester, Eventgruppen, Vorlesungen und Campus-Events.  
Alle Filter sind optional – ohne Parameter wird der komplette Datensatz zurückgegeben.

### Query-Parameter (alle optional)

| Parameter     | Typ      | Beschreibung                                                                    | Beispiel                        |
|---------------|----------|---------------------------------------------------------------------------------|---------------------------------|
| `building`    | `string` | Filtert Vorlesungen **und** Events nach Gebäude-Kürzel (exakter Match)          | `?building=G2`                  |
| `room`        | `string` | Filtert Vorlesungen nach Raum (Partial-Match, case-insensitiv)                  | `?room=G2+1`                    |
| `professor`   | `string` | Filtert Vorlesungen nach Dozent (Partial-Match, case-insensitiv)                | `?professor=Müller`             |
| `course`      | `string` | Filtert nach `courseOfStudyId` (= StarPlan-Code), mehrere mit Komma             | `?course=INF+S1%2B2,INF+S3%2B4` |
| `semester`    | `string` | Filtert nach `semesterId`, mehrere mit Komma                                    | `?semester=sem_3,sem_4`         |
| `event_group` | `string` | Filtert Events nach `groupId`, mehrere mit Komma                                | `?event_group=sports,career`    |
| `date_from`   | `string` | Nur Einträge ab diesem Datum (`YYYY-MM-DD`)                                     | `?date_from=2026-04-14`         |
| `date_to`     | `string` | Nur Einträge bis zu diesem Datum (`YYYY-MM-DD`, inklusive)                      | `?date_to=2026-04-20`           |
| `recurrence`  | `string` | Filtert Vorlesungen nach Typ: `weekly` oder `once`                              | `?recurrence=weekly`            |

**Kombinierbar:** Alle Parameter können kombiniert werden.  
Beispiel – alle wöchentlichen Vorlesungen in Building B, Semester 3:
```
GET /api/v1/timetable?building=Building+B&semester=sem_3&recurrence=weekly
```

> **Hinweis:** Die App filtert aktuell noch client-seitig. Die Query-Parameter sind für spätere Performance-Optimierung und direkte API-Nutzung vorgesehen – das Response-Format bleibt identisch, nur die zurückgegebenen Einträge werden reduziert.

### Response – `Content-Type: application/json`

```json
{
  "courses_of_study": [
    { "id": "cs_b3",   "label": "Computer Science" },
    { "id": "me_b1",   "label": "Mechanical Engineering" },
    { "id": "mb_b5",   "label": "Medical Biotechnology" },
    { "id": "bwl_b2",  "label": "Business Administration" },
    { "id": "ei_b4",   "label": "Electrical Engineering" },
    { "id": "wi_b6",   "label": "Industrial Engineering" },
    { "id": "arch_b1", "label": "Architecture" },
    { "id": "inf_b2",  "label": "Applied Informatics" },
    { "id": "phy_b1",  "label": "Applied Physics" },
    { "id": "env_b2",  "label": "Environmental Engineering" },
    { "id": "civ_b3",  "label": "Civil Engineering" },
    { "id": "che_b2",  "label": "Chemical Engineering" },
    { "id": "bio_b1",  "label": "Biomedical Engineering" },
    { "id": "ds_b1",   "label": "Data Science" },
    { "id": "ai_b1",   "label": "Artificial Intelligence" },
    { "id": "ux_b1",   "label": "User Experience Design" },
    { "id": "log_b1",  "label": "Logistics & Supply Chain" },
    { "id": "fin_b1",  "label": "Finance & Accounting" },
    { "id": "mkt_b1",  "label": "Marketing & Communication" }
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
  "lectures": [
    {
      "id":             "lec_001",
      "title":          "Algorithms & Data Structures",
      "courseOfStudyId": "cs_b3",
      "semesterId":      "sem_3",
      "room":            "B 204",
      "building":        "Building B",
      "professor":       "Prof. Dr. Müller",
      "startTime":       "2026-04-14T08:00:00",
      "endTime":         "2026-04-14T09:30:00",
      "color":           "#4A90D9",
      "recurrence":      "weekly",
      "notes":           "Bring your laptop."
    }
  ],
  "events": [
    {
      "id":        "evt_001",
      "title":     "Campus Run 5K",
      "groupId":   "sports",
      "location":  "Campus Sports Ground",
      "building":  "Sports Complex",
      "organizer": "Student Sports Club",
      "startTime": "2026-04-14T17:00:00",
      "endTime":   "2026-04-14T19:00:00",
      "color":     "#F39C12",
      "description": "Annual 5K campus run open to all students and staff.",
      "imageUrl":  "https://example.com/image.jpg"
    }
  ]
}
```

### Feldspezifikation

#### `courses_of_study[]` – Studiengangsliste (Pflicht)
| Feld    | Typ      | Pflicht | Beschreibung              |
|---------|----------|---------|---------------------------|
| `id`    | `string` | Ja      | Eindeutige ID             |
| `label` | `string` | Ja      | Anzeigename               |

#### `semesters[]` – Semesterliste (Pflicht, kann leer sein)
| Feld    | Typ      | Pflicht | Beschreibung              |
|---------|----------|---------|---------------------------|
| `id`    | `string` | Ja      | z. B. `"sem_1"`           |
| `label` | `string` | Ja      | z. B. `"Semester 1"`      |

#### `event_groups[]` – Eventgruppen (Pflicht)
| Feld    | Typ      | Pflicht | Beschreibung              |
|---------|----------|---------|---------------------------|
| `id`    | `string` | Ja      | z. B. `"sports"`          |
| `label` | `string` | Ja      | Anzeigename               |

#### `lectures[]` – Vorlesungen (Pflicht)
| Feld              | Typ      | Pflicht | Beschreibung                                          |
|-------------------|----------|---------|-------------------------------------------------------|
| `id`              | `string` | Ja      | Eindeutige ID, z. B. `"lec_001"`                     |
| `title`           | `string` | Ja      | Name der Vorlesung                                   |
| `courseOfStudyId` | `string` | Ja      | Referenz auf `courses_of_study[].id`                 |
| `semesterId`      | `string` | Nein    | Referenz auf `semesters[].id`, Default `""`          |
| `room`            | `string` | Ja      | Raumbezeichnung, z. B. `"B 204"`                     |
| `building`        | `string` | Ja      | Gebäudename                                          |
| `professor`       | `string` | Ja      | Name des Dozenten                                    |
| `startTime`       | `string` | Ja      | ISO 8601, z. B. `"2026-04-14T08:00:00"`             |
| `endTime`         | `string` | Ja      | ISO 8601                                             |
| `color`           | `string` | Ja      | Hex-Farbe mit `#`, z. B. `"#4A90D9"` (6 Zeichen)   |
| `recurrence`      | `string` | Nein    | `"weekly"` oder `"once"`, Default `"once"`           |
| `notes`           | `string` | Nein    | Freitext, Default `""`                               |

#### `events[]` – Campus-Events (Pflicht)
| Feld          | Typ           | Pflicht | Beschreibung                                       |
|---------------|---------------|---------|---------------------------------------------------|
| `id`          | `string`      | Ja      | Eindeutige ID, z. B. `"evt_001"`                 |
| `title`       | `string`      | Ja      | Name des Events                                  |
| `groupId`     | `string`      | Ja      | Referenz auf `event_groups[].id`                 |
| `location`    | `string`      | Ja      | Ortsangabe                                       |
| `building`    | `string`      | Ja      | Gebäudename                                      |
| `organizer`   | `string`      | Ja      | Veranstalter                                     |
| `startTime`   | `string`      | Ja      | ISO 8601                                         |
| `endTime`     | `string`      | Ja      | ISO 8601                                         |
| `color`       | `string`      | Ja      | Hex-Farbe mit `#`, z. B. `"#F39C12"`            |
| `description` | `string`      | Ja      | Beschreibungstext                                |
| `imageUrl`    | `string\|null` | Nein   | Bild-URL oder `null`                             |

---

## 2. `GET /api/v1/settings`

### Beschreibung
Lädt die gespeicherten Nutzereinstellungen. Wird beim App-Start aufgerufen.

### Request
- Keine Parameter, kein Body.

### Response – `Content-Type: application/json`

```json
{
  "notificationLeadMinutes": 15,
  "defaultCourseOfStudyIds": ["cs_b3"],
  "defaultSemesterIds":      ["sem_3"],
  "defaultEventGroupIds":    ["career", "sports"],
  "savedLectureIds":         [],
  "savedEventIds":           [],
  "theme":                   "system"
}
```

### Feldspezifikation

| Feld                       | Typ        | Pflicht | Beschreibung                                                |
|----------------------------|------------|---------|-------------------------------------------------------------|
| `notificationLeadMinutes`  | `int`      | Ja      | Vorlaufzeit für Benachrichtigungen in Minuten               |
| `defaultCourseOfStudyIds`  | `string[]` | Ja      | Vorausgewählte Studiengänge (IDs aus `courses_of_study`)    |
| `defaultSemesterIds`       | `string[]` | Ja      | Vorausgewählte Semester (IDs aus `semesters`), kann leer sein |
| `defaultEventGroupIds`     | `string[]` | Ja      | Vorausgewählte Eventgruppen (IDs aus `event_groups`)        |
| `savedLectureIds`          | `string[]` | Ja      | Vom Nutzer gespeicherte Vorlesungs-IDs                      |
| `savedEventIds`            | `string[]` | Ja      | Vom Nutzer gespeicherte Event-IDs                           |
| `theme`                    | `string`   | Nein    | `"system"` \| `"light"` \| `"dark"`, Default `"system"`   |

> **Hinweis:** Das Feld `defaultCourseOfStudyId` (Singular) wird vom App-Code auch noch als Legacy-Format erkannt und als einzelner Wert in die Liste gewandelt – das neue Format ist aber immer der Plural `defaultCourseOfStudyIds`.

---

## 3. `PUT /api/v1/settings`

### Beschreibung
Speichert die aktuellen Nutzereinstellungen. Wird aufgerufen, wenn der Nutzer in der App Einstellungen ändert.

### Request – `Content-Type: application/json`

Body ist identisch mit dem Response-Format von `GET /api/settings`:

```json
{
  "notificationLeadMinutes": 15,
  "defaultCourseOfStudyIds": ["cs_b3"],
  "defaultSemesterIds":      ["sem_3"],
  "defaultEventGroupIds":    ["career", "sports"],
  "savedLectureIds":         ["lec_001"],
  "savedEventIds":           [],
  "theme":                   "dark"
}
```

### Response

```json
{ "success": true }
```

Oder HTTP `200 OK` ohne Body – beides wird von der App akzeptiert.

---

## 4. `GET /api/v1/streetview/graph`

### Beschreibung
Liefert den 360°-Navigationsgraph des Campus für den Street-View-Screen. Die App lädt diesen Graphen separat (in `lib/models/graph_node.dart`).

### Request
- Keine Parameter, kein Body.

### Response – `Content-Type: application/json`

```json
{
  "startNode": "node0",
  "nodes": [
    {
      "id":       "node0",
      "image":    "https://cdn.example.com/360/0.jpg",
      "building": "Waterfront",
      "room":     "Pier Entrance",
      "heading":  12,
      "exits": {
        "front": "node1",
        "right": "node2"
      },
      "spots": [
        {
          "name":        "Dock Sign",
          "longitude":   8.0,
          "latitude":    0.0,
          "description": "Beschreibungstext des Punktes"
        }
      ]
    },
    {
      "id":       "node1",
      "image":    "https://cdn.example.com/360/1.jpg",
      "building": "North Sector",
      "room":     "Snow Access Road",
      "heading":  22,
      "exits": {
        "back":  "node0",
        "front": "node4",
        "left":  "node3"
      },
      "spots": []
    }
  ]
}
```

### Feldspezifikation

#### Root-Objekt
| Feld        | Typ      | Pflicht | Beschreibung                                  |
|-------------|----------|---------|-----------------------------------------------|
| `startNode` | `string` | Ja      | ID des Start-Knotens beim Öffnen des Screens  |
| `nodes`     | `array`  | Ja      | Liste aller Knoten (wird in Map umgewandelt)  |

#### `nodes[]` – Einzelner Knoten
| Feld       | Typ                    | Pflicht | Beschreibung                                                      |
|------------|------------------------|---------|-------------------------------------------------------------------|
| `id`       | `string`               | Ja      | Eindeutige Knoten-ID, z. B. `"node0"`                            |
| `image`    | `string`               | Ja      | URL (oder Asset-Pfad) zum 360°-Bild                              |
| `building` | `string`               | Ja      | Gebäudename                                                       |
| `room`     | `string`               | Ja      | Raum-/Standortbezeichnung                                         |
| `heading`  | `number`               | Ja      | Blickrichtung in Grad (wird als `double` gespeichert)            |
| `exits`    | `object<string,string>`| Ja      | Map von Richtung → Knoten-ID, z. B. `{"front":"node1"}`         |
| `spots`    | `array`                | Ja      | Liste interaktiver Punkte (kann leer `[]` sein)                  |

#### `spots[]` – Interaktive Punkte
| Feld          | Typ      | Pflicht | Beschreibung                                         |
|---------------|----------|---------|------------------------------------------------------|
| `name`        | `string` | Ja      | Anzeigename des Punktes                              |
| `longitude`   | `number` | Ja      | X-Position im Panorama (wird als `double` verwendet) |
| `latitude`    | `number` | Ja      | Y-Position im Panorama (wird als `double` verwendet) |
| `description` | `string` | Ja      | Beschreibungstext                                    |

> **Hinweis zu `exits`-Richtungen:** Aktuell werden folgende Richtungsschlüssel im Beispieldatensatz verwendet: `"front"`, `"back"`, `"left"`, `"right"`. Die App liest diese Werte generisch als Map – beliebige Schlüssel sind technisch möglich.

---

## 5. `GET /api/v1/buildings`

### Beschreibung
Liefert alle Gebäude des Campus mit den darin enthaltenen Räumen. Die Daten werden aus Vorlesungen und Events aggregiert.  
Nützlich für Dropdown-Filter in der App oder für eine Raumsuche.

### Request
- Keine Parameter, kein Body.

### Response – `Content-Type: application/json`

```json
{
  "buildings": [
    {
      "name":  "Building A",
      "rooms": ["A 101", "A 215"]
    },
    {
      "name":  "Building B",
      "rooms": ["B 204", "B 310"]
    },
    {
      "name":  "Building C",
      "rooms": ["C 012"]
    },
    {
      "name":  "Building D",
      "rooms": ["D 001"]
    }
  ]
}
```

### Feldspezifikation

#### Root-Objekt
| Feld        | Typ     | Pflicht | Beschreibung            |
|-------------|---------|---------|-------------------------|
| `buildings` | `array` | Ja      | Liste aller Gebäude     |

#### `buildings[]`
| Feld    | Typ        | Pflicht | Beschreibung                                     |
|---------|------------|---------|--------------------------------------------------|
| `name`  | `string`   | Ja      | Gebäudename, identisch mit `building`-Feld in Lectures/Events |
| `rooms` | `string[]` | Ja      | Sortierte Liste aller Räume in diesem Gebäude    |

> **Hinweis:** `rooms` enthält nur Räume aus `lectures[]`. Events haben einen `location`-String, aber keinen strukturierten Raum – diese tauchen hier nicht auf.

---

## 6. `GET /api/v1/rooms`

### Beschreibung
Liefert eine flache Liste aller Räume. Optional nach Gebäude gefiltert.  
Praktisch für eine Raumsuche oder Autocomplete-Felder.

### Query-Parameter

| Parameter  | Typ      | Pflicht | Beschreibung                                          | Beispiel              |
|------------|----------|---------|-------------------------------------------------------|-----------------------|
| `building` | `string` | Nein    | Nur Räume aus diesem Gebäude (exakter Match)          | `?building=Building+B`|
| `search`   | `string` | Nein    | Partial-Match auf Raumnamen (case-insensitiv)         | `?search=B+2`         |

### Response – `Content-Type: application/json`

Ohne Parameter – alle Räume:
```json
{
  "rooms": [
    { "room": "A 101",  "building": "Building A" },
    { "room": "A 215",  "building": "Building A" },
    { "room": "B 204",  "building": "Building B" },
    { "room": "B 310",  "building": "Building B" },
    { "room": "C 012",  "building": "Building C" },
    { "room": "D 001",  "building": "Building D" }
  ]
}
```

Mit `?building=Building+B`:
```json
{
  "rooms": [
    { "room": "B 204", "building": "Building B" },
    { "room": "B 310", "building": "Building B" }
  ]
}
```

### Feldspezifikation

#### `rooms[]`
| Feld       | Typ      | Pflicht | Beschreibung                                        |
|------------|----------|---------|-----------------------------------------------------|
| `room`     | `string` | Ja      | Raumbezeichnung, identisch mit `room`-Feld in Lectures |
| `building` | `string` | Ja      | Gebäude, in dem der Raum liegt                      |

> **Kombination mit `/api/v1/timetable`:** Wenn der Nutzer einen Raum auswählt, kann anschließend  
> `GET /api/v1/timetable?building=Building+B&room=B+204` gerufen werden, um alle Vorlesungen in diesem Raum zu laden.

---

## Technische Hinweise für die Implementierung

### Datums-/Zeitformat
Alle `startTime`/`endTime`-Felder müssen im **ISO 8601**-Format sein:
```
"2026-04-14T08:00:00"
```
Die App parst diese mit `DateTime.parse()` – Zeitzone ist optional, wird aber als local behandelt.

### Farben
Alle `color`-Felder müssen als **6-stelliger Hex-String mit `#`** geliefert werden:
```
"#4A90D9"
```
Die App wandelt intern mit `int.parse('FF' + hex, radix: 16)` zu einem Flutter-`Color`-Objekt.

### Null-Handling
- `imageUrl` in Events darf `null` sein – das einzige optionale Feld.
- `semesterId` in Lectures darf fehlen oder `null` sein → Default `""`.
- `recurrence` in Lectures darf fehlen → Default `"once"`.
- `notes` in Lectures darf fehlen → Default `""`.
- `theme` in Settings darf fehlen → Default `"system"`.

### Dateigröße / Caching
Die App hat kein eigenes HTTP-Caching implementiert. Das Backend sollte sinnvolle `Cache-Control`-Header setzen:
- `GET /api/timetable` → z. B. `Cache-Control: max-age=300` (5 Minuten)
- `GET /api/settings` → `Cache-Control: no-cache` (immer aktuell)
- `GET /api/street-view-graph` → z. B. `Cache-Control: max-age=3600` (1 Stunde)

### HTTP-Pakete (Flutter-Seite – noch nicht implementiert)
Für die Implementierung in der App muss noch in `pubspec.yaml` ergänzt werden:
```yaml
dependencies:
  http: ^1.2.0   # oder
  dio: ^5.4.0
```

---

## Wo im Code muss die API eingebunden werden?

| Datei                                | Was ändern                                                   |
|--------------------------------------|--------------------------------------------------------------|
| `lib/app_data_service.dart`          | `load()` – Asset-Aufrufe durch HTTP-Calls ersetzen           |
| `lib/app_data_service.dart`          | `saveSettings()` – lokale Zuweisung durch PUT-Request ersetzen |
| `pubspec.yaml`                       | HTTP-Paket hinzufügen                                        |
| (neu) `lib/services/api_service.dart`| Neuer Service mit Base-URL und HTTP-Client                   |

Der Kommentar in `app_data_service.dart` Zeile 7 bestätigt das:
```dart
/// Replace [load] with API calls when the backend is ready.
```

---

## Zusammenfassung

Die App benötigt **6 Endpunkte**:

1. **`GET /api/v1/timetable`** → alle Stundenplan- und Eventdaten, mit optionalen Filtern
2. **`GET /api/v1/settings`** → Nutzereinstellungen (beim Start geladen)
3. **`PUT /api/v1/settings`** → Nutzereinstellungen speichern (bei jeder Änderung)
4. **`GET /api/v1/streetview/graph`** → Campus-Navigationsgraph mit 360°-Bildern
5. **`GET /api/v1/buildings`** → alle Gebäude mit ihren Räumen
6. **`GET /api/v1/rooms`** → Räumeliste, optional nach Gebäude oder Suchbegriff gefiltert

### Filter-Übersicht für `/api/timetable`

| Filter        | Filtert                  | Typ                        |
|---------------|--------------------------|----------------------------|
| `building`    | Lectures + Events        | Exakter Match              |
| `room`        | Nur Lectures             | Partial-Match              |
| `professor`   | Nur Lectures             | Partial-Match              |
| `course`      | Nur Lectures             | ID(s), Komma-getrennt      |
| `semester`    | Nur Lectures             | ID(s), Komma-getrennt      |
| `event_group` | Nur Events               | ID(s), Komma-getrennt      |
| `date_from`   | Lectures + Events        | Datum `YYYY-MM-DD`         |
| `date_to`     | Lectures + Events        | Datum `YYYY-MM-DD`         |
| `recurrence`  | Nur Lectures             | `weekly` oder `once`       |

Alle Antworten sind **JSON**. Es gibt aktuell **keine Authentifizierung**.
