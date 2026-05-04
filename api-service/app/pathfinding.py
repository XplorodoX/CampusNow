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


def find_route(
    graph: dict[str, Any],
    target_room: str,
    start_node_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """Compute shortest path from start_node to any node with room == target_room.

    Args:
        graph: The raw graph dict with keys 'startNode' and 'nodes'.
        target_room: The room identifier to navigate to.
        start_node_id: Starting node ID. Defaults to graph['startNode'].

    Returns:
        Ordered list of step dicts, or None if no path exists.
        Each step: {node_id, image, building, room, heading, direction}
        'direction' is the exit label taken FROM this node to reach the next one,
        or None for the final destination node.
    """
    nodes_by_id: dict[str, dict] = {n["id"]: n for n in graph.get("nodes", [])}
    start = start_node_id or graph.get("startNode")

    if not start or start not in nodes_by_id:
        return None

    # Dijkstra — all edges have weight 1
    heap: list[_State] = [_State(0, start, None, None)]
    # visited: node_id → (prev_node_id, direction_taken_to_get_here)
    visited: dict[str, tuple[str | None, str | None]] = {}

    while heap:
        state = heapq.heappop(heap)
        nid, cost = state.node_id, state.cost

        if nid in visited:
            continue
        visited[nid] = (state.prev_node_id, state.direction)

        node = nodes_by_id[nid]
        if node.get("room") == target_room:
            return _reconstruct(visited, nodes_by_id, nid)

        for direction, neighbor_id in node.get("exits", {}).items():
            if neighbor_id not in visited and neighbor_id in nodes_by_id:
                heapq.heappush(heap, _State(cost + 1, neighbor_id, nid, direction))

    return None


def _reconstruct(
    visited: dict[str, tuple[str | None, str | None]],
    nodes_by_id: dict[str, dict],
    target_id: str,
) -> list[dict[str, Any]]:
    """Walk backwards through visited map to build the ordered step list."""
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
        # The direction shown on a step is the exit taken *from* this node
        # to reach the next — stored in visited[next_node].direction
        if i + 1 < len(path):
            next_nid = path[i + 1]
            _, direction = visited[next_nid]
        else:
            direction = None

        steps.append({
            "node_id": nid,
            "image": node.get("image"),
            "building": node.get("building"),
            "room": node.get("room"),
            "heading": node.get("heading", 0),
            "direction": direction,
        })

    return steps
