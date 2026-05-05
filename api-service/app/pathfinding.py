"""Dijkstra-based pathfinding for StreetView navigation graphs."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class _State:
    cost: int
    node_id: str = field(compare=False)
    prev_node_id: str | None = field(compare=False)
    direction: str | None = field(compare=False)


def _node_has_room(node: dict, target_room: str) -> bool:
    """True if this node provides access to target_room."""
    for r in node.get("nearby_rooms", []):
        if r.get("room_id") == target_room:
            return True
    return False


def _room_direction(node: dict, target_room: str) -> str | None:
    """Return the door direction for target_room at this node, or None."""
    for r in node.get("nearby_rooms", []):
        if r.get("room_id") == target_room:
            return r.get("direction")
    return None


def find_route(
    graph: dict[str, Any],
    target_room: str,
    start_node_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """Compute shortest path to the node that has access to target_room.

    Args:
        graph: Raw graph dict with keys 'startNode' and 'nodes'.
        target_room: Room ID to navigate to (must appear in a node's nearby_rooms).
        start_node_id: Starting node ID. Defaults to graph['startNode'].

    Returns:
        Ordered list of step dicts, or None if no path exists.
        Each step: {node_id, image, building, heading, direction, nearby_rooms, room_direction}
        - direction: exit label taken FROM this node to reach the next one (None at destination)
        - room_direction: how to find the target room door at the destination node
    """
    nodes_by_id: dict[str, dict] = {n["id"]: n for n in graph.get("nodes", [])}
    start = start_node_id or graph.get("startNode")

    if not start or start not in nodes_by_id:
        return None

    heap: list[_State] = [_State(0, start, None, None)]
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
                heapq.heappush(heap, _State(cost + 1, neighbor_id, nid, direction))

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

        # Direction taken FROM this node to reach the next
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
            # Only set at the destination node
            "room_direction": _room_direction(node, target_room) if is_dest else None,
        })

    return steps
