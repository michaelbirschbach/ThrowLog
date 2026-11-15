"""Detect people, keep a track id, and store the pose keypoints from the same model."""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

from throwlog.config import AppConfig
from throwlog.ingest import apply_display_rotation

IMPLEMENTED = True


def run(session_dir: Path, config: AppConfig) -> None:
    """Track every sampled frame and write tracks/detections.json."""
    started = time.perf_counter()
    ingest_path = session_dir / "ingest.json"
    if not ingest_path.is_file():
        raise FileNotFoundError(f"ingest has not been run for {session_dir.name}")
    ingest = json.loads(ingest_path.read_text())
    video_path = Path(ingest["video_path"])
    if not video_path.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")

    orientation = int(ingest["orientation_degrees"])
    stride = config.pose.track_every_n_frames
    model = YOLO(config.pose.model)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")
    capture.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)

    detections: list[dict] = []
    frame_index = 0
    preview = None
    preview_frame = int(ingest["preview_frame"]) - (int(ingest["preview_frame"]) % stride)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % stride != 0:
                frame_index += 1
                continue
            upright = apply_display_rotation(frame, orientation)
            result = model.track(
                upright,
                persist=True,
                tracker=f"{config.pose.tracker}.yaml",
                imgsz=config.pose.imgsz,
                device=config.pose.device,
                conf=config.pose.confidence,
                verbose=False,
            )[0]
            people = _people(result, frame_index)
            detections.extend(people)
            if frame_index == preview_frame:
                preview = _draw(upright, people, config.pose.keypoint_confidence)
            frame_index += 1
    finally:
        capture.release()

    tracks_dir = session_dir / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    if preview is not None:
        preview_path = tracks_dir / "preview.jpg"
        if not cv2.imwrite(str(preview_path), preview):
            raise RuntimeError(f"could not write {preview_path}")
    else:
        preview_path = None

    track_ids = sorted({row["track_id"] for row in detections})
    record = {
        "session_id": session_dir.name,
        "model": config.pose.model,
        "device": config.pose.device,
        "imgsz": config.pose.imgsz,
        "confidence": config.pose.confidence,
        "track_every_n_frames": stride,
        "detections": len(detections),
        "track_ids": track_ids,
        "preview_frame": preview_frame,
        "preview_path": None if preview_path is None else str(preview_path),
        "elapsed_s": round(time.perf_counter() - started, 3),
        "people": detections,
    }
    (tracks_dir / "detections.json").write_text(json.dumps(record) + "\n")


def _people(result, frame_index: int) -> list[dict]:
    boxes = result.boxes
    if boxes is None or boxes.id is None or len(boxes) == 0:
        return []
    keypoints = result.keypoints
    xy = None if keypoints is None else keypoints.xy.cpu().numpy()
    conf = None if keypoints is None or keypoints.conf is None else keypoints.conf.cpu().numpy()
    people = []
    ids = boxes.id.cpu().numpy()
    det_conf = boxes.conf.cpu().numpy()
    xyxy = boxes.xyxy.cpu().numpy()
    for index, track_id in enumerate(ids):
        points = []
        if xy is not None:
            for keypoint_index, point in enumerate(xy[index]):
                score = 0.0 if conf is None else float(conf[index][keypoint_index])
                points.append([round(float(point[0]), 1), round(float(point[1]), 1), round(score, 3)])
        box = xyxy[index]
        people.append(
            {
                "frame": frame_index,
                "track_id": int(track_id),
                "det_conf": round(float(det_conf[index]), 3),
                "box": [round(float(value), 1) for value in box],
                "keypoints": points,
            }
        )
    return people


def _draw(frame, people: list[dict], keypoint_confidence: float):
    canvas = frame.copy()
    for person in people:
        x1, y1, x2, y2 = [int(value) for value in person["box"]]
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (40, 180, 60), 4)
        label = str(person["track_id"])
        cv2.putText(
            canvas,
            label,
            (x1, max(40, y1 - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (40, 180, 60),
            3,
        )
        for x, y, score in person["keypoints"]:
            if score < keypoint_confidence:
                continue
            cv2.circle(canvas, (int(x), int(y)), 6, (0, 180, 255), -1)
    return canvas
