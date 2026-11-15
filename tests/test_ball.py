import numpy as np

from throwlog.ball import drop_static, find_blobs, link_flights, match_throws, outside_boxes
from throwlog.config import load_config


def _dark_frame(width=320, height=180):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :] = (20, 20, 20)
    return frame


def _circle(frame, center, radius=6):
    import cv2

    cv2.circle(frame, center, radius, (235, 235, 235), -1)


def test_a_white_circle_on_a_dark_background_is_found():
    config = load_config().ball
    config.detect_width = 320
    frame = _dark_frame()
    _circle(frame, (80, 90))
    blobs = find_blobs(frame, config)
    assert blobs
    assert any(abs(blob["x"] - 80) < 4 and abs(blob["y"] - 90) < 4 for blob in blobs)


def test_a_blob_inside_a_person_box_is_dropped():
    kept = outside_boxes([{"x": 10, "y": 10, "area": 20}, {"x": 80, "y": 80, "area": 20}], [[0, 0, 40, 40]])
    assert kept == [{"x": 80, "y": 80, "area": 20}]


def test_a_blob_that_sits_still_is_not_a_ball():
    still = [{"frame": frame, "x": 10.0, "y": 10.0, "area": 20} for frame in range(15)]
    moving = {"frame": 3, "x": 100.0, "y": 40.0, "area": 20}
    kept = drop_static(still + [moving], cell_px=12, max_hits=12)
    assert kept == [moving]


def test_a_moving_circle_becomes_one_flight_and_confirms_a_nearby_throw():
    config = load_config().ball
    config.detect_width = 320
    blobs = []
    for index, x in enumerate((40, 70, 100, 130, 170)):
        frame = _dark_frame()
        _circle(frame, (x, 90))
        for blob in find_blobs(frame, config):
            blob["frame"] = index
            blobs.append(blob)
    flights = link_flights(
        blobs,
        max_jump_px=config.max_jump_px,
        max_gap_frames=config.max_gap_frames,
        min_track_frames=config.min_track_frames,
        min_travel_px=config.min_travel_px,
        min_straightness=config.min_straightness,
    )
    assert len(flights) == 1
    rows = [
        {
            "flight_id": 1,
            "frame_start": flights[0][0]["frame"],
            "frame_end": flights[0][-1]["frame"],
        }
    ]
    matched = match_throws([{"frame": 2, "player_id": "p1"}], rows, window=2)
    missed = match_throws([{"frame": 30, "player_id": "p1"}], rows, window=2)
    assert matched[0]["confirmed"] is True
    assert missed[0]["confirmed"] is False
