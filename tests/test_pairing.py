from throwlog.pairing import assign_drill


def _person(player_id, box):
    return {"player_id": player_id, "box": box}


def _flight(start, end):
    return {"points": [{"x": start[0], "y": start[1]}, {"x": end[0], "y": end[1]}]}


def test_one_other_person_is_the_receiver():
    drill, partner = assign_drill("p1", [_person("p2", [800, 0, 900, 100])], None, approach_px=30)
    assert drill == "catch"
    assert partner == "p2"


def test_nobody_else_in_frame_is_a_wall_drill():
    drill, partner = assign_drill("p1", [], None, approach_px=30)
    assert drill == "wall"
    assert partner is None


def test_the_ball_picks_the_receiver_when_two_people_are_there():
    others = [
        _person("p2", [0, 0, 40, 40]),
        _person("p3", [400, 0, 480, 80]),
    ]
    flight = _flight((200, 20), (420, 40))
    drill, partner = assign_drill("p1", others, flight, approach_px=30)
    assert drill == "catch"
    assert partner == "p3"
