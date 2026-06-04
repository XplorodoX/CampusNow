from typing import Literal

from pydantic import BaseModel, Field

NodeType = Literal["corridor", "entrance", "staircase", "elevator"]


class StreetViewSpot(BaseModel):
    name: str
    longitude: float
    latitude: float
    description: str | None = None


class RoomAccess(BaseModel):
    """Ein Raum der von dieser Gang-Position aus zugänglich ist."""
    room_id: str = Field(..., description="Raum-ID, z. B. 'G2 0.01'")
    direction: str | None = Field(
        None,
        description="Richtung zur Tür aus Sicht der Kamera, z. B. 'links', 'rechts', 'geradeaus'",
    )


class StreetViewNode(BaseModel):
    id: str
    image: str = Field(..., description="Pfad oder URL zum 360°-Panoramabild")
    building: str | None = None
    floor: int | None = Field(None, description="Stockwerk des Nodes (0=EG, 1=1OG, 2=2OG)")
    node_type: NodeType = Field("corridor", description="corridor | entrance | staircase | elevator")
    heading: float = Field(0, description="Startausrichtung der Kamera in Grad (0–360°)")
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
    pos_override: dict | None = Field(
        None,
        description="Manuelle Floorplan-Position {x, y} – gesetzt vom Editor per Drag & Drop",
    )


class StreetViewNodeUpdate(BaseModel):
    """Partial update für einen einzelnen Node – nur gesetzte Felder werden überschrieben."""
    image: str | None = None
    building: str | None = None
    floor: int | None = None
    node_type: NodeType | None = None
    heading: float | None = None
    exits: dict[str, str] | None = None
    nearby_rooms: list[RoomAccess] | None = None
    spots: list[StreetViewSpot] | None = None
    pos_override: dict | None = None


class StreetViewGraph(BaseModel):
    startNode: str = Field(..., description="ID des Startknotens")
    nodes: list[StreetViewNode]


class StreetViewGraphCreate(BaseModel):
    """Zum Anlegen oder vollständigen Ersetzen eines Graphen für einen Raum/Bereich."""
    room_id: str | None = Field(None, description="Raum-ID dem dieser Graph gehört")
    building_id: str | None = Field(None, description="Gebäude-ID dem dieser Graph gehört")
    graph: StreetViewGraph
