"""AGENT: ConstraintAgent — post-scheduling constraint auditor"""
from mesa import Agent
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


class ConstraintAgent(Agent):
    def __init__(self, model):
        super().__init__(model)
        self.violations = []
        self.log = []

    def audit(self):
        self.violations = []
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT s.session_id, s.teacher_id, s.room_id, s.day, s.time_slot,
                   co.group_id, r.capacity, g.group_size,
                   t.name, r.room_name, co.course_name
            FROM Schedule s
            JOIN Courses co ON s.course_id = co.course_id
            JOIN StudentGroups g ON co.group_id = g.group_id
            JOIN Classrooms r ON s.room_id = r.room_id
            JOIN Teachers t ON s.teacher_id = t.teacher_id
            WHERE s.status = 'scheduled'
        """)
        sessions = c.fetchall()
        conn.close()

        self._check_teacher_double_booking(sessions)
        self._check_room_double_booking(sessions)
        self._check_group_double_booking(sessions)
        self._check_capacity_violations(sessions)

        if self.violations:
            conn = get_connection()
            for v in self.violations:
                conn.execute(
                    "INSERT INTO ConflictLog (description, resolved) VALUES (?, 0)", (v,)
                )
            conn.commit()
            conn.close()

        self.log.append(
            f"[ConstraintAgent] Audit done — {len(self.violations)} violation(s)."
        )

    def _check_teacher_double_booking(self, sessions):
        seen = {}
        for sid, tid, rid, day, ts, gid, cap, gsize, tname, rname, cname in sessions:
            key = (tid, day, ts)
            if key in seen:
                self._add(f"TEACHER CONFLICT: {tname} double-booked on {day} {ts} (sessions {seen[key]} & {sid})")
            else:
                seen[key] = sid

    def _check_room_double_booking(self, sessions):
        seen = {}
        for sid, tid, rid, day, ts, gid, cap, gsize, tname, rname, cname in sessions:
            key = (rid, day, ts)
            if key in seen:
                self._add(f"ROOM CONFLICT: {rname} double-booked on {day} {ts} (sessions {seen[key]} & {sid})")
            else:
                seen[key] = sid

    def _check_group_double_booking(self, sessions):
        seen = {}
        for sid, tid, rid, day, ts, gid, cap, gsize, tname, rname, cname in sessions:
            key = (gid, day, ts)
            if key in seen:
                self._add(f"GROUP CONFLICT: Group {gid} double-booked on {day} {ts} (sessions {seen[key]} & {sid})")
            else:
                seen[key] = sid

    def _check_capacity_violations(self, sessions):
        for sid, tid, rid, day, ts, gid, cap, gsize, tname, rname, cname in sessions:
            if gsize > cap:
                self._add(f"CAPACITY VIOLATION: {cname} in {rname} — group size {gsize} > capacity {cap} (session {sid})")

    def _add(self, msg):
        self.violations.append(msg)
        self.log.append(f"[ConstraintAgent] ✗ {msg}")

    def step(self):
        self.audit()
