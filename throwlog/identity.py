"""Join track ids that are the same person, then recount throws on each person."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from throwlog.config import AppConfig
from throwlog.throws import peaks_for_frames

IMPLEMENTED = True


def run(session_dir: Path, config: AppConfig) -> None:
    """Write identity/players.json and throws/by_player.json."""
    started = time.perf_counter()
    source = session_dir / "tracks" / "detections.json"
    ingest_path = session_dir / "ingest.json"
    if not source.is_file():
        raise FileNotFoundError(f"tracking has not been run for {session_dir.name}")
    if not ingest_path.is_file():
        raise FileNotFoundError(f"ingest has not been run for {session_dir.name}")
    detections = json.loads(source.read_text())["people"]
    fps = float(json.loads(ingest_path.read_text())["fps"])
    summaries = summarize_tracks(detections)
    clusters = link_tracks(
        summaries,
        height_ratio_max=config.identity.height_ratio_max,
        overlap_iou_min=config.identity.overlap_iou_min,
        max_gap_frames=config.identity.max_gap_frames,
    )
    players = []
    counted = []
    for index, track_ids in enumerate(clusters, start=1):
        frames = _merged_frames(summaries, track_ids)
        peaks = peaks_for_frames(frames, fps, config)
        throws = [
            {
                "frame": frame,
                "timestamp_s": round(frame / fps, 3),
                "wrist_speed": round(speed, 3),
            }
            for frame, speed in peaks
        ]
        player_id = f"p{index}"
        height = statistics.median(summaries[track_id].height for track_id in track_ids)
        players.append(
            {
                "player_id": player_id,
                "track_ids": track_ids,
                "frame_start": frames[0]["frame"] if frames else None,
                "frame_end": frames[-1]["frame"] if frames else None,
                "frame_count": len(frames),
                "median_height": round(height, 1),
                "throw_count": len(throws),
                "throws": throws,
            }
        )
        for throw in throws:
            counted.append({"player_id": player_id, **throw})
    record = {
        "session_id": session_dir.name,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "players": players,
    }
    identity_dir = session_dir / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / "players.json").write_text(json.dumps(record, indent=2) + "\n")
    throws_dir = session_dir / "throws"
    throws_dir.mkdir(parents=True, exist_ok=True)
    (throws_dir / "by_player.json").write_text(
        json.dumps({"session_id": session_dir.name, "throws": counted}, indent=2) + "\n"
    )


class TrackSummary:
    def __init__(self, track_id: int):
        self.track_id = track_id
        self.boxes: dict[int, list[float]] = {}
        self.rows: list[dict] = []
        self.height = 0.0

    @property
    def start(self) -> int:
        return min(self.boxes)

    @property
    def end(self) -> int:
        return max(self.boxes)


def summarize_tracks(detections: list[dict]) -> dict[int, TrackSummary]:
    summaries: dict[int, TrackSummary] = {}
    for person in detections:
        track_id = int(person["track_id"])
        summary = summaries.setdefault(track_id, TrackSummary(track_id))
        frame = int(person["frame"])
        summary.boxes[frame] = [float(value) for value in person["box"]]
        summary.rows.append(
            {
                "frame": frame,
                "det_conf": float(person["det_conf"]),
                "keypoints": person["keypoints"],
            }
        )
    for summary in summaries.values():
        heights = [box[3] - box[1] for box in summary.boxes.values()]
        summary.height = statistics.median(heights)
        summary.rows.sort(key=lambda row: row["frame"])
    return summaries


def link_tracks(
    summaries: dict[int, TrackSummary],
    *,
    height_ratio_max: float,
    overlap_iou_min: float,
    max_gap_frames: int,
) -> list[list[int]]:
    """Return clusters of track ids, each cluster ordered by id."""
    ids = sorted(summaries)
    parent = {track_id: track_id for track_id in ids}

    def find(track_id: int) -> int:
        while parent[track_id] != track_id:
            parent[track_id] = parent[parent[track_id]]
            track_id = parent[track_id]
        return track_id

    def union(left: int, right: int) -> None:
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    same_frame: list[tuple[int, int]] = []
    gaps: list[tuple[int, int, int]] = []
    conflicts: set[tuple[int, int]] = set()
    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            kind, gap = _relation(
                summaries[left],
                summaries[right],
                height_ratio_max,
                overlap_iou_min,
                max_gap_frames,
            )
            if kind == "same":
                same_frame.append((left, right))
            elif kind == "gap":
                gaps.append((gap, left, right))
            elif kind == "conflict":
                conflicts.add((left, right))
    for left, right in same_frame:
        union(left, right)
    for _gap, left, right in sorted(gaps):
        if find(left) == find(right):
            continue
        if _cluster_conflict(parent, find, left, right, conflicts):
            continue
        union(left, right)
    groups: dict[int, list[int]] = {}
    for track_id in ids:
        groups.setdefault(find(track_id), []).append(track_id)
    return [sorted(members) for members in groups.values()]


def _cluster_conflict(parent, find, left: int, right: int, conflicts: set[tuple[int, int]]) -> bool:
    left_members = [track_id for track_id in parent if find(track_id) == find(left)]
    right_members = [track_id for track_id in parent if find(track_id) == find(right)]
    for one in left_members:
        for other in right_members:
            pair = (min(one, other), max(one, other))
            if pair in conflicts:
                return True
    return False


def _relation(left: TrackSummary, right: TrackSummary, height_ratio_max: float, overlap_iou_min: float, max_gap_frames: int) -> tuple[str, int]:
    shorter = min(left.height, right.height)
    if shorter <= 0 or max(left.height, right.height) / shorter > height_ratio_max:
        return "different", 0
    shared = set(left.boxes) & set(right.boxes)
    if shared:
        scores = sorted(_iou(left.boxes[frame], right.boxes[frame]) for frame in shared)
        if scores[len(scores) // 2] >= overlap_iou_min:
            return "same", 0
        return "conflict", 0
    earlier, later = (left, right) if left.end <= right.start else (right, left)
    gap = later.start - earlier.end - 1
    if 0 <= gap <= max_gap_frames:
        return "gap", gap
    return "different", gap


def _iou(left: list[float], right: list[float]) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection <= 0:
        return 0.0
    area_left = (left[2] - left[0]) * (left[3] - left[1])
    area_right = (right[2] - right[0]) * (right[3] - right[1])
    return intersection / (area_left + area_right - intersection)


def _merged_frames(summaries: dict[int, TrackSummary], track_ids: list[int]) -> list[dict]:
    chosen: dict[int, dict] = {}
    for track_id in track_ids:
        for row in summaries[track_id].rows:
            current = chosen.get(row["frame"])
            if current is None or row["det_conf"] > current["det_conf"]:
                chosen[row["frame"]] = row
    return [chosen[frame] for frame in sorted(chosen)]
