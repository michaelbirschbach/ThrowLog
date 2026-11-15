from throwlog.throws import find_peaks, _interval_speed


def _point(x, y, conf=1.0):
    return [x, y, conf]


def _body(wrist):
    points = [_point(0, 0) for _ in range(17)]
    points[5] = _point(0, 0)
    points[6] = _point(100, 0)
    points[9] = _point(*wrist)
    points[10] = _point(50, 40)
    return points


def test_interval_speed_uses_the_faster_wrist_in_shoulder_widths():
    before = _body((50, 0))
    after = _body((50, 100))
    speed = _interval_speed(before, after, delta_s=0.5, min_conf=0.3)
    assert speed == 2.0


def test_peaks_keep_the_higher_event_inside_the_minimum_gap():
    frames = [0, 10, 20, 25, 50]
    speeds = [1.0, 6.0, 1.0, 9.0, 1.0]
    peaks = find_peaks(frames, speeds, min_gap_frames=30, peak_factor=2.0, floor=None)
    assert [frame for frame, _speed in peaks] == [25]


def test_low_shoulder_confidence_drops_the_interval():
    before = _body((0, 0))
    after = _body((10, 0))
    after[5][2] = 0.0
    before[5][2] = 0.0
    assert _interval_speed(before, after, delta_s=0.1, min_conf=0.3) is None
