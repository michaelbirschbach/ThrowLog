import json

from throwlog.export import write_throws_csv, write_throws_json
from throwlog.schemas import ComponentConfidence, DrillType, ThrowRecord


def _row():
    return ThrowRecord(
        session_id="img_0138",
        throw_id=1,
        timestamp_s=1.0,
        frame=30,
        player_id="pitcher",
        partner_id=None,
        drill_type=DrillType.wall,
        ball_type="unknown",
        distance_ft=60.0,
        velocity_mph=90.0,
        velocity_low_mph=86.0,
        velocity_high_mph=94.0,
        confidence=0.5,
        component_conf=ComponentConfidence(
            detection=0.5,
            identity=0.5,
            ball_type=0.5,
            distance=0.5,
            velocity=0.5,
        ),
        needs_review=False,
        clip_path="export/throw_0001.mp4",
    )


def test_json_and_csv_round_trip_a_valid_throw(tmp_path):
    write_throws_json([_row()], tmp_path / "throws.json")
    write_throws_csv([_row()], tmp_path / "throws.csv")
    payload = json.loads((tmp_path / "throws.json").read_text())
    assert payload[0]["drill_type"] == "wall"
    header = (tmp_path / "throws.csv").read_text().splitlines()[0]
    assert header.startswith("session_id,throw_id,")
