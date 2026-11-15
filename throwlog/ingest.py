"""Decode a session video and record frame rate, size, rotation, and the tracking sample."""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

from throwlog.config import ROOT, AppConfig
from throwlog.paths import MANIFESTS

IMPLEMENTED = True

_ROTATION = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def apply_display_rotation(frame: np.ndarray, degrees: int) -> np.ndarray:
    """Turn a stored frame into the upright display frame.

    Ninety degrees is clockwise. That is the rotation this phone clip needs
    when the decoder does not apply it.
    """
    degrees = int(degrees) % 360
    if degrees == 0:
        return frame
    code = _ROTATION.get(degrees)
    if code is None:
        raise ValueError(f"unsupported rotation: {degrees}")
    return cv2.rotate(frame, code)


def sample_frame_indices(frame_count: int, every_n: int) -> list[int]:
    if every_n < 1:
        raise ValueError("sample_every_n_frames must be at least 1")
    return list(range(0, frame_count, every_n))


def resolve_video(session_dir: Path) -> tuple[Path, str]:
    """Return the video path and the timing basis for this session.

    `source.json` in the session folder wins. Otherwise the manifest named
    after the session id is used.
    """
    source = session_dir / "source.json"
    if source.exists():
        data = json.loads(source.read_text())
        path = Path(data["video_path"])
        timing = str(data.get("timing", "unknown"))
        return path, timing

    manifest = MANIFESTS / f"{session_dir.name}.yaml"
    if manifest.exists():
        info = yaml.safe_load(manifest.read_text())
        path = Path(info["path"])
        if not path.is_absolute():
            path = ROOT / path
        timing = str(info.get("timing", "unknown"))
        return path, timing

    raise FileNotFoundError(
        f"no video for session {session_dir.name}. "
        "Add source.json or a manifest under data/manifests."
    )


def run(session_dir: Path, config: AppConfig) -> None:
    """Decode the session video and write ingest.json plus one upright preview."""
    started = time.perf_counter()
    video_path, timing = resolve_video(session_dir)
    if not video_path.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")
    # Apply the display rotation ourselves so the result does not depend on
    # whether this OpenCV build auto-orients.
    capture.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        capture.release()
        raise RuntimeError(f"video reported no frame rate: {video_path}")
    orientation = int(round(float(capture.get(cv2.CAP_PROP_ORIENTATION_META)))) % 360
    reported_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_count = 0
    stored_shape: tuple[int, int] | None = None
    display_shape: tuple[int, int] | None = None
    preview_index = None
    preview = None

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if stored_shape is None:
            stored_shape = (int(frame.shape[0]), int(frame.shape[1]))
            upright = apply_display_rotation(frame, orientation)
            display_shape = (int(upright.shape[0]), int(upright.shape[1]))
        frame_count += 1
    capture.release()

    if frame_count == 0 or stored_shape is None or display_shape is None:
        raise RuntimeError(f"video contained no frames: {video_path}")

    preview_index = frame_count // 2
    capture = cv2.VideoCapture(str(video_path))
    capture.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
    capture.set(cv2.CAP_PROP_POS_FRAMES, preview_index)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"could not read preview frame {preview_index}")
    preview = apply_display_rotation(frame, orientation)

    every_n = config.ingest.sample_every_n_frames
    sampled = sample_frame_indices(frame_count, every_n)
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    preview_path = frames_dir / "preview.jpg"
    if not cv2.imwrite(str(preview_path), preview):
        raise RuntimeError(f"could not write {preview_path}")

    record = {
        "session_id": session_dir.name,
        "video_path": str(video_path),
        "fps": fps,
        "frame_count": frame_count,
        "reported_frame_count": reported_frames,
        "duration_s": round(frame_count / fps, 3),
        "timing": timing,
        "orientation_degrees": orientation,
        "stored_height": stored_shape[0],
        "stored_width": stored_shape[1],
        "display_height": display_shape[0],
        "display_width": display_shape[1],
        "sample_every_n_frames": every_n,
        "full_rate_window_frames": config.ingest.full_rate_window_frames,
        "full_rate_windows": [],
        "sampled_frame_count": len(sampled),
        "sampled_frames": sampled,
        "preview_frame": preview_index,
        "preview_path": str(preview_path),
        "elapsed_s": round(time.perf_counter() - started, 3),
    }
    (session_dir / "ingest.json").write_text(json.dumps(record, indent=2) + "\n")
