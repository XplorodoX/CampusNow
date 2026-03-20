# CampusNow - System Architektur Diagramm

```mermaid
graph TB
    subgraph "Client"
        Flutter["📱 Flutter App<br/>(Android + iOS)"]
    end
    
    subgraph "Docker Network"
        subgraph "Scraper Service"
            Scraper["🔄 Scraper Service<br/>(Python)<br/>- Sammelt iCal Links<br/>- Parsed Vorlesungen<br/>- Aktualisiert täglich morgens"]
        end
        
        subgraph "API Service"
            API["🔌 REST API Service<br/>(Python FastAPI)<br/>- Swagger Dokumentation<br/>- Endpoints für<br/>  Stundenplan/Räume/Bilder"]
        end
        
        subgraph "Data Storage"
            MongoDB["🗄️ MongoDB<br/>- Vorlesungen<br/>- Räume<br/>- Studiengänge<br/>- Metadaten"]
            FileSystem["💾 Image Storage<br/>/data/images/360/"]
        end
    end
    
    Flutter -->|REST API Calls| API
    API -->|Query/Insert| MongoDB
    API -->|Read/Write| FileSystem
    Scraper -->|Parse + Insert| MongoDB
    Scraper -->|Download + Store| FileSystem

    style Flutter fill:#4CAF50,color:#fff
    style Scraper fill:#2196F3,color:#fff
    style API fill:#2196F3,color:#fff
    style MongoDB fill:#13AA52,color:#fff
    style FileSystem fill:#FF9800,color:#fff
```

## System-Flow

1. **Täglich morgens (6:00 Uhr)**:
   - Scraper-Service startet
   - Feldt HS-Aalen Starplan Website nach iCal-Links
   - Ladet und parsed iCal-Dateien
   - Downloaded neue 360°-Bilder der Räume
   - Speichert alles in MongoDB + Dateisystem

2. **Flutter App**:
   - Ruft REST-API bei Bedarf ab
   - Zeigt Stundenplan nach Raum/Studiengang
   - lädt 360°-Bilder für Street-View

3. **REST-API**:
   - Liefert Echtzeit-Daten aus MongoDB
   - Serviert Bilder mit verschiedenen Größen
   - Automatisch dokumentiert mit Swagger
