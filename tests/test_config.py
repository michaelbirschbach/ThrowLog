from throwlog.config import load_config


def test_default_config_loads_and_leaves_throw_threshold_unset():
    config = load_config()
    assert config.ingest.sample_every_n_frames == 2
    assert config.pose.device == "mps"
    assert config.throws.wrist_speed_min is None
    assert config.review.confidence_threshold == 0.5
    assert config.ball_colors == {}
