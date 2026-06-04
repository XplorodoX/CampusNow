# CampusNow API – Frontend-Dokumentation

> **Stand:** Juni 2026 · **Version:** 1.0.0  
> Vollständige Referenz aller REST-Endpoints für die Flutter-App-Integration.

---

## Inhaltsverzeichnis

1. [Übersicht](#1-übersicht)
2. [Requests senden](#2-requests-senden)
3. [Responses empfangen](#3-responses-empfangen)
4. [Authentifizierung](#4-authentifizierung)
5. [Fehlerbehandlung](#5-fehlerbehandlung)
6. [Users](#6-users)
7. [Settings](#7-settings)
8. [Timetable](#8-timetable)
9. [StreetView & Navigation](#9-streetview--navigation)
10. [Buildings](#10-buildings)
11. [Rooms](#11-rooms)
12. [Events](#12-events)
13. [Images](#13-images)
14. [Scheduler](#14-scheduler)
15. [Datenmodelle](#15-datenmodelle)
16. [Schnellreferenz](#16-schnellreferenz-aller-endpoints)

---

## 1. Übersicht

| | |
|---|---|
| **Base URL (Produktion)** | `https://streetview.8xc.de` |
| **Base URL (Lokal)** | `http://localhost:6058` |
| **API-Prefix** | `/api/v1` |
| **Swagger UI** | `{base}/docs` |

Alle Pfade in dieser Dokumentation sind relativ zur **Base URL + API-Prefix**.  
Vollständiges Beispiel: `https://streetview.8xc.de/api/v1/timetable`

---

## 2. Requests senden

### 2.1 Allgemeine Request-Headers

Für alle Requests empfohlen:

```
Accept: application/json
Content-Type: application/json   ← nur bei POST/PUT/PATCH mit JSON-Body
```

### 2.2 Requests nach Typ

#### GET – Daten abrufen
Keine Body, keine Content-Type-Header nötig. Parameter werden als Query-String übergeben.

```bash
# cURL
curl -X GET "https://streetview.8xc.de/api/v1/timetable?course=INF%20S1%2B2" \
  -H "Accept: application/json"
```

```dart
// Flutter (http package)
final response = await http.get(
  Uri.parse('https://streetview.8xc.de/api/v1/timetable')
    .replace(queryParameters: {'course': 'INF S1+2'}),
  headers: {'Accept': 'application/json'},
);
```

#### POST / PUT / PATCH – JSON-Body senden

```bash
# cURL
curl -X POST "https://streetview.8xc.de/api/v1/events" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "X-API-Key: <api-key>" \
  -d '{"title": "Event", "start_time": "2026-07-10T09:00:00+02:00", "end_time": "2026-07-10T17:00:00+02:00"}'
```

```dart
// Flutter
final response = await http.post(
  Uri.parse('https://streetview.8xc.de/api/v1/events'),
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-API-Key': apiKey,
  },
  body: jsonEncode({
    'title': 'Event',
    'start_time': '2026-07-10T09:00:00+02:00',
    'end_time': '2026-07-10T17:00:00+02:00',
  }),
);
```

#### POST – Datei hochladen (Multipart)

Für Bild-Uploads: `Content-Type: multipart/form-data` (wird automatisch gesetzt).

```bash
# cURL
curl -X POST "https://streetview.8xc.de/api/v1/images/rooms/2_35/upload" \
  -H "X-API-Key: <api-key>" \
  -F "file=@/pfad/zum/panorama.jpg"
```

```dart
// Flutter
final request = http.MultipartRequest(
  'POST',
  Uri.parse('https://streetview.8xc.de/api/v1/images/rooms/2_35/upload'),
)
  ..headers['X-API-Key'] = apiKey
  ..files.add(await http.MultipartFile.fromPath('file', '/pfad/panorama.jpg'));

final response = await request.send();
```

#### DELETE – Ressource löschen

```bash
# cURL
curl -X DELETE "https://streetview.8xc.de/api/v1/events/64a1b2c3d4e5f6789abcdef0" \
  -H "X-API-Key: <api-key>"
```

```dart
// Flutter
final response = await http.delete(
  Uri.parse('https://streetview.8xc.de/api/v1/events/64a1b2c3d4e5f6789abcdef0'),
  headers: {'X-API-Key': apiKey},
);
```

### 2.3 URL-Encoding

Query-Parameter mit Sonderzeichen müssen URL-encoded sein:

| Zeichen | Encoded | Beispiel |
|---------|---------|---------|
| Leerzeichen | `%20` | `G2 2.34` → `G2%202.34` |
| `+` | `%2B` | `INF S1+2` → `INF%20S1%2B2` |
| `/` | `%2F` | `path/to` → `path%2Fto` |
| `,` | `%2C` | `sem_3,sem_4` → `sem_3%2Csem_4` |

> **Flutter-Tipp:** `Uri.replace(queryParameters: {...})` encoded automatisch korrekt.  
> Niemals manuell concatenaten: `'?to_room=' + roomId` — das führt bei Leerzeichen zu Fehlern.

```dart
// Richtig
final uri = Uri.parse('$baseUrl/api/v1/streetview/route/building/G2')
  .replace(queryParameters: {
    'to_room': 'G2 2.34',
    'from_room': 'G2 2.01',
  });
// Ergibt: /api/v1/streetview/route/building/G2?to_room=G2%202.34&from_room=G2%202.01
```

---

## 3. Responses empfangen

### 3.1 Response-Formate nach Endpoint-Typ

| Endpoint-Typ | Response `Content-Type` | Verarbeitung |
|---|---|---|
| Normale Endpoints | `application/json` | `jsonDecode(response.body)` |
| `/map` Endpoints | `image/svg+xml` | Als String speichern oder `SvgPicture.string()` |
| `/floorplan/{id}` | `image/svg+xml` | Als String speichern |
| `/images/rooms/{id}/{file}` | `image/jpeg` oder `image/png` | Als Bytes speichern (`response.bodyBytes`) |

### 3.2 JSON-Responses parsen

```dart
import 'dart:convert';

final response = await http.get(Uri.parse('$baseUrl/api/v1/timetable'));

if (response.statusCode == 200) {
  final data = jsonDecode(response.body) as Map<String, dynamic>;
  final lectures = data['lectures'] as List<dynamic>;
  // ...
} else {
  final error = jsonDecode(response.body)['detail'] as String;
  throw Exception('API Error: $error');
}
```

### 3.3 SVG-Responses anzeigen

```dart
// pubspec.yaml: flutter_svg: ^2.0.0
import 'package:flutter_svg/flutter_svg.dart';

final response = await http.get(
  Uri.parse('$baseUrl/api/v1/streetview/graph/building/G2/map?floor=2'),
);

if (response.statusCode == 200) {
  final svgString = response.body;
  // Anzeigen:
  SvgPicture.string(svgString)
  // Oder als URL direkt laden:
  SvgPicture.network('$baseUrl/api/v1/streetview/graph/building/G2/map?floor=2')
}
```

### 3.4 Bild-Responses laden

```dart
// Als bytes
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/images/rooms/2_35/panorama.jpg?size=medium'),
);
final imageBytes = response.bodyBytes;
Image.memory(imageBytes)

// Oder direkt als NetworkImage (einfacher)
Image.network('$baseUrl/api/v1/images/rooms/2_35/panorama.jpg?size=medium')
```

### 3.5 Response-Headers prüfen

```dart
final contentType = response.headers['content-type'];
final contentLength = response.headers['content-length'];
```

---

## 4. Authentifizierung

### 4.1 Admin-Endpoints (`X-API-Key`)

Alle **Admin-Schreib-Endpoints** (`POST`, `PUT`, `PATCH`, `DELETE` außer Settings) erfordern:

```
X-API-Key: <api-key>
```

```dart
// Flutter – konstanter API-Key in der App
const apiKey = 'dein-api-key';

final response = await http.post(
  uri,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey,
  },
  body: jsonEncode(body),
);
```

Fehlender oder ungültiger Key → `401 Unauthorized`:
```json
{ "detail": "Unauthorized" }
```

### 4.2 User-Endpoints (`X-User-ID`)

Die **User- und Settings-Endpoints** (`POST /users`, `GET`, `PUT`, `PATCH /settings`) identifizieren den Nutzer über seine **Firebase UID**:

```
X-User-ID: <firebase-uid>
```

```dart
// Flutter – Firebase UID nach Login
import 'package:firebase_auth/firebase_auth.dart';

final uid = FirebaseAuth.instance.currentUser?.uid;

final response = await http.get(
  Uri.parse('$baseUrl/api/v1/settings'),
  headers: {
    'Accept': 'application/json',
    'X-User-ID': uid!,
  },
);
```

Fehlender oder leerer Header → `400 Bad Request`:
```json
{ "detail": "X-User-ID Header fehlt." }
```

Jeder Nutzer hat seine eigenen Einstellungen — isoliert über seine Firebase UID.

---

## 5. Fehlerbehandlung

Alle Fehler-Responses:
- **Content-Type:** `application/json`
- **Body:**
```json
{ "detail": "Beschreibung des Fehlers" }
```

| Status | Bedeutung | Typischer Grund |
|--------|-----------|----------------|
| `200` | Erfolg | — |
| `400` | Ungültige Parameter | `X-User-ID` fehlt, Crop-Format falsch, Wert außerhalb Range |
| `401` | Nicht autorisiert | API-Key fehlt oder falsch · User nicht registriert |
| `404` | Nicht gefunden | Gebäude/Raum/Node/Bild existiert nicht |
| `413` | Datei zu groß | Upload > 20 MB |
| `415` | Falsches Format | Kein JPEG/PNG/WEBP |
| `422` | Schema-Fehler | Pflichtfeld fehlt, falscher Typ |
| `500` | Serverfehler | Datenbankfehler, interner Fehler |

```dart
// Universelle Fehlerbehandlung Flutter
Future<Map<String, dynamic>> apiGet(String path) async {
  final response = await http.get(Uri.parse('$baseUrl$path'));
  
  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  }
  
  String detail = 'Unbekannter Fehler';
  try {
    detail = jsonDecode(response.body)['detail'] ?? detail;
  } catch (_) {}
  
  throw ApiException(response.statusCode, detail);
}

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);
}
```

---

## 6. Users

### `POST /users`

Registriert einen neuen User anhand seiner Firebase UID. **Öffentlicher Endpoint — kein API-Key nötig.**

Einmalig nach dem ersten Firebase-Login aufrufen. Ist die UID bereits registriert, wird der vorhandene User zurückgegeben (idempotent).

> Ohne vorherige Registrierung liefern alle `GET /settings`, `PUT /settings` und `PATCH /settings` einen `401 Unauthorized`.

**Request:**
```
POST /api/v1/users
X-User-ID: <firebase-uid>
```

**Response (201 Created – neuer User):**
```json
{ "created_at": "2026-06-04T12:00:00+00:00" }
```

**Response (200 OK – bereits registriert):**
```json
{ "created_at": "2026-06-01T09:30:00+00:00" }
```

**cURL:**
```bash
curl -X POST "https://streetview.8xc.de/api/v1/users" \
  -H "X-User-ID: <firebase-uid>"
```

**Flutter:**
```dart
final uid = FirebaseAuth.instance.currentUser!.uid;
final response = await http.post(
  Uri.parse('$baseUrl/api/v1/users'),
  headers: {'X-User-ID': uid},
);
// 201 = neu angelegt, 200 = bereits registriert — beides ist OK
```

**Empfohlener App-Flow:**
```dart
// 1. Firebase Login
final userCredential = await FirebaseAuth.instance.signInWithXxx(...);
final uid = userCredential.user!.uid;

// 2. User registrieren (einmalig, idempotent)
await http.post(
  Uri.parse('$baseUrl/api/v1/users'),
  headers: {'X-User-ID': uid},
);

// 3. Settings laden
final settingsRes = await http.get(
  Uri.parse('$baseUrl/api/v1/settings'),
  headers: {'X-User-ID': uid},
);
```

---

## 7. Settings

### `GET /settings`

Gibt Benutzereinstellungen + statische Metadaten zurück. **Einmalig pro Session aufrufen.**

**Request:**
```
GET /api/v1/settings
Accept: application/json
X-User-ID: <firebase-uid>
```

**Response:**
```
200 OK
Content-Type: application/json
```
```json
{
  "notificationLeadMinutes": 15,
  "defaultCourseOfStudyIds": ["INF S1+2"],
  "defaultSemesterIds": ["sem_3"],
  "defaultEventGroupIds": [],
  "savedLectureIds": [],
  "savedEventIds": [],
  "theme": "system",
  "courses_of_study": [
    { "id": "INF S1+2", "label": "Informatik S1+2", "color": "#4f8ef7" }
  ],
  "semesters": [
    { "id": "sem_3", "label": "Sommersemester 2026" }
  ],
  "event_groups": [
    { "id": "sports", "label": "Sport", "color": "#3fb950" }
  ]
}
```

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/settings" \
  -H "X-User-ID: <firebase-uid>"
```

**Flutter:**
```dart
final uid = FirebaseAuth.instance.currentUser!.uid;
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/settings'),
  headers: {'X-User-ID': uid},
);
final config = jsonDecode(response.body);
```

---

### `PUT /settings`

Überschreibt alle Einstellungen. Metadatenfelder (`courses_of_study` etc.) werden ignoriert.

**Request:**
```
PUT /api/v1/settings
Content-Type: application/json
X-User-ID: <firebase-uid>
```
```json
{
  "notificationLeadMinutes": 15,
  "defaultCourseOfStudyIds": ["INF S1+2"],
  "defaultSemesterIds": ["sem_3"],
  "defaultEventGroupIds": [],
  "savedLectureIds": [],
  "savedEventIds": [],
  "theme": "dark"
}
```

**Body-Felder:**

| Feld | Typ | Default | Beschreibung |
|------|-----|---------|-------------|
| `notificationLeadMinutes` | `int` | `15` | Benachrichtigungsvorlauf in Minuten |
| `defaultCourseOfStudyIds` | `string[]` | `[]` | Vorausgewählte Studiengänge |
| `defaultSemesterIds` | `string[]` | `[]` | Vorausgewählte Semester |
| `defaultEventGroupIds` | `string[]` | `[]` | Vorausgewählte Event-Gruppen |
| `savedLectureIds` | `string[]` | `[]` | Gespeicherte Vorlesungs-IDs |
| `savedEventIds` | `string[]` | `[]` | Gespeicherte Event-IDs |
| `theme` | `string` | `"system"` | `"light"` \| `"dark"` \| `"system"` |

**Response:**
```
200 OK
Content-Type: application/json
```
Gleiche Struktur wie Request Body.

**cURL:**
```bash
curl -X PUT "https://streetview.8xc.de/api/v1/settings" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: <firebase-uid>" \
  -d '{"notificationLeadMinutes": 15, "theme": "dark", "defaultCourseOfStudyIds": [], "defaultSemesterIds": [], "defaultEventGroupIds": [], "savedLectureIds": [], "savedEventIds": []}'
```

**Flutter:**
```dart
final uid = FirebaseAuth.instance.currentUser!.uid;
final response = await http.put(
  Uri.parse('$baseUrl/api/v1/settings'),
  headers: {
    'Content-Type': 'application/json',
    'X-User-ID': uid,
  },
  body: jsonEncode({
    'notificationLeadMinutes': 15,
    'theme': 'dark',
    'defaultCourseOfStudyIds': ['INF S1+2'],
    'defaultSemesterIds': ['sem_3'],
    'defaultEventGroupIds': [],
    'savedLectureIds': [],
    'savedEventIds': [],
  }),
);
```

---

### `PATCH /settings`

Aktualisiert nur übergebene Felder.

**Request:**
```
PATCH /api/v1/settings
Content-Type: application/json
X-User-ID: <firebase-uid>
```
```json
{
  "theme": "dark",
  "notificationLeadMinutes": 30
}
```

**Response:**
```
200 OK
Content-Type: application/json
```
Vollständiges `UserSettings`-Objekt nach dem Update.

**cURL:**
```bash
curl -X PATCH "https://streetview.8xc.de/api/v1/settings" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: <firebase-uid>" \
  -d '{"theme": "dark"}'
```

**Flutter:**
```dart
final uid = FirebaseAuth.instance.currentUser!.uid;
final response = await http.patch(
  Uri.parse('$baseUrl/api/v1/settings'),
  headers: {
    'Content-Type': 'application/json',
    'X-User-ID': uid,
  },
  body: jsonEncode({'theme': 'dark'}),
);
```

---

## 8. Timetable

### `GET /timetable`

Gefilterte Vorlesungen + Events. Alle Parameter optional.

**Request:**
```
GET /api/v1/timetable?course=INF%20S1%2B2&semester=sem_3
Accept: application/json
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `course` | `string` | nein | Studiengang-IDs, kommagetrennt (z.B. `INF S1+2,INF S3+4`) |
| `semester` | `string` | nein | Semester-IDs, kommagetrennt (z.B. `sem_3,sem_4`) |
| `event_group` | `string` | nein | Event-Gruppen-IDs, kommagetrennt (z.B. `sports,career`) |
| `building` | `string` | nein | Gebäude-Kürzel, exakter Match (z.B. `G2`) |
| `room` | `string` | nein | Raum-Teilstring, case-insensitiv |
| `professor` | `string` | nein | Professor-Name, Teilstring, case-insensitiv |
| `date_from` | `string` | nein | Datum `YYYY-MM-DD` |
| `date_to` | `string` | nein | Datum `YYYY-MM-DD` (inklusiv) |
| `recurrence` | `string` | nein | `"weekly"` oder `"once"` |
| `public_only` | `bool` | nein | Nur öffentliche Events (default: `false`) |
| `limit_lectures` | `int` | nein | Max. Vorlesungen (default: `200`, max: `1000`) |
| `limit_events` | `int` | nein | Max. Events (default: `50`, max: `200`) |

**Response:**
```
200 OK
Content-Type: application/json
```
```json
{
  "lectures": [
    {
      "id": "abc123",
      "title": "Algorithmen und Datenstrukturen",
      "moduleId": "ADS",
      "courseOfStudyId": "INF S1+2",
      "semesterId": "sem_3",
      "room": "G2 2.01",
      "building": "G2",
      "professor": "Prof. Dr. Müller",
      "startTime": "2026-06-02T08:00:00+02:00",
      "endTime": "2026-06-02T09:30:00+02:00",
      "dayOfWeek": "Monday",
      "durationMinutes": 90,
      "recurrence": "weekly"
    }
  ],
  "events": [
    {
      "id": "evt456",
      "title": "Campusfest 2026",
      "groupId": "social",
      "color": "#f0b429",
      "startTime": "2026-06-15T14:00:00+02:00",
      "endTime": "2026-06-15T20:00:00+02:00",
      "is_public": true,
      "detail_url": "https://hs-aalen.de/events/campusfest",
      "image_url": "https://...",
      "building": "G2",
      "room": null,
      "description": "Jährliches Campusfest",
      "organizer": "Studentenwerk",
      "registration_url": null,
      "registration_deadline": null
    }
  ]
}
```

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/timetable?course=INF%20S1%2B2&date_from=2026-06-01"
```

**Flutter:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/timetable').replace(queryParameters: {
    'course': 'INF S1+2',
    'date_from': '2026-06-01',
    'date_to': '2026-06-30',
  }),
);
final data = jsonDecode(response.body);
final lectures = (data['lectures'] as List).cast<Map<String, dynamic>>();
final events   = (data['events']   as List).cast<Map<String, dynamic>>();
```

---

## 9. StreetView & Navigation

### Konzept

- **Nodes**: Standpunkte mit 360°-Panoramabild, verbunden über `exits`
- **Exits**: Gerichtete Verbindungen (`{"front": "node_b"}`) — Richtung aus Kameraperspektive
- **Routing**: Dijkstra über geografische Distanz, automatisch aus `pos_override`-Koordinaten

---

### `GET /streetview/graph/building/{building_id}`

**Request:**
```
GET /api/v1/streetview/graph/building/G2
Accept: application/json
```

**Response:**
```
200 OK
Content-Type: application/json
```
Vollständiges `StreetViewGraph`-Objekt (kann groß sein — cachen!).

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/streetview/graph/building/G2"
```

**Flutter:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/streetview/graph/building/G2'),
);
final graph = jsonDecode(response.body) as Map<String, dynamic>;
final nodes = (graph['nodes'] as List).cast<Map<String, dynamic>>();
```

---

### `GET /streetview/graph/building/{building_id}/map`

Navigationsgraph als **SVG-Bild**.

**Request:**
```
GET /api/v1/streetview/graph/building/G2/map?floor=2
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `floor` | `int` | nein | `-1`=UG · `0`=EG · `1`=1OG · `2`=2OG. Ohne Angabe: alle Etagen gestapelt |

**Response:**
```
200 OK
Content-Type: image/svg+xml
```

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/streetview/graph/building/G2/map?floor=2" \
  -o karte.svg
```

**Flutter:**
```dart
// Als SVG anzeigen (flutter_svg package)
SvgPicture.network(
  '$baseUrl/api/v1/streetview/graph/building/G2/map?floor=2',
  fit: BoxFit.contain,
)

// Oder manuell laden
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/streetview/graph/building/G2/map')
    .replace(queryParameters: {'floor': '2'}),
);
final svgString = response.body; // Content-Type: image/svg+xml
```

---

### `GET /streetview/route/building/{building_id}`

Dijkstra-Route als JSON-Schrittliste.

> `from_room` und `to_room` sind **Raum-IDs** (z.B. `G2 2.01`) — keine Node-IDs.

**Request:**
```
GET /api/v1/streetview/route/building/G2?to_room=G2%202.34&from_room=G2%202.01
Accept: application/json
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `to_room` | `string` | **ja** | Ziel-Raum-ID, z.B. `G2 2.34` |
| `from_room` | `string` | nein | Start-Raum-ID, z.B. `G2 2.01`. Standard: `startNode` des Graphen |

**Response:**
```
200 OK
Content-Type: application/json
```
```json
{
  "building_id": "G2",
  "to_room": "G2 2.34",
  "total_steps": 10,
  "steps": [
    {
      "node_id": "2_01_02",
      "image": "/api/v1/images/rooms/2_01_02/2_01_02.jpg",
      "building": "G2",
      "heading": 0.0,
      "direction": "front",
      "nearby_rooms": [
        { "room_id": "G2 2.01", "direction": null },
        { "room_id": "G2 2.02", "direction": null }
      ],
      "room_direction": null
    },
    {
      "node_id": "2_34",
      "image": "/api/v1/images/rooms/2_34/2_34.jpg",
      "building": "G2",
      "heading": 0.0,
      "direction": null,
      "nearby_rooms": [{ "room_id": "G2 2.34", "direction": "links" }],
      "room_direction": "links"
    }
  ]
}
```

**Felder:**

| Feld | Beschreibung |
|------|-------------|
| `steps[n].direction` | Exit-Richtung zum **nächsten** Node (`null` am Ziel) |
| `steps[last].room_direction` | Wo die Zieltür ist — nur am letzten Schritt |
| `steps[n].image` | Relativer Pfad → volles Bild: `{baseUrl}{image}` |
| `steps[n].heading` | Kamerawinkel beim Panorama-Laden (0–360°) |

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/streetview/route/building/G2?to_room=G2%202.34&from_room=G2%202.01"
```

**Flutter:**
```dart
final uri = Uri.parse('$baseUrl/api/v1/streetview/route/building/G2')
  .replace(queryParameters: {
    'to_room': 'G2 2.34',
    'from_room': 'G2 2.01',
  });

final response = await http.get(uri);
if (response.statusCode == 200) {
  final data = jsonDecode(response.body);
  final steps = (data['steps'] as List).cast<Map<String, dynamic>>();
  for (final step in steps) {
    final imageUrl = '$baseUrl${step['image']}';
    final direction = step['direction']; // null am Ziel
    final roomDir   = step['room_direction']; // nur letzter Schritt
  }
}
```

---

### `GET /streetview/route/building/{building_id}/map`

Route als **SVG-Visualisierung** (Pfad gold hervorgehoben).

**Request:**
```
GET /api/v1/streetview/route/building/G2/map?to_room=G2%202.34&from_room=G2%202.01
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `to_room` | `string` | **ja** | Ziel-Raum-ID |
| `from_room` | `string` | nein | Start-Raum-ID (Standard: `startNode`) |
| `floor` | `int` | nein | Etage. Standard: automatisch aus Zielraum |

**Response:**
```
200 OK
Content-Type: image/svg+xml
```

**Flutter:**
```dart
SvgPicture.network(
  Uri.parse('$baseUrl/api/v1/streetview/route/building/G2/map')
    .replace(queryParameters: {
      'to_room': 'G2 2.34',
      'from_room': 'G2 2.01',
    }).toString(),
)
```

---

### `GET /streetview/floorplan/{building_id}`

Roher Grundriss ohne Nodes.

**Response:** `image/svg+xml`

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/streetview/floorplan/G2" -o grundriss.svg
```

---

### `GET /streetview/floorplan/{building_id}/rooms`

Raumkoordinaten aus dem Grundriss. Key = Raum-Suffix ohne Gebäude-Prefix.

**Response:** `application/json`
```json
{
  "2.35": { "x": 412.5, "y": 543.0 },
  "2.36": { "x": 445.2, "y": 543.0 }
}
```

---

### `POST /streetview/graph`

Graph speichern / ersetzen (Upsert auf `building_id`).

**Request:**
```
POST /api/v1/streetview/graph
Content-Type: application/json
X-API-Key: <api-key>
```
```json
{
  "building_id": "G2",
  "graph": {
    "startNode": "2_01_02",
    "nodes": [
      {
        "id": "2_01_02",
        "image": "/api/v1/images/rooms/2_01_02/2_01_02.jpg",
        "building": "G2",
        "floor": 2,
        "node_type": "corridor",
        "heading": 0,
        "exits": { "front": "2_04" },
        "nearby_rooms": [
          { "room_id": "G2 2.01", "direction": null },
          { "room_id": "G2 2.02", "direction": null }
        ],
        "spots": [],
        "pos_override": { "x": 155.0, "y": 543.0 }
      }
    ]
  }
}
```

**Response:** `application/json`
```json
{ "id": "G2", "message": "Graph for building 'G2' saved successfully" }
```

---

### `PATCH /streetview/graph/building/{building_id}/node/{node_id}`

Einzelnen Node teilweise aktualisieren. Alle Felder optional.

**Request:**
```
PATCH /api/v1/streetview/graph/building/G2/node/2_01_02
Content-Type: application/json
X-API-Key: <api-key>
```
```json
{
  "heading": 90,
  "nearby_rooms": [
    { "room_id": "G2 2.01", "direction": "links" }
  ]
}
```

**Response:** `application/json`
```json
{ "message": "Node '2_01_02' updated in building 'G2'" }
```

---

### Verfügbare Räume für Routing (Gebäude G2)

```
G2 2.01  G2 2.02  G2 2.04  G2 2.05  G2 2.06  G2 2.07  G2 2.08
G2 2.09  G2 2.10  G2 2.11  G2 2.12  G2 2.13  G2 2.14  G2 2.15
G2 2.16  G2 2.17  G2 2.18  G2 2.19  G2 2.20  G2 2.21  G2 2.22
G2 2.23  G2 2.24  G2 2.25  G2 2.26  G2 2.28  G2 2.29  G2 2.30
G2 2.31  G2 2.32  G2 2.33  G2 2.34  G2 2.35  G2 2.36  G2 2.37
G2 2.38  G2 2.39  G2 2.40  G2 2.41
```

> `G2 2.03` und `G2 2.27` existieren nicht.

---

## 10. Buildings

### `GET /buildings`

**Request:**
```
GET /api/v1/buildings?campus=Main
Accept: application/json
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `campus` | `string` | nein | `"Main"` oder `"Burren"` |
| `skip` | `int` | nein | Pagination-Offset (default: `0`) |
| `limit` | `int` | nein | Max. Ergebnisse (default: `100`, max: `500`) |

**Response:** `application/json`
```json
[
  {
    "id": "64a1b2c3d4e5f6789abc1234",
    "code": "G2",
    "name": "Gebäude G2",
    "campus": "Main",
    "address": "Beethovenstr. 1, 73430 Aalen",
    "floors": [0, 1, 2],
    "street_view_enabled": true,
    "description": null,
    "room_count": 45,
    "last_scraped": "2026-06-01T06:00:00Z",
    "created_at": "2025-01-15T10:00:00Z"
  }
]
```

**cURL:**
```bash
curl "https://streetview.8xc.de/api/v1/buildings?campus=Main"
```

**Flutter:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/buildings')
    .replace(queryParameters: {'campus': 'Main'}),
);
final buildings = (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
```

---

## 11. Rooms

### `GET /rooms`

**Request:**
```
GET /api/v1/rooms?building=G2&floor=2
Accept: application/json
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `floor` | `int` | nein | Etage filtern |
| `search` | `string` | nein | Suche im Raumname, case-insensitiv |
| `building` | `string` | nein | Gebäude-Kürzel oder MongoDB-ID |
| `skip` | `int` | nein | Offset (default: `0`) |
| `limit` | `int` | nein | Max. Ergebnisse (default: `100`, max: `1000`) |

**Response:** `application/json`
```json
[
  {
    "id": "64a1b2c3d4e5f6789abc5678",
    "room_number": "G2 2.35",
    "floor": 2,
    "capacity": 30,
    "building": "G2",
    "building_id": "64a1b2c3d4e5f6789abc1234",
    "has_video": true,
    "has_projector": true,
    "street_view_enabled": true,
    "room_image_360": {
      "image_paths": ["2_35/2_35.jpg"],
      "latest_update": "2026-05-15T12:00:00Z",
      "url_prefix": "/api/v1/images/rooms"
    },
    "created_at": "2025-01-15T10:00:00Z"
  }
]
```

> **Bild-URL zusammensetzen:** `{baseUrl}{room_image_360.url_prefix}/{room_image_360.image_paths[0]}`  
> Beispiel: `https://streetview.8xc.de/api/v1/images/rooms/2_35/2_35.jpg`

**Flutter:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/rooms').replace(queryParameters: {
    'building': 'G2',
    'floor': '2',
  }),
);
final rooms = (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
```

---

## 12. Events

### `GET /events`

**Request:**
```
GET /api/v1/events?groupId=sports&date_from=2026-06-01
Accept: application/json
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `groupId` | `string` | nein | `sports` · `workshops` · `academic` · `culture` · `alumni` · `international` · `career` · `social` |
| `building` | `string` | nein | Gebäude-Kürzel, exakter Match |
| `date_from` | `string` | nein | Ab Datum (ISO 8601) |
| `date_to` | `string` | nein | Bis Datum (ISO 8601) |
| `public_only` | `bool` | nein | Nur öffentliche Events (default: `false`) |
| `skip` | `int` | nein | Offset (default: `0`) |
| `limit` | `int` | nein | Max. Ergebnisse (default: `50`, max: `200`) |

**Response:** `application/json`
```json
[
  {
    "id": "64a1b2c3d4e5f6789abcdef0",
    "title": "Campusfest 2026",
    "groupId": "social",
    "start_time": "2026-06-15T14:00:00+02:00",
    "end_time": "2026-06-15T20:00:00+02:00",
    "building": "G2",
    "room": null,
    "organizer": "Studentenwerk",
    "is_public": true,
    "image_url": "https://hs-aalen.de/images/campusfest.jpg",
    "detail_url": "https://hs-aalen.de/events/campusfest",
    "description": "Jährliches Campusfest mit Live-Musik",
    "registration_url": null,
    "registration_deadline": null,
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-15T08:00:00Z"
  }
]
```

---

### `POST /events`

**Request:**
```
POST /api/v1/events
Content-Type: application/json
X-API-Key: <api-key>
```
```json
{
  "title": "Workshop: Flutter Basics",
  "groupId": "workshops",
  "start_time": "2026-07-10T09:00:00+02:00",
  "end_time": "2026-07-10T17:00:00+02:00",
  "building": "G2",
  "room": "G2 2.01",
  "organizer": "Prof. Dr. Schmidt",
  "is_public": true,
  "image_url": null,
  "detail_url": "https://hs-aalen.de/events/flutter-workshop",
  "description": "Einführung in Flutter-Entwicklung",
  "registration_url": "https://hs-aalen.de/register/flutter",
  "registration_deadline": "2026-07-05"
}
```

**Pflichtfelder:** `title`, `start_time`, `end_time`

**Response:** `application/json`
```json
{ "id": "64a1b2c3d4e5f6789abcdef1" }
```

---

### `PUT /events/{event_id}`

Ersetzt ein Event vollständig.

**Request:**
```
PUT /api/v1/events/64a1b2c3d4e5f6789abcdef0
Content-Type: application/json
X-API-Key: <api-key>
```

Body: Gleiche Felder wie `POST`

**Response:** `application/json`
```json
{ "message": "Event updated successfully" }
```

---

### `DELETE /events/{event_id}`

**Request:**
```
DELETE /api/v1/events/64a1b2c3d4e5f6789abcdef0
X-API-Key: <api-key>
```

**Response:** `application/json`
```json
{ "message": "Event deleted successfully" }
```

---

## 13. Images

### `GET /images/rooms/{room_id}`

Alle Bilder für einen Raum.

> `room_id` = Node-ID mit Unterstrichen (z.B. `2_35`), nicht Raumnummer (`G2 2.35`)

**Request:**
```
GET /api/v1/images/rooms/2_35
Accept: application/json
```

**Response:** `application/json`
```json
{
  "room_id": "2_35",
  "images": [
    {
      "id": "64a1b2c3d4e5f6789abc9999",
      "room_id": "2_35",
      "image_filename": "2026-05-15-120000-panorama.jpg",
      "file_size_mb": 4.2,
      "image_type": "360_panoramic",
      "image_path": "/app/data/images/360/2_35/2026-05-15-120000-panorama.jpg",
      "uploaded_at": "2026-05-15T12:00:00Z",
      "image_url_api": "/api/v1/images/rooms/2_35/2026-05-15-120000-panorama.jpg"
    }
  ],
  "total_count": 1
}
```

> **Bild laden:** `{baseUrl}{image_url_api}` → `https://streetview.8xc.de/api/v1/images/rooms/2_35/2026-05-15-120000-panorama.jpg`

---

### `GET /images/rooms/{room_id}/latest`

Neuestes Bild für einen Raum.

**Response:** `application/json` — einzelnes `ImageResponse`-Objekt  
**404** wenn kein Bild vorhanden.

---

### `GET /images/rooms/{room_id}/{filename}`

Bild herunterladen, optional transformiert.

**Request:**
```
GET /api/v1/images/rooms/2_35/panorama.jpg?size=medium
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `size` | `string` | nein | `"original"` (default) · `"medium"` · `"thumbnail"` |
| `width` | `int` | nein | Zielbreite px (1–8192) |
| `height` | `int` | nein | Zielhöhe px (1–8192) |
| `crop` | `string` | nein | `"w,h"` (zentriert) oder `"x,y,w,h"`. Werte: px, `%`, oder `0.0–1.0` |

**Response:**
```
200 OK
Content-Type: image/jpeg   (oder image/png / image/webp)
Content-Length: <bytes>
```
Body: Binäre Bilddaten

**Beispiele:**
```bash
# Original
curl "https://streetview.8xc.de/api/v1/images/rooms/2_35/panorama.jpg" -o original.jpg

# Thumbnail
curl "https://streetview.8xc.de/api/v1/images/rooms/2_35/panorama.jpg?size=thumbnail" -o thumb.jpg

# Custom Größe
curl "https://streetview.8xc.de/api/v1/images/rooms/2_35/panorama.jpg?width=1920&height=960" -o resized.jpg

# Rechte Bildhälfte (crop: 50% bis Ende)
curl "https://streetview.8xc.de/api/v1/images/rooms/2_35/panorama.jpg?crop=50%25,0,50%25,100%25" -o right-half.jpg
```

**Flutter:**
```dart
// Einfach per NetworkImage / Image.network (empfohlen für Anzeige)
Image.network(
  '$baseUrl/api/v1/images/rooms/2_35/panorama.jpg?size=medium',
)

// Als Bytes laden (z.B. für 360°-Viewer)
final response = await http.get(
  Uri.parse('$baseUrl/api/v1/images/rooms/2_35/panorama.jpg'),
);
// response.bodyBytes = Uint8List mit JPEG-Daten
final imageBytes = response.bodyBytes;
```

---

### `HEAD /images/rooms/{room_id}/{filename}`

Prüft Existenz ohne Body zu laden.

**Request:**
```
HEAD /api/v1/images/rooms/2_35/panorama.jpg
```

**Response:**
```
200 OK
Content-Type: image/jpeg
Content-Length: 4398080
```
oder `404` wenn nicht vorhanden.

**Flutter:**
```dart
final response = await http.head(
  Uri.parse('$baseUrl/api/v1/images/rooms/2_35/panorama.jpg'),
);
final exists = response.statusCode == 200;
```

---

### `POST /images/rooms/{room_id}/upload`

Bild hochladen.

**Request:**
```
POST /api/v1/images/rooms/2_35/upload
Content-Type: multipart/form-data
X-API-Key: <api-key>
```

| Form-Feld | Typ | Beschreibung |
|-----------|-----|-------------|
| `file` | `File` | JPEG, PNG oder WEBP · max. **20 MB** |

**Response:** `application/json`
```json
{
  "message": "Image uploaded successfully",
  "filename": "2026-06-04-143000-panorama.jpg"
}
```

**cURL:**
```bash
curl -X POST "https://streetview.8xc.de/api/v1/images/rooms/2_35/upload" \
  -H "X-API-Key: <api-key>" \
  -F "file=@/pfad/zum/panorama.jpg"
```

**Flutter:**
```dart
final request = http.MultipartRequest(
  'POST',
  Uri.parse('$baseUrl/api/v1/images/rooms/2_35/upload'),
)
  ..headers['X-API-Key'] = apiKey
  ..files.add(await http.MultipartFile.fromPath(
    'file',
    '/pfad/zum/panorama.jpg',
    contentType: MediaType('image', 'jpeg'),
  ));

final streamedResponse = await request.send();
final response = await http.Response.fromStream(streamedResponse);
final result = jsonDecode(response.body);
final filename = result['filename'];
```

---

### `DELETE /images/rooms/{room_id}/{filename}`

**Request:**
```
DELETE /api/v1/images/rooms/2_35/2026-06-04-143000-panorama.jpg
X-API-Key: <api-key>
```

**Response:** `application/json`
```json
{ "message": "Image deleted successfully" }
```

---

## 14. Scheduler

### `GET /scheduler/status`

**Request:**
```
GET /api/v1/scheduler/status
Accept: application/json
```

**Response:** `application/json`
```json
{
  "status": "success",
  "schedule": "Täglich um 06:00 Uhr (Europe/Berlin)",
  "last_run": {
    "id": "64a1b2c3d4e5f6789abc0001",
    "status": "success",
    "started_at": "2026-06-04T06:00:00Z",
    "completed_at": "2026-06-04T06:08:32Z",
    "rooms_processed": 312,
    "courses_processed": 18,
    "lectures_total": 4521,
    "buildings_upserted": 12,
    "error": null
  },
  "total_runs": 142,
  "failed_runs": 3,
  "error": null
}
```

**Status-Werte:** `"success"` · `"failed"` · `"running"` · `"never_run"` · `"error"`

---

### `GET /scheduler/logs`

**Request:**
```
GET /api/v1/scheduler/logs?limit=10&status=failed
Accept: application/json
```

**Query-Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|-------------|
| `limit` | `int` | nein | Max. Einträge (default: `20`, max: `100`) |
| `status` | `string` | nein | `"success"` · `"failed"` · `"running"` |

**Response:** `application/json`
```json
{
  "logs": [
    {
      "id": "64a1b2c3d4e5f6789abc0001",
      "status": "success",
      "started_at": "2026-06-04T06:00:00Z",
      "completed_at": "2026-06-04T06:08:32Z",
      "rooms_processed": 312,
      "courses_processed": 18,
      "lectures_total": 4521,
      "buildings_upserted": 12,
      "error": null
    }
  ],
  "total": 142,
  "limit": 10,
  "error": null
}
```

---

### `POST /scheduler/trigger`

Scraper manuell starten. Gibt sofort zurück — Fortschritt über `GET /scheduler/status`.

**Request:**
```
POST /api/v1/scheduler/trigger
X-API-Key: <api-key>
```

**Response:** `application/json`
```json
{
  "message": "Scraper job triggered successfully",
  "status": "triggered"
}
```

---

## 15. Datenmodelle

### `UserResponse`

Response von `POST /api/v1/users`.

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `created_at` | `string` | ISO-8601-Timestamp der Registrierung |

---

### `StreetViewGraph`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `startNode` | `string` | ID des Standard-Startknotens |
| `nodes` | `StreetViewNode[]` | Alle Navigationspunkte |

---

### `StreetViewNode`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | `string` | Eindeutige Node-ID (z.B. `"2_01_02"`) |
| `image` | `string` | Relativer Pfad zum Panoramabild → volles Bild: `{baseUrl}{image}` |
| `building` | `string \| null` | Gebäude-Kürzel (z.B. `"G2"`) |
| `floor` | `int \| null` | `-1`=UG · `0`=EG · `1`=1OG · `2`=2OG |
| `node_type` | `string` | `"corridor"` · `"entrance"` · `"staircase"` · `"elevator"` |
| `heading` | `float` | Kameraausrichtung beim Laden in Grad (0–360) |
| `exits` | `dict[string → string]` | Richtung → Ziel-Node-ID, z.B. `{"front": "2_04", "left": "2_08"}` |
| `nearby_rooms` | `RoomAccess[]` | Räume an diesem Standpunkt |
| `spots` | `StreetViewSpot[]` | Interaktive Panorama-Punkte |
| `pos_override` | `{x: float, y: float} \| null` | Manuelle Floorplan-Position (vom Editor, nicht für App relevant) |

**Exit-Richtungen:** `"front"` · `"back"` · `"left"` · `"right"` · `"up"` · `"down"`

---

### `RoomAccess`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `room_id` | `string` | Raum-ID (z.B. `"G2 2.35"`) |
| `direction` | `string \| null` | Richtung zur Tür aus Kameraperspektive (z.B. `"links"`, `"rechts"`, `"geradeaus"`) |

---

### `StreetViewSpot`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `name` | `string` | Name des Spots |
| `longitude` | `float` | Longitude im Panorama (0–360) |
| `latitude` | `float` | Latitude im Panorama (-90 bis 90) |
| `description` | `string \| null` | Optionale Beschreibung |

---

### `StreetViewNodeUpdate` (nur für PATCH)

Alle Felder optional:

| Feld | Typ |
|------|-----|
| `image` | `string \| null` |
| `building` | `string \| null` |
| `floor` | `int \| null` |
| `node_type` | `"corridor" \| "entrance" \| "staircase" \| "elevator" \| null` |
| `heading` | `float \| null` |
| `exits` | `dict[string → string] \| null` |
| `nearby_rooms` | `RoomAccess[] \| null` |
| `spots` | `StreetViewSpot[] \| null` |
| `pos_override` | `{x: float, y: float} \| null` |

---

### `RouteStep`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `node_id` | `string` | Node-ID |
| `image` | `string \| null` | Relativer Pfad → `{baseUrl}{image}` |
| `building` | `string \| null` | Gebäude-Kürzel |
| `heading` | `float` | Kamerawinkel (0–360°) |
| `direction` | `string \| null` | Exit nehmen → zum nächsten Node (`null` am Ziel) |
| `nearby_rooms` | `RoomAccess[]` | Räume an diesem Node |
| `room_direction` | `string \| null` | Wo die Zieltür ist — **nur am letzten Schritt** |

---

### `AppConfig` (Settings-Response)

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `notificationLeadMinutes` | `int` | Vorlaufzeit Benachrichtigungen (default: `15`) |
| `defaultCourseOfStudyIds` | `string[]` | Vorausgewählte Studiengänge |
| `defaultSemesterIds` | `string[]` | Vorausgewählte Semester |
| `defaultEventGroupIds` | `string[]` | Vorausgewählte Event-Gruppen |
| `savedLectureIds` | `string[]` | Gemerkte Vorlesungen |
| `savedEventIds` | `string[]` | Gemerkte Events |
| `theme` | `string` | `"light"` · `"dark"` · `"system"` |
| `courses_of_study` | `{id, label, color}[]` | Alle Studiengänge mit Farbe |
| `semesters` | `{id, label}[]` | Alle Semester |
| `event_groups` | `{id, label, color}[]` | Alle Event-Gruppen mit Farbe |

---

### `BuildingResponse`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | `string` | MongoDB ObjectId |
| `code` | `string` | Kürzel (z.B. `"G2"`) |
| `name` | `string` | Vollständiger Name |
| `campus` | `string` | `"Main"` oder `"Burren"` |
| `address` | `string \| null` | Anschrift |
| `floors` | `int[]` | Verfügbare Etagen (z.B. `[0, 1, 2]`) |
| `street_view_enabled` | `bool` | Hat 360°-Panoramas |
| `description` | `string \| null` | Optionale Beschreibung |
| `room_count` | `int` | Anzahl Räume |
| `last_scraped` | `datetime \| null` | Letzter Scraper-Lauf |
| `created_at` | `datetime \| null` | Erstellungsdatum |

---

### `RoomResponse`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | `string` | MongoDB ObjectId |
| `room_number` | `string` | Raumnummer (z.B. `"G2 2.35"`) |
| `floor` | `int \| null` | Etage |
| `capacity` | `int \| null` | Sitzplätze |
| `building` | `string \| null` | Gebäude-Kürzel |
| `building_id` | `string \| null` | MongoDB ObjectId des Gebäudes |
| `has_video` | `bool` | Videoanlage |
| `has_projector` | `bool` | Beamer |
| `street_view_enabled` | `bool` | Hat 360°-Panorama |
| `room_image_360` | `{image_paths: string[], latest_update: datetime, url_prefix: string} \| null` | 360°-Bild-Info |
| `created_at` | `datetime \| null` | Erstellungsdatum |

---

### `EventResponse`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | `string` | MongoDB ObjectId |
| `title` | `string` | Titel |
| `groupId` | `string \| null` | Event-Gruppe |
| `start_time` | `datetime \| null` | Startzeit (ISO 8601 mit Timezone, z.B. `2026-06-15T14:00:00+02:00`) |
| `end_time` | `datetime \| null` | Endzeit |
| `building` | `string \| null` | Gebäude-Kürzel |
| `room` | `string \| null` | Raumnummer |
| `organizer` | `string \| null` | Veranstalter |
| `is_public` | `bool` | Ohne Login sichtbar |
| `image_url` | `string \| null` | Externe Bild-URL |
| `detail_url` | `string \| null` | Detail-Seite |
| `description` | `string \| null` | Beschreibung |
| `registration_url` | `string \| null` | Anmeldelink |
| `registration_deadline` | `string \| null` | Anmeldeschluss |
| `created_at` | `datetime \| null` | Erstellungsdatum |
| `updated_at` | `datetime \| null` | Letztes Update |

---

## 16. Schnellreferenz aller Endpoints

| Method | Endpoint | Auth | Request `Content-Type` | Response `Content-Type` |
|--------|----------|:----:|------------------------|------------------------|
| `POST` | `/users` | `X-User-ID` | — | `application/json` |
| `GET` | `/settings` | `X-User-ID` ¹ | — | `application/json` |
| `PUT` | `/settings` | `X-User-ID` ¹ | `application/json` | `application/json` |
| `PATCH` | `/settings` | `X-User-ID` ¹ | `application/json` | `application/json` |
| `GET` | `/timetable` | — | — | `application/json` |
| `GET` | `/streetview/graph` | — | — | `application/json` |
| `GET` | `/streetview/graph/building/{id}` | — | — | `application/json` |
| `POST` | `/streetview/graph` | `X-API-Key` | `application/json` | `application/json` |
| `PATCH` | `/streetview/graph/building/{id}/node/{nid}` | `X-API-Key` | `application/json` | `application/json` |
| `GET` | `/streetview/graph/building/{id}/map[?floor=]` | — | — | `image/svg+xml` |
| `GET` | `/streetview/floorplan/{id}` | — | — | `image/svg+xml` |
| `GET` | `/streetview/floorplan/{id}/rooms` | — | — | `application/json` |
| `GET` | `/streetview/route/building/{id}?to_room=&from_room=` | — | — | `application/json` |
| `GET` | `/streetview/route/building/{id}/map?to_room=&from_room=` | — | — | `image/svg+xml` |
| `GET` | `/buildings` | — | — | `application/json` |
| `GET` | `/rooms` | — | — | `application/json` |
| `GET` | `/events` | — | — | `application/json` |
| `POST` | `/events` | `X-API-Key` | `application/json` | `application/json` |
| `PUT` | `/events/{id}` | `X-API-Key` | `application/json` | `application/json` |
| `DELETE` | `/events/{id}` | `X-API-Key` | — | `application/json` |
| `GET` | `/images/rooms/{id}` | — | — | `application/json` |
| `GET` | `/images/rooms/{id}/latest` | — | — | `application/json` |
| `GET` | `/images/rooms/{id}/{filename}[?size=&width=&height=&crop=]` | — | — | `image/jpeg` |
| `HEAD` | `/images/rooms/{id}/{filename}` | — | — | *(kein Body)* |
| `POST` | `/images/rooms/{id}/upload` | `X-API-Key` | `multipart/form-data` | `application/json` |
| `DELETE` | `/images/rooms/{id}/{filename}` | `X-API-Key` | — | `application/json` |
| `GET` | `/scheduler/status` | — | — | `application/json` |
| `GET` | `/scheduler/logs` | — | — | `application/json` |
| `POST` | `/scheduler/trigger` | `X-API-Key` | — | `application/json` |

> ¹ `X-User-ID` muss zuerst über `POST /users` registriert worden sein — sonst `401`.
