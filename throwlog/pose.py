"""Group tracked keypoints into one time series per person."""

from __future__ import annotations

import json
import time
from pathlib import Path

from throwlog.config import AppConfig

IMPLEMENTED = True

LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_WRIST = 9
RIGHT_WRIST = 10


def run(session_dir: Path, config: AppConfig) -> None:
    """Read tracks/detections.json and write poses/keypoints.json."""
    del config
    started = time.perf_counter()
    source = session_dir / "tracks" / "detections.json"
    if not source.is_file():
        raise FileNotFoundError(f"tracking has not been run for {session_dir.name}")
    detections = json.loads(source.read_text())
    grouped: dict[int, list[dict]] = {}
    for person in detections["people"]:
        grouped.setdefault(int(person["track_id"]), []).append(
            {"frame": int(person["frame"]), "keypoints": person["keypoints"]}
        )
    tracks = []
    for track_id, frames in sorted(grouped.items()):
        frames.sort(key=lambda row: row["frame"])
        tracks.append({"track_id": track_id, "frames": frames})
    record = {
        "session_id": session_dir.name,
        "track_count": len(tracks),
        "elapsed_s": round(time.perf_counter() - started, 3),
        "tracks": tracks,
    }
    poses_dir = session_dir / "poses"
    poses_dir.mkdir(parents=True, exist_ok=True)
    (poses_dir / "keypoints.json").write_text(json.dumps(record) + "\n")
