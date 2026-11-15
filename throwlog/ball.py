"""Find a ball in flight and use it to confirm throw candidates.

The detector looks for two appearances of a light ball, measured on the catch
short: a small white spot on a dark background, and a larger white ball still
close to the camera. Color names stay unmapped until ball_colors is filled in.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np

from throwlog.config import AppConfig, BallConfig
from throwlog.ingest import apply_display_rotation

IMPLEMENTED = True

COLOR = "white"


def run(session_dir: Path, config: AppConfig) -> None:
    """Write ball/flights.json. A candidate is confirmed when a flight is nearby in time."""
    started = time.perf_counter()
    ingest_path = session_dir / "ingest.json"
    tracks_path = session_dir / "tracks" / "detections.json"
    if not ingest_path.is_file():
        raise FileNotFoundError(f"ingest has not been run for {session_dir.name}")
    if not tracks_path.is_file():
        raise FileNotFoundError(f"tracking has not been run for {session_dir.name}")
    ingest = json.loads(ingest_path.read_text())
    video_path = Path(ingest["video_path"])
    if not video_path.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")

    throws, throw_source = _load_throws(session_dir)
    scale = config.ball.detect_width / float(ingest["display_width"])
    boxes = _boxes_by_frame(json.loads(tracks_path.read_text())["people"], scale)
    blobs = _scan_video(
        video_path,
        orientation=int(ingest["orientation_degrees"]),
        boxes=boxes,
        config=config.ball,
    )
    moving = drop_static(blobs, config.ball.static_cell_px, config.ball.static_cell_hits)
    flights = link_flights(
        moving,
        max_jump_px=config.ball.max_jump_px,
        max_gap_frames=config.ball.max_gap_frames,
        min_track_frames=config.ball.min_track_frames,
        min_travel_px=config.ball.min_travel_px,
        min_straightness=config.ball.min_straightness,
    )
    fps = float(ingest["fps"])
    ball_type = config.ball_colors.get(COLOR, COLOR)
    full_scale = float(ingest["display_width"]) / config.ball.detect_width
    flight_rows = [_flight_row(index, flight, fps, full_scale, ball_type) for index, flight in enumerate(flights, start=1)]
    matched = match_throws(throws, flight_rows, config.ball.confirm_window_frames)
    record = {
        "session_id": session_dir.name,
        "color": COLOR,
        "ball_type": ball_type,
        "throw_source": throw_source,
        "detect_width": config.ball.detect_width,
        "flight_count": len(flight_rows),
        "confirmed_count": sum(1 for row in matched if row["confirmed"]),
        "elapsed_s": round(time.perf_counter() - started, 3),
        "flights": flight_rows,
        "throws": matched,
    }
    ball_dir = session_dir / "ball"
    ball_dir.mkdir(parents=True, exist_ok=True)
    (ball_dir / "flights.json").write_text(json.dumps(record, indent=2) + "\n")


def find_blobs(frame: np.ndarray, config: BallConfig) -> list[dict]:
    """White blobs in detect-width coordinates. Distant spots and a close ball."""
    if frame.shape[1] > config.detect_width:
        height = int(round(frame.shape[0] * config.detect_width / frame.shape[1]))
        frame = cv2.resize(frame, (config.detect_width, height))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    local = cv2.blur(value, (31, 31))
    contrast = value.astype(np.int16) - local.astype(np.int16)
    distant = (
        (local < config.background_value_max)
        & (saturation < config.sat_max)
        & (value > config.value_min)
        & (contrast > config.contrast_min)
    )
    close = (saturation < config.close_sat_max) & (value > config.close_value_min)
    blobs = _components(distant, config.area_min, config.area_max, max_side=28)
    blobs.extend(_components(close, config.close_area_min, config.close_area_max, max_side=90))
    return blobs


def drop_static(blobs: list[dict], cell_px: int, max_hits: int) -> list[dict]:
    """Remove blobs that sit in one place for many frames. Those are lights and trim, not a ball."""
    if not blobs:
        return []
    hits: dict[tuple[int, int], int] = {}
    for blob in blobs:
        cell = (int(blob["x"]) // cell_px, int(blob["y"]) // cell_px)
        hits[cell] = hits.get(cell, 0) + 1
    return [
        blob
        for blob in blobs
        if hits[(int(blob["x"]) // cell_px, int(blob["y"]) // cell_px)] < max_hits
    ]


def outside_boxes(blobs: list[dict], boxes: list[list[float]], pad: float = 8) -> list[dict]:
    """Drop blobs whose center lies inside a person box."""
    kept = []
    for blob in blobs:
        if any(_inside(blob["x"], blob["y"], box, pad) for box in boxes):
            continue
        kept.append(blob)
    return kept


def link_flights(
    blobs: list[dict],
    *,
    max_jump_px: float,
    max_gap_frames: int,
    min_track_frames: int,
    min_travel_px: float,
    min_straightness: float,
) -> list[list[dict]]:
    """Join blobs that move in a mostly straight line. Each blob needs a frame index."""
    by_frame: dict[int, list[dict]] = {}
    for blob in blobs:
        by_frame.setdefault(int(blob["frame"]), []).append(blob)
    if not by_frame:
        return []
    last_frame = max(by_frame)
    active: list[list[dict]] = []
    finished: list[list[dict]] = []
    for frame in range(0, last_frame + 1):
        found = by_frame.get(frame, [])
        used = [False] * len(found)
        still: list[list[dict]] = []
        for track in active:
            previous = track[-1]
            if frame - int(previous["frame"]) > max_gap_frames:
                finished.append(track)
                continue
            choice = _nearest(previous, found, used, max_jump_px)
            if choice is None:
                still.append(track)
                continue
            used[choice] = True
            track.append(found[choice])
            still.append(track)
        for index, blob in enumerate(found):
            if not used[index]:
                still.append([blob])
        active = still
    finished.extend(active)
    return [track for track in finished if _is_flight(track, min_track_frames, min_travel_px, min_straightness)]


def match_throws(throws: list[dict], flights: list[dict], window: int) -> list[dict]:
    """Mark a throw confirmed when a flight passes within `window` frames of it."""
    matched = []
    for throw in throws:
        frame = int(throw["frame"])
        best_id = None
        best_gap = None
        for flight in flights:
            gap = _frame_gap(frame, int(flight["frame_start"]), int(flight["frame_end"]))
            if gap > window:
                continue
            if best_gap is None or gap < best_gap:
                best_id = flight["flight_id"]
                best_gap = gap
        row = dict(throw)
        row["confirmed"] = best_id is not None
        row["flight_id"] = best_id
        row["frame_gap"] = best_gap
        matched.append(row)
    return matched


def _scan_video(video_path: Path, orientation: int, boxes: dict[int, list[list[float]]], config: BallConfig) -> list[dict]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")
    capture.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
    blobs: list[dict] = []
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            upright = apply_display_rotation(frame, orientation)
            for blob in outside_boxes(find_blobs(upright, config), boxes.get(frame_index, [])):
                blob["frame"] = frame_index
                blobs.append(blob)
            frame_index += 1
    finally:
        capture.release()
    return blobs


def _components(mask: np.ndarray, area_min: int, area_max: int, max_side: int) -> list[dict]:
    image = mask.astype(np.uint8) * 255
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, _labels, stats, centroids = cv2.connectedComponentsWithStats(image, 8)
    blobs = []
    for index in range(1, count):
        _x, _y, width, height, area = stats[index]
        if area < area_min or area > area_max:
            continue
        if width < 4 or height < 4 or width > max_side or height > max_side:
            continue
        aspect = width / max(height, 1)
        if aspect < 0.55 or aspect > 1.8:
            continue
        if area / max(width * height, 1) < 0.45:
            continue
        center_x, center_y = centroids[index]
        blobs.append({"x": float(center_x), "y": float(center_y), "area": int(area)})
    return blobs


def _nearest(previous: dict, found: list[dict], used: list[bool], max_jump_px: float) -> int | None:
    best_index = None
    best_distance = max_jump_px
    for index, blob in enumerate(found):
        if used[index]:
            continue
        distance = ((blob["x"] - previous["x"]) ** 2 + (blob["y"] - previous["y"]) ** 2) ** 0.5
        if distance <= best_distance:
            best_index = index
            best_distance = distance
    return best_index


def _is_flight(track: list[dict], min_track_frames: int, min_travel_px: float, min_straightness: float) -> bool:
    if len(track) < min_track_frames:
        return False
    travel, path = _travel(track)
    if path <= 0 or travel < min_travel_px:
        return False
    return travel / path >= min_straightness


def _travel(track: list[dict]) -> tuple[float, float]:
    net = ((track[-1]["x"] - track[0]["x"]) ** 2 + (track[-1]["y"] - track[0]["y"]) ** 2) ** 0.5
    path = 0.0
    for previous, current in zip(track, track[1:]):
        path += ((current["x"] - previous["x"]) ** 2 + (current["y"] - previous["y"]) ** 2) ** 0.5
    return net, path


def _inside(x: float, y: float, box: list[float], pad: float) -> bool:
    x1, y1, x2, y2 = box
    return x1 - pad <= x <= x2 + pad and y1 - pad <= y <= y2 + pad


def _frame_gap(frame: int, start: int, end: int) -> int:
    if frame < start:
        return start - frame
    if frame > end:
        return frame - end
    return 0


def _load_throws(session_dir: Path) -> tuple[list[dict], str]:
    by_player = session_dir / "throws" / "by_player.json"
    candidates = session_dir / "throws" / "candidates.json"
    if by_player.is_file():
        rows = json.loads(by_player.read_text())["throws"]
        return rows, "by_player"
    if candidates.is_file():
        rows = json.loads(candidates.read_text())["candidates"]
        return rows, "candidates"
    raise FileNotFoundError(f"throws have not been run for {session_dir.name}")


def _boxes_by_frame(people: list[dict], scale: float) -> dict[int, list[list[float]]]:
    boxes: dict[int, list[list[float]]] = {}
    for person in people:
        box = [float(value) * scale for value in person["box"]]
        boxes.setdefault(int(person["frame"]), []).append(box)
    return boxes


def _flight_row(flight_id: int, track: list[dict], fps: float, full_scale: float, ball_type: str) -> dict:
    travel, path = _travel(track)
    return {
        "flight_id": flight_id,
        "ball_type": ball_type,
        "frame_start": int(track[0]["frame"]),
        "frame_end": int(track[-1]["frame"]),
        "timestamp_start_s": round(track[0]["frame"] / fps, 3),
        "timestamp_end_s": round(track[-1]["frame"] / fps, 3),
        "travel_px": round(travel * full_scale, 1),
        "straightness": round(travel / path, 3),
        "points": [
            {
                "frame": int(point["frame"]),
                "x": round(point["x"] * full_scale, 1),
                "y": round(point["y"] * full_scale, 1),
            }
            for point in track
        ],
    }
