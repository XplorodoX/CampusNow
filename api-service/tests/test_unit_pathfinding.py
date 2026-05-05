"""Unit tests for Dijkstra pathfinding (app.pathfinding)."""

import pytest

from app.pathfinding import find_route

# ---------------------------------------------------------------------------
# Minimal test graph
#
#   node0 --front--> node1 --front--> node2 (room="G2 0.02")
#          \--right-> node3 (room="G2 0.03")
# ---------------------------------------------------------------------------

GRAPH = {
    "startNode": "node0",
    "nodes": [
        {
            "id": "node0",
            "image": "img0.jpg",
            "building": "G2",
            "heading": 0,
            "exits": {"front": "node1", "right": "node3"},
            "nearby_rooms": [],
        },
        {
            "id": "node1",
            "image": "img1.jpg",
            "building": "G2",
            "heading": 10,
            "exits": {"front": "node2", "back": "node0"},
            "nearby_rooms": [],
        },
        {
            "id": "node2",
            "image": "img2.jpg",
            "building": "G2",
            "heading": 5,
            "exits": {"back": "node1"},
            "nearby_rooms": [{"room_id": "G2 0.02", "direction": "links"}],
        },
        {
            "id": "node3",
            "image": "img3.jpg",
            "building": "G2",
            "heading": 90,
            "exits": {"left": "node0"},
            "nearby_rooms": [{"room_id": "G2 0.03", "direction": "Tür geradeaus"}],
        },
    ],
}


def test_direct_neighbor():
    """node0 → right → node3 (1 step), room_direction is set at destination."""
    steps = find_route(GRAPH, target_room="G2 0.03")
    assert steps is not None
    assert len(steps) == 2
    assert steps[0]["node_id"] == "node0"
    assert steps[0]["direction"] == "right"
    assert steps[1]["node_id"] == "node3"
    assert steps[1]["direction"] is None
    assert steps[1]["room_direction"] == "Tür geradeaus"


def test_two_hops():
    """node0 → front → node1 → front → node2 (2 hops)."""
    steps = find_route(GRAPH, target_room="G2 0.02")
    assert steps is not None
    assert len(steps) == 3
    assert [s["node_id"] for s in steps] == ["node0", "node1", "node2"]
    assert steps[0]["direction"] == "front"
    assert steps[1]["direction"] == "front"
    assert steps[2]["direction"] is None
    assert steps[2]["room_direction"] == "links"


def test_custom_start_node():
    """Starting from node1, one hop to node2."""
    steps = find_route(GRAPH, target_room="G2 0.02", start_node_id="node1")
    assert steps is not None
    assert len(steps) == 2
    assert steps[0]["node_id"] == "node1"
    assert steps[1]["node_id"] == "node2"


def test_start_is_target():
    """If startNode itself has access to the target room, path has exactly one step."""
    graph = {
        "startNode": "node0",
        "nodes": [
            {"id": "node0", "image": "x.jpg", "heading": 0, "exits": {},
             "nearby_rooms": [{"room_id": "G2 0.01", "direction": "links"}]},
        ],
    }
    steps = find_route(graph, target_room="G2 0.01")
    assert steps is not None
    assert len(steps) == 1
    assert steps[0]["direction"] is None
    assert steps[0]["room_direction"] == "links"


def test_no_path_returns_none():
    """Room exists in graph but node is unreachable → None."""
    graph = {
        "startNode": "node0",
        "nodes": [
            {"id": "node0", "image": "x.jpg", "heading": 0, "exits": {}, "nearby_rooms": []},
            {"id": "node1", "image": "y.jpg", "heading": 0, "exits": {},
             "nearby_rooms": [{"room_id": "G2 0.99", "direction": None}]},
        ],
    }
    assert find_route(graph, target_room="G2 0.99") is None


def test_unknown_room_returns_none():
    assert find_route(GRAPH, target_room="DOES_NOT_EXIST") is None


def test_invalid_start_node_returns_none():
    assert find_route(GRAPH, target_room="G2 0.02", start_node_id="GHOST") is None


def test_step_fields_present():
    """Every step must contain the required fields."""
    steps = find_route(GRAPH, target_room="G2 0.02")
    assert steps is not None
    required = {"node_id", "image", "building", "heading", "direction", "nearby_rooms", "room_direction"}
    for step in steps:
        assert required <= step.keys()


def test_shortest_path_preferred():
    """Dijkstra must pick the shortest (fewest hops) path when alternatives exist."""
    nr = lambda rid: [{"room_id": rid, "direction": "geradeaus"}]
    graph = {
        "startNode": "node0",
        "nodes": [
            {"id": "node0",  "image": "i0.jpg", "heading": 0, "exits": {"front": "node1", "right": "nodeA"}, "nearby_rooms": []},
            {"id": "node1",  "image": "i1.jpg", "heading": 0, "exits": {"front": "target"}, "nearby_rooms": []},
            {"id": "nodeA",  "image": "iA.jpg", "heading": 0, "exits": {"front": "nodeB"},  "nearby_rooms": []},
            {"id": "nodeB",  "image": "iB.jpg", "heading": 0, "exits": {"front": "target"}, "nearby_rooms": []},
            {"id": "target", "image": "iT.jpg", "heading": 0, "exits": {}, "nearby_rooms": nr("G2 0.05")},
        ],
    }
    steps = find_route(graph, target_room="G2 0.05")
    assert steps is not None
    assert len(steps) == 3  # node0 → node1 → target
    assert [s["node_id"] for s in steps] == ["node0", "node1", "target"]
