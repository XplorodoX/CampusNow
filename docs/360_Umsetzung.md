Plan: 360°-Bilder für G2 aufnehmen, speichern & navigierbar machen
Das System kurz erklärt
Das Backend kennt bereits Nodes (Knotenpunkte). Jeder Node ist:

eine 360°-Fotoposition im Gebäude
verknüpft mit bis zu 4 Ausgängen (exits: front / back / left / right → nächster Node)
verknüpft mit Räumen in der Nähe (nearby_rooms: room_id + Richtung zur Tür)
Der Dijkstra-Algorithmus findet den kürzesten Weg durch diese Nodes zu einem Zielraum. Das Frontend zeigt das Panorama, der Nutzer drückt auf einem D-Pad eine Richtung, und der nächste Node wird geladen.

1. Wo Fotos machen (Node-Placement-Strategie)
Nicht jeder Raum braucht ein eigenes Foto. Die Kamera steht im Gang, nicht im Raum.


Typ         Wann ein Node                        Wie viele
──────────  ───────────────────────────────────  ─────────
Eingang     Jeder Gebäudeeingang                 1-2 pro Gebäude
Gang-Knoten Jede Kreuzung / T-Abzweigung         1 pro Junction
Treppenhaus Jedes Treppenhaus, pro Etage 1       3 (EG/1OG/2OG)
Sackgasse   Langes Korridor-Ende mit Räumen      1 extra Node
Faustregel: Wenn man von einem Punkt in 2+ Richtungen abbiegen kann, ist es ein Node. Lange, gerade Gänge mit Räumen auf beiden Seiten brauchen einen Node alle ~20m.

Für G2 ca. 20–35 Nodes (nicht 105 — Rooms und Nodes sind verschiedene Dinge).

2. Naming Convention (Dateiname = Node-ID)

G2-EG-E01      Eingang EG, Node 01
G2-EG-G01      Gang EG, Knotenpunkt 01
G2-EG-G02      Gang EG, Knotenpunkt 02
G2-EG-T01      Treppenhaus EG (verbindet zu G2-1OG-T01)
G2-1OG-G01     Gang 1.OG, Knotenpunkt 01
G2-1OG-T01     Treppenhaus 1.OG
G2-2OG-G01     ...
Das Node-ID wird gleichzeitig:

Ordnername auf dem Server: /data/images/360/G2-EG-G01/
Bild-URL in der API: /api/v1/images/rooms/G2-EG-G01/latest
Referenz im Graph JSON
3. Wie die Bilder gespeichert werden
Dateistruktur (Docker Volume)

data/images/360/
  G2-EG-E01/
    panorama.jpg          ← Upload via API
  G2-EG-G01/
    panorama.jpg
  G2-EG-T01/
    panorama.jpg
  G2-1OG-G01/
    panorama.jpg
  ...
Datenbank (MongoDB image_metadata)
Ein Dokument pro Bild — wird automatisch beim Upload angelegt:


{
  "room_id": "G2-EG-G01",
  "image_filename": "2025-05-07-120000-panorama.jpg",
  "image_type": "360_panoramic",
  "image_url_api": "/api/v1/images/rooms/G2-EG-G01/latest"
}
Upload-Befehl (einmalig pro Node)

curl -X POST /api/v1/images/rooms/G2-EG-G01/upload \
  -H "X-API-Key: DEIN_KEY" \
  -F "file=@G2-EG-G01.jpg"
4. Der Graph (MongoDB streetview_graphs)
Ein einziges Dokument für das gesamte Gebäude G2:


{
  "building_id": "G2",
  "graph": {
    "startNode": "G2-EG-E01",
    "nodes": [
      {
        "id": "G2-EG-E01",
        "image": "/api/v1/images/rooms/G2-EG-E01/latest",
        "building": "G2",
        "floor": 0,
        "heading": 0,
        "exits": {
          "front": "G2-EG-G01"
        },
        "nearby_rooms": [],
        "spots": []
      },
      {
        "id": "G2-EG-G01",
        "image": "/api/v1/images/rooms/G2-EG-G01/latest",
        "building": "G2",
        "floor": 0,
        "heading": 90,
        "exits": {
          "front": "G2-EG-G02",
          "left": "G2-EG-T01",
          "back": "G2-EG-E01"
        },
        "nearby_rooms": [
          { "room_id": "G2 0.01", "direction": "rechts" },
          { "room_id": "G2 0.03", "direction": "rechts" }
        ],
        "spots": [
          {
            "name": "Raum G2 0.01",
            "longitude": 270,
            "latitude": 0,
            "description": "Tür zu G2 0.01"
          }
        ]
      },
      {
        "id": "G2-EG-T01",
        "image": "/api/v1/images/rooms/G2-EG-T01/latest",
        "building": "G2",
        "floor": 0,
        "heading": 0,
        "exits": {
          "front": "G2-1OG-T01",
          "back": "G2-EG-G01"
        },
        "nearby_rooms": [],
        "spots": []
      }
    ]
  }
}
Schlüsselprinzipien:

exits verbindet Nodes horizontal (Gang) und vertikal (Treppe: "front" = rauf)
nearby_rooms sagt "von hier ist Raum X erreichbar, Tür ist rechts/links/geradeaus"
spots sind anklickbare Pins im Panorama (Longitude 0-360°, Latitude -90 bis +90°)
heading ist der Blickwinkel wenn der Node geladen wird (0° = Norden/Vorne)
5. Was in der API noch fehlt / gebaut werden muss
Aktuell vorhanden ✓
POST /api/v1/images/rooms/{node_id}/upload — Bild hochladen
GET /api/v1/images/rooms/{node_id}/latest — Bild abrufen
POST /api/v1/streetview/graph — kompletten Graph speichern
GET /api/v1/streetview/graph/building/G2 — Graph abrufen
GET /api/v1/streetview/route/building/G2?to_room=G2 0.21 — Dijkstra
Fehlt noch ✗
Endpoint	Wozu
PATCH /api/v1/streetview/graph/building/{id}/node/{node_id}	Einzelnen Node updaten ohne den ganzen Graph zu ersetzen (wichtig wenn man nach und nach Fotos macht)
GET /api/v1/streetview/graph/building/{id}?floor=0	Graph nach Etage filtern (für Etagen-Karte im Frontend)
POST /api/v1/images/nodes/bulk-upload	Mehrere Panoramen auf einmal hochladen
field: floor auf StreetViewNode	Etage am Node speichern (0/1/2), damit das Frontend weiß wo man ist
field: node_type auf StreetViewNode	"corridor" | "entrance" | "staircase" für UI-Anzeige
Modell-Erweiterung (klein aber wichtig)
StreetViewNode braucht zwei neue Felder:


floor: int | None = Field(None, description="Stockwerk des Nodes (0=EG, 1=1OG, ...)")
node_type: str = Field("corridor", description="corridor | entrance | staircase | elevator")
6. Praktischer Workflow in der echten Welt

1. VORBEREITUNG
   ─ Grundriss ausdrucken (docs/Floorplan-G2.svg)
   ─ Potentielle Node-Positionen mit X markieren
   ─ Jeden Node benennen (G2-EG-G01, G2-EG-G02, ...)

2. FOTOGRAFIEREN (Etage für Etage)
   ─ 360°-Kamera auf ~1.5m Höhe
   ─ Kamera zeigt Richtung "front" (Laufrichtung = 0°)
   ─ Für jede Position: Foto + auf Papier notieren:
       • Von wo kommt man hin (back)
       • Wohin führt front/left/right
       • Welche Türen sind sichtbar (→ nearby_rooms)
       • Heading: wo zeigt die Kamera hin

3. UPLOAD
   ─ Für jeden Node: curl POST /api/v1/images/rooms/G2-EG-G01/upload
   ─ Oder kleines Upload-Script das einen Ordner einliest

4. GRAPH BAUEN
   ─ graph_G2.json Datei befüllen (Vorlage aus Schritt oben)
   ─ Jeden Node eintragen mit exits + nearby_rooms

5. GRAPH PUSHEN
   ─ curl POST /api/v1/streetview/graph mit building_id: "G2"

6. TESTEN
   ─ GET /api/v1/streetview/route/building/G2?to_room=G2 0.21
   ─ Prüfen ob Dijkstra sinnvoll navigiert