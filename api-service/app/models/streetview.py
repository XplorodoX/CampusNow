from pydantic import BaseModel, Field


class StreetViewSpot(BaseModel):
    name: str
    longitude: float
    latitude: float
    description: str | None = None


class StreetViewNode(BaseModel):
    id: str
    image: str = Field(..., description="Pfad oder URL zum 360°-Bild")
    building: str | None = None
    room: str | None = None
    heading: float = Field(0, description="Startausrichtung der Kamera in Grad")
    exits: dict[str, str] = Field(
        default_factory=dict,
        description="Navigierbare Ausgänge: Richtung → Node-ID (z. B. {'front': 'node1'})",
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
