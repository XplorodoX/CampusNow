from pydantic import BaseModel, Field


class StreetViewSpot(BaseModel):
    name: str
    longitude: float
    latitude: float
    description: str | None = None


class RoomAccess(BaseModel):
    """Ein Raum der von dieser Gang-Position aus zugänglich ist."""
    room_id: str = Field(..., description="Raum-ID, z. B. 'G2-0.01'")
    direction: str | None = Field(
        None,
        description="Richtung zur Tür aus Sicht der Kamera, z. B. 'links', 'rechts', 'geradeaus', 'Tür'",
    )


class StreetViewNode(BaseModel):
    id: str
    image: str = Field(..., description="Pfad oder URL zum 360°-Panoramabild")
    building: str | None = None
    heading: float = Field(0, description="Startausrichtung der Kamera in Grad")
    exits: dict[str, str] = Field(
        default_factory=dict,
        description="Navigierbare Ausgänge: Richtung → Node-ID (z. B. {'front': 'node1'})",
    )
    nearby_rooms: list[RoomAccess] = Field(
        default_factory=list,
        description="Räume die von dieser Position aus erreichbar sind, mit Richtungsangabe",
    )
    spots: list[StreetViewSpot] = Field(
        default_factory=list,
        description="Interaktive Punkte im Panorama",
    )


class StreetViewGraph(BaseModel):
    startNode: str = Field(..., description="ID des Startknotens")
    nodes: list[StreetViewNode]


class StreetViewGraphCreate(BaseModel):
    """Zum Anlegen oder vollständigen Ersetzen eines Graphen für einen Raum/Bereich."""
    room_id: str | None = Field(None, description="Raum-ID dem dieser Graph gehört")
    building_id: str | None = Field(None, description="Gebäude-ID dem dieser Graph gehört")
    graph: StreetViewGraph
