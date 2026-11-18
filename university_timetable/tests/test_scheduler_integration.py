"""
Integration tests for SchedulerAgent._schedule_course() and _backtrack().

These tests seed a minimal but realistic dataset (3 courses, guaranteed to fit),
run the scheduler end-to-end, and assert that all courses are placed and that
the DB matches the in-memory state.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database.db_setup as db_module


# ── helpers ────────────────────────────────────────────────────────────────

def seed_minimal(conn):
    """Insert 1 teacher, 1 group, 1 room, and 3 courses — all schedulable."""
    conn.execute(
        "INSERT INTO Teachers (name,email,available_days,preferred_time,subject) "
        "VALUES ('Dr. Test','t@test.tn','Monday,Tuesday,Wednesday,Thursday,Friday','08:00-10:00','Math')"
    )
    conn.execute(
        "INSERT INTO StudentGroups (group_name,program,year,group_size) VALUES ('G1','CS',1,20)"
    )
    conn.execute(
        "INSERT INTO Classrooms (room_name,capacity,equipment) VALUES ('Room1',30,'Projector')"
    )
    for name in ("CourseA", "CourseB", "CourseC"):
        cur = conn.execute(
            "INSERT INTO Courses (course_name,group_id,required_room_type) VALUES (?,1,'Standard')",
            (name,)
        )
        conn.execute(
            "INSERT INTO CourseTeachers (course_id,teacher_id) VALUES (?,1)",
            (cur.lastrowid,)
        )
    conn.commit()


# ── tests ──────────────────────────────────────────────────────────────────

def test_all_three_courses_scheduled(use_test_db):
    """Scheduler must place all 3 courses when slots and rooms are available."""
    conn = db_module.get_connection()
    seed_minimal(conn)
    conn.close()

    from timetable_model import TimetableModel
    model = TimetableModel(seed=42)
    model.scheduler.run_scheduling()

    assert model.scheduler.resolved_count == 3, (
        f"Expected 3 scheduled, got {model.scheduler.resolved_count}. "
        f"Conflicts: {model.scheduler.conflicts}"
    )
    assert model.scheduler.conflicts == [], (
        f"Unexpected conflicts: {model.scheduler.conflicts}"
    )


def test_db_matches_in_memory_schedule(use_test_db):
    """Rows written to Schedule must match the in-memory scheduled list."""
    conn = db_module.get_connection()
    seed_minimal(conn)
    conn.close()

    from timetable_model import TimetableModel
    model = TimetableModel(seed=42)
    model.scheduler.run_scheduling()

    conn = db_module.get_connection()
    db_sessions = conn.execute(
        "SELECT session_id FROM Schedule WHERE status='scheduled'"
    ).fetchall()
    conn.close()

    in_mem_ids = {s["session_id"] for s in model.scheduler.scheduled}
    db_ids     = {row[0] for row in db_sessions}

    assert db_ids == in_mem_ids, (
        f"DB session ids {db_ids} don't match in-memory ids {in_mem_ids}"
    )


def test_no_double_bookings(use_test_db):
    """No two sessions should share the same (teacher, day, time_slot)."""
    conn = db_module.get_connection()
    seed_minimal(conn)
    conn.close()

    from timetable_model import TimetableModel
    model = TimetableModel(seed=42)
    model.scheduler.run_scheduling()

    seen = set()
    for s in model.scheduler.scheduled:
        key = (s["teacher_id"], s["day"], s["time_slot"])
        assert key not in seen, f"Double-booking detected: {key}"
        seen.add(key)


def test_backtrack_resolves_tight_schedule(use_test_db):
    """
    With only 1 room and 1 teacher, 3 courses must still all be scheduled
    (each in a different slot). Backtracking should handle any ordering issues.
    """
    conn = db_module.get_connection()
    seed_minimal(conn)
    conn.close()

    from timetable_model import TimetableModel
    model = TimetableModel(seed=0)  # fixed seed for determinism
    model.scheduler.run_scheduling()

    assert model.scheduler.resolved_count == 3
    # Each course must land in a distinct slot
    slots = [(s["day"], s["time_slot"]) for s in model.scheduler.scheduled]
    assert len(slots) == len(set(slots)), "Courses share a time slot — conflict not resolved"
