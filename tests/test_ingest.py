import json

import cv2
import numpy as np

from throwlog.config import load_config
from throwlog.ingest import apply_display_rotation, run, sample_frame_indices


def test_sample_keeps_every_nth_frame():
    assert sample_frame_indices(7, 2) == [0, 2, 4, 6]


def test_ninety_degrees_is_clockwise_and_upright():
    frame = np.zeros((2, 4, 3), np.uint8)
    frame[0, 0] = (9, 8, 7)
    rotated = apply_display_rotation(frame, 90)
    assert rotated.shape == (4, 2, 3)
    assert rotated[0, 1].tolist() == [9, 8, 7]
    assert apply_display_rotation(frame, 0) is frame


def test_ingest_writes_metadata_for_a_short_clip(tmp_path):
    video = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(
        str(video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (32, 16),
    )
    assert writer.isOpened()
    for index in range(6):
        frame = np.zeros((16, 32, 3), np.uint8)
        frame[:, :, 1] = 20 * index
        writer.write(frame)
    writer.release()

    session = tmp_path / "session"
    session.mkdir()
    (session / "source.json").write_text(
        json.dumps({"video_path": str(video), "timing": "playback"})
    )
    run(session, load_config())

    record = json.loads((session / "ingest.json").read_text())
    assert record["frame_count"] == 6
    assert record["fps"] == 10
    assert record["duration_s"] == 0.6
    assert record["timing"] == "playback"
    assert record["display_width"] == 32
    assert record["display_height"] == 16
    assert record["sampled_frames"] == [0, 2, 4]
    assert (session / "frames" / "preview.jpg").is_file()
