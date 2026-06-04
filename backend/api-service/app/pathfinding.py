"""Dijkstra-based pathfinding for StreetView navigation graphs.

Edge weights are the Euclidean distance between node positions (from pos_override).
If a node has no position, a default penalty is used so the algorithm still works
but prefers positioned nodes.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Any

_DEFAULT_EDGE_COST = 100.0  # fallback wenn pos_override fehlt


@dataclass(order=True)
class _State:
    cost: float
    node_id: str = field(compare=False)
    prev_node_id: str | None = field(compare=False)
    direction: str | None = field(compare=False)


def _pos(node: dict) -> tuple[float, float] | None:
    po = node.get("pos_override")
    if po and po.get("x") is not None and po.get("y") is not None:
        return float(po["x"]), float(po["y"])
    return None


def _edge_cost(a: dict, b: dict) -> float:
    """Euklidische Distanz zwischen zwei Nodes, automatisch aus pos_override."""
    pa, pb = _pos(a), _pos(b)
    if pa and pb:
        return math.sqrt((pb[0] - pa[0]) ** 2 + (pb[1] - pa[1]) ** 2)
    return _DEFAULT_EDGE_COST


def _node_has_room(node: dict, target_room: str) -> bool:
    return any(r.get("room_id") == target_room for r in node.get("nearby_rooms", []))


def _room_direction(node: dict, target_room: str) -> str | None:
    for r in node.get("nearby_rooms", []):
        if r.get("room_id") == target_room:
            return r.get("direction")
    return None


def find_route(
    graph: dict[str, Any],
    target_room: str,
    start_node_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """Kürzester Weg (geografische Distanz) zum Node mit Zugang zu target_room.

    Gewichtung: Euklidische Distanz zwischen Node-Positionen (pos_override).
    Keine manuelle Angabe nötig – wird automatisch berechnet.
    """
    nodes_by_id: dict[str, dict] = {n["id"]: n for n in graph.get("nodes", [])}
    start = start_node_id or graph.get("startNode")

    if not start or start not in nodes_by_id:
        return None

    heap: list[_State] = [_State(0.0, start, None, None)]
    visited: dict[str, tuple[str | None, str | None]] = {}

    while heap:
        state = heapq.heappop(heap)
        nid, cost = state.node_id, state.cost

        if nid in visited:
            continue
        visited[nid] = (state.prev_node_id, state.direction)

        node = nodes_by_id[nid]
        if _node_has_room(node, target_room):
            return _reconstruct(visited, nodes_by_id, nid, target_room)

        for direction, neighbor_id in node.get("exits", {}).items():
            if neighbor_id not in visited and neighbor_id in nodes_by_id:
                neighbor = nodes_by_id[neighbor_id]
                weight = _edge_cost(node, neighbor)
                heapq.heappush(heap, _State(cost + weight, neighbor_id, nid, direction))

    return None


def _reconstruct(
    visited: dict[str, tuple[str | None, str | None]],
    nodes_by_id: dict[str, dict],
    target_id: str,
    target_room: str,
) -> list[dict[str, Any]]:
    path: list[str] = []
    current = target_id
    while current is not None:
        path.append(current)
        prev, _ = visited[current]
        current = prev
    path.reverse()

    steps = []
    for i, nid in enumerate(path):
        node = nodes_by_id[nid]
        is_dest = i == len(path) - 1

        if not is_dest:
            _, direction = visited[path[i + 1]]
        else:
            direction = None

        steps.append({
            "node_id": nid,
            "image": node.get("image"),
            "building": node.get("building"),
            "heading": node.get("heading", 0),
            "direction": direction,
            "nearby_rooms": node.get("nearby_rooms", []),
            "room_direction": _room_direction(node, target_room) if is_dest else None,
        })

    return steps
