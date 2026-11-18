import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class MockModel:
    def register_agent(self, agent): pass


def test_group_hint_free_slot_returns_true_no_hint():
    from agents.group_room_agents import GroupAgent
    a = GroupAgent(MockModel(), 1, "G1", "CS", 1, 30)
    ok, hint = a.check_and_hint("Monday", "08:00-10:00")
    assert ok is True
    assert hint is None


def test_group_hint_booked_slot_returns_false_with_hint():
    from agents.group_room_agents import GroupAgent
    a = GroupAgent(MockModel(), 1, "G1", "CS", 1, 30)
    a.booked_slots.add(("Monday", "08:00-10:00"))
    ok, hint = a.check_and_hint("Monday", "08:00-10:00")
    assert ok is False
    assert hint is not None
    assert hint != ("Monday", "08:00-10:00")


def test_group_hint_is_next_chronological_free_slot():
    from agents.group_room_agents import GroupAgent
    a = GroupAgent(MockModel(), 1, "G1", "CS", 1, 30)
    a.booked_slots.add(("Monday", "08:00-10:00"))
    ok, hint = a.check_and_hint("Monday", "08:00-10:00")
    assert hint == ("Monday", "10:00-12:00")


def test_group_hint_wraps_to_next_day():
    from agents.group_room_agents import GroupAgent
    a = GroupAgent(MockModel(), 1, "G1", "CS", 1, 30)
    slots = [("Monday", t) for t in ["08:00-10:00","10:00-12:00","12:00-14:00","14:00-16:00","16:00-18:00"]]
    a.booked_slots.update(slots)
    ok, hint = a.check_and_hint("Monday", "16:00-18:00")
    assert hint is not None
    assert hint[0] == "Tuesday"


def test_room_hint_available_slot_returns_true_no_hint():
    from agents.group_room_agents import RoomAgent
    r = RoomAgent(MockModel(), 1, "R1", 40, "Projector")
    ok, hint = r.check_and_hint("Standard", 30, "Monday", "08:00-10:00")
    assert ok is True
    assert hint is None


def test_room_hint_booked_returns_false_with_next_slot():
    from agents.group_room_agents import RoomAgent
    r = RoomAgent(MockModel(), 1, "R1", 40, "Projector")
    r.booked_slots.add(("Monday", "08:00-10:00"))
    ok, hint = r.check_and_hint("Standard", 30, "Monday", "08:00-10:00")
    assert ok is False
    assert hint == ("Monday", "10:00-12:00")


def test_room_hint_wrong_type_returns_no_hint():
    from agents.group_room_agents import RoomAgent
    r = RoomAgent(MockModel(), 1, "R1", 40, "Projector")  # no Computers
    ok, hint = r.check_and_hint("Lab", 30, "Monday", "08:00-10:00")
    assert ok is False
    assert hint is None
