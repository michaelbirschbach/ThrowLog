"""Find throw events from wrist-speed peaks in the pose time series."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Optional

from throwlog.config import AppConfig
from throwlog.pose import LEFT_SHOULDER, LEFT_WRIST, RIGHT_SHOULDER, RIGHT_WRIST

IMPLEMENTED = True

_WRISTS = (LEFT_WRIST, RIGHT_WRIST)


def run(session_dir: Path, config: AppConfig) -> None:
    """Write throws/candidates.json. Counts are candidates, not yet hand-checked."""
    started = time.perf_counter()
    source = session_dir / "poses" / "keypoints.json"
    ingest_path = session_dir / "ingest.json"
    if not source.is_file():
        raise FileNotFoundError(f"pose has not been run for {session_dir.name}")
    if not ingest_path.is_file():
        raise FileNotFoundError(f"ingest has not been run for {session_dir.name}")
    poses = json.loads(source.read_text())
    fps = float(json.loads(ingest_path.read_text())["fps"])
    minimum_gap = config.throws.min_gap_frames
    window = config.throws.smooth_frames
    factor = config.throws.peak_factor
    floor = config.throws.wrist_speed_min

    candidates = []
    for track in poses["tracks"]:
        if len(track["frames"]) < config.throws.min_track_frames:
            continue
        peaks = peaks_for_frames(track["frames"], fps, config)
        for frame, speed in peaks:
            candidates.append(
                {
                    "track_id": track["track_id"],
                    "frame": frame,
                    "timestamp_s": round(frame / fps, 3),
                    "wrist_speed": round(speed, 3),
                }
            )
    candidates.sort(key=lambda row: (row["frame"], row["track_id"]))
    record = {
        "session_id": session_dir.name,
        "speed_unit": "shoulder_widths_per_second",
        "peak_factor": factor,
        "min_gap_frames": minimum_gap,
        "smooth_frames": window,
        "wrist_speed_min": floor,
        "candidate_count": len(candidates),
        "elapsed_s": round(time.perf_counter() - started, 3),
        "candidates": candidates,
    }
    throws_dir = session_dir / "throws"
    throws_dir.mkdir(parents=True, exist_ok=True)
    (throws_dir / "candidates.json").write_text(json.dumps(record, indent=2) + "\n")


def peaks_for_frames(frames: list[dict], fps: float, config: AppConfig) -> list[tuple[int, float]]:
    """Wrist-speed peaks for one person. `frames` are sorted pose rows."""
    used, speeds = _wrist_speed_series(frames, fps, config.pose.keypoint_confidence)
    smoothed = _smooth(speeds, config.throws.smooth_frames)
    return find_peaks(
        used,
        smoothed,
        min_gap_frames=config.throws.min_gap_frames,
        peak_factor=config.throws.peak_factor,
        floor=config.throws.wrist_speed_min,
    )


def _wrist_speed_series(frames: list[dict], fps: float, min_conf: float) -> tuple[list[int], list[float]]:
    used_frames: list[int] = []
    speeds: list[float] = []
    previous = None
    for row in frames:
        current_frame = int(row["frame"])
        current = row["keypoints"]
        if previous is not None:
            previous_frame, previous_points = previous
            delta = (current_frame - previous_frame) / fps
            speed = _interval_speed(previous_points, current, delta, min_conf)
            if speed is not None:
                used_frames.append(current_frame)
                speeds.append(speed)
        previous = (current_frame, current)
    return used_frames, speeds


def _interval_speed(previous, current, delta_s: float, min_conf: float) -> Optional[float]:
    if delta_s <= 0 or len(previous) < 17 or len(current) < 17:
        return None
    scale = _shoulder_width(current, min_conf) or _shoulder_width(previous, min_conf)
    if scale is None or scale < 1:
        return None
    speeds = []
    for index in _WRISTS:
        before = previous[index]
        after = current[index]
        if before[2] < min_conf or after[2] < min_conf:
            continue
        distance = math.hypot(after[0] - before[0], after[1] - before[1])
        speeds.append(distance / scale / delta_s)
    if not speeds:
        return None
    return max(speeds)


def _shoulder_width(keypoints, min_conf: float) -> Optional[float]:
    left = keypoints[LEFT_SHOULDER]
    right = keypoints[RIGHT_SHOULDER]
    if left[2] < min_conf or right[2] < min_conf:
        return None
    return math.hypot(left[0] - right[0], left[1] - right[1])


def _smooth(values: list[float], window: int) -> list[float]:
    if window <= 1 or len(values) == 0:
        return list(values)
    half = window // 2
    smoothed = []
    for index in range(len(values)):
        start = max(0, index - half)
        stop = min(len(values), index + half + 1)
        chunk = values[start:stop]
        smoothed.append(sum(chunk) / len(chunk))
    return smoothed


def find_peaks(
    frames: list[int],
    speeds: list[float],
    *,
    min_gap_frames: int,
    peak_factor: float,
    floor: Optional[float],
) -> list[tuple[int, float]]:
    """Return (frame, speed) for local peaks that clear the relative threshold."""
    if len(speeds) < 3:
        return []
    ordered = sorted(speeds)
    median = ordered[len(ordered) // 2]
    threshold = median * peak_factor
    if floor is not None:
        threshold = max(threshold, floor)
    peaks: list[tuple[int, float]] = []
    for index in range(1, len(speeds) - 1):
        speed = speeds[index]
        if speed < threshold:
            continue
        if speed < speeds[index - 1] or speed < speeds[index + 1]:
            continue
        frame = frames[index]
        if peaks and frame - peaks[-1][0] < min_gap_frames:
            if speed > peaks[-1][1]:
                peaks[-1] = (frame, speed)
            continue
        peaks.append((frame, speed))
    return peaks
