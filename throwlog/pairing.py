"""Assign each confirmed throw to a receiver, or mark it as a wall drill.

A catch needs another person on screen. When several people are there, the
receiver is the one the ball moves toward. A throw with nobody else in frame
is a wall drill. Throws the ball stage did not confirm stay unpaired.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from throwlog.config import AppConfig

IMPLEMENTED = True


def run(session_dir: Path, config: AppConfig) -> None:
    """Write pairing/pairs.json from ball flights and player boxes."""
    started = time.perf_counter()
    flights_path = session_dir / "ball" / "flights.json"
    tracks_path = session_dir / "tracks" / "detections.json"
    if not flights_path.is_file():
        raise FileNotFoundError(f"ball detection has not been run for {session_dir.name}")
    if not tracks_path.is_file():
        raise FileNotFoundError(f"tracking has not been run for {session_dir.name}")
    ball = json.loads(flights_path.read_text())
    people = json.loads(tracks_path.read_text())["people"]
    track_to_player = _load_players(session_dir, people)
    player_ids = sorted(set(track_to_player.values()))
    boxes = _boxes_by_frame(people, track_to_player)
    flights = {int(flight["flight_id"]): flight for flight in ball["flights"]}
    pairs = []
    for throw in ball["throws"]:
        pairs.append(
            _pair_throw(
                throw,
                flights.get(throw.get("flight_id")),
                boxes,
                player_ids,
                presence_frames=config.pairing.presence_frames,
                approach_px=config.pairing.approach_px,
            )
        )
    record = {
        "session_id": session_dir.name,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "catch_count": sum(1 for row in pairs if row["drill_type"] == "catch"),
        "wall_count": sum(1 for row in pairs if row["drill_type"] == "wall"),
        "unpaired_count": sum(1 for row in pairs if row["drill_type"] is None),
        "pairs": pairs,
    }
    pairing_dir = session_dir / "pairing"
    pairing_dir.mkdir(parents=True, exist_ok=True)
    (pairing_dir / "pairs.json").write_text(json.dumps(record, indent=2) + "\n")


def assign_drill(thrower_id: str, others: list[dict], flight: dict | None, approach_px: float) -> tuple[str, str | None]:
    """Return drill type and partner id. `others` are the people on screen besides the thrower."""
    if not others:
        return "wall", None
    if len(others) == 1 or flight is None:
        return "catch", others[0]["player_id"] if len(others) == 1 else _closest(flight, others)
    approached = []
    for person in others:
        start = _point_box_distance(flight["points"][0], person["box"])
        end = _point_box_distance(flight["points"][-1], person["box"])
        if start - end >= approach_px:
            approached.append((end, person["player_id"]))
    if approached:
        approached.sort()
        return "catch", approached[0][1]
    return "catch", _closest(flight, others)


def _pair_throw(throw: dict, flight: dict | None, boxes: dict, players: list[str], presence_frames: int, approach_px: float) -> dict:
    thrower = throw.get("player_id") or f"t{throw.get('track_id')}"
    row = {
        "player_id": thrower,
        "frame": throw["frame"],
        "timestamp_s": throw["timestamp_s"],
        "flight_id": throw.get("flight_id"),
        "confirmed": bool(throw.get("confirmed")),
        "drill_type": None,
        "partner_id": None,
    }
    if not row["confirmed"]:
        return row
    others = _others(thrower, int(throw["frame"]), boxes, players, presence_frames)
    drill, partner = assign_drill(thrower, others, flight, approach_px)
    row["drill_type"] = drill
    row["partner_id"] = partner
    return row


def _others(thrower: str, frame: int, boxes: dict, players: list[str], presence_frames: int) -> list[dict]:
    present = []
    for player_id in players:
        if player_id == thrower:
            continue
        box = _box_near(boxes, player_id, frame, presence_frames)
        if box is not None:
            present.append({"player_id": player_id, "box": box})
    return present


def _box_near(boxes: dict, player_id: str, frame: int, window: int) -> list[float] | None:
    for delta in range(window + 1):
        for candidate in (frame - delta, frame + delta):
            box = boxes.get(candidate, {}).get(player_id)
            if box is not None:
                return box
    return None


def _closest(flight: dict | None, others: list[dict]) -> str:
    if flight is None:
        return others[0]["player_id"]
    point = flight["points"][-1]
    ranked = sorted(others, key=lambda person: _point_box_distance(point, person["box"]))
    return ranked[0]["player_id"]


def _point_box_distance(point: dict, box: list[float]) -> float:
    x1, y1, x2, y2 = box
    dx = max(x1 - point["x"], 0, point["x"] - x2)
    dy = max(y1 - point["y"], 0, point["y"] - y2)
    return (dx * dx + dy * dy) ** 0.5


def _load_players(session_dir: Path, people: list[dict]) -> dict[int, str]:
    """Map track id to player id. Without identity, each track is its own player."""
    identity_path = session_dir / "identity" / "players.json"
    mapping: dict[int, str] = {}
    if identity_path.is_file():
        for player in json.loads(identity_path.read_text())["players"]:
            for track_id in player["track_ids"]:
                mapping[int(track_id)] = player["player_id"]
        return mapping
    for person in people:
        track_id = int(person["track_id"])
        mapping[track_id] = f"t{track_id}"
    return mapping


def _boxes_by_frame(people: list[dict], track_to_player: dict[int, str]) -> dict[int, dict[str, list[float]]]:
    best: dict[int, dict[str, tuple[float, list[float]]]] = {}
    for person in people:
        player_id = track_to_player.get(int(person["track_id"]))
        if player_id is None:
            continue
        frame = int(person["frame"])
        box = [float(value) for value in person["box"]]
        current = best.setdefault(frame, {}).get(player_id)
        confidence = float(person.get("det_conf", 0))
        if current is None or confidence > current[0]:
            best[frame][player_id] = (confidence, box)
    return {frame: {player_id: box for player_id, (_confidence, box) in rows.items()} for frame, rows in best.items()}
