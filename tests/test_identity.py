from throwlog.identity import TrackSummary, link_tracks


def _track(track_id, frames, box, height_box=None):
    summary = TrackSummary(track_id)
    summary.boxes = {frame: list(box) for frame in frames}
    summary.height = (box[3] - box[1]) if height_box is None else height_box
    summary.rows = []
    return summary


def test_overlapping_similar_boxes_join():
    tracks = {
        1: _track(1, range(0, 10), [0, 0, 100, 200]),
        2: _track(2, range(8, 20), [10, 10, 110, 210]),
    }
    assert link_tracks(tracks, height_ratio_max=1.5, overlap_iou_min=0.25, max_gap_frames=60) == [[1, 2]]


def test_overlapping_boxes_with_no_overlap_stay_apart():
    tracks = {
        1: _track(1, range(0, 10), [0, 0, 80, 200]),
        2: _track(2, range(0, 10), [200, 0, 280, 200]),
    }
    clusters = link_tracks(tracks, height_ratio_max=1.5, overlap_iou_min=0.25, max_gap_frames=60)
    assert clusters == [[1], [2]]


def test_a_gap_does_not_absorb_someone_who_is_on_screen_at_the_same_time():
    tracks = {
        1: _track(1, range(0, 30), [0, 0, 100, 200]),
        2: _track(2, range(20, 50), [5, 0, 105, 200]),
        3: _track(3, range(40, 60), [300, 0, 400, 200]),
    }
    clusters = link_tracks(tracks, height_ratio_max=1.5, overlap_iou_min=0.25, max_gap_frames=30)
    assert [1, 2] in clusters
    assert [3] in clusters


def test_a_short_gap_joins_and_a_different_height_does_not():
    tracks = {
        1: _track(1, range(0, 10), [0, 0, 100, 400]),
        2: _track(2, range(20, 30), [0, 0, 100, 400]),
        3: _track(3, range(40, 50), [0, 0, 40, 80]),
    }
    clusters = link_tracks(tracks, height_ratio_max=1.5, overlap_iou_min=0.25, max_gap_frames=15)
    assert [1, 2] in clusters
    assert [3] in clusters
