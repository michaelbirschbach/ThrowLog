import pytest
from pydantic import ValidationError

from throwlog.schemas import ComponentConfidence, DrillType, ThrowRecord


def _record(**overrides):
    base = dict(
        session_id="img_0138",
        throw_id=1,
        timestamp_s=1.5,
        frame=45,
        player_id="pitcher",
        partner_id=None,
        drill_type=DrillType.wall,
        ball_type="unknown",
        distance_ft=60.0,
        velocity_mph=88.0,
        velocity_low_mph=84.0,
        velocity_high_mph=92.0,
        confidence=0.4,
        component_conf=ComponentConfidence(
            detection=0.8,
            identity=0.7,
            ball_type=0.2,
            distance=0.3,
            velocity=0.3,
        ),
        needs_review=True,
        clip_path="export/throw_0001.mp4",
    )
    base.update(overrides)
    return ThrowRecord.model_validate(base)


def test_wall_throw_accepts_a_null_partner():
    row = _record()
    assert row.drill_type is DrillType.wall
    assert row.partner_id is None


def test_catch_throw_requires_a_partner():
    with pytest.raises(ValidationError):
        _record(drill_type=DrillType.catch, partner_id=None)


def test_velocity_range_must_contain_the_estimate():
    with pytest.raises(ValidationError):
        _record(velocity_low_mph=90.0)
