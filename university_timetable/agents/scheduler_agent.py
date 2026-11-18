"""
AGENT: SchedulerAgent v3 — fixed
Changes from v2:
  - MAX_RETRIES raised from 5 → 12
  - teacher_ids shuffled per course to prevent systematic bias toward
    the first teacher in GROUP_CONCAT order
  - Backtracking: if a course exhausts all slots, the scheduler attempts
    to swap a previously committed session out of the conflicting slot
    before giving up entirely
"""

from mesa import Agent
import sys, os, random
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

MAX_RETRIES = 12   # FIX 2a: was 5 — gives more room before backtracking kicks in


class SchedulerAgent(Agent):
    def __init__(self, model):
        super().__init__(model)
        self.scheduled         = []
        self.conflicts         = []
        self.log               = []
        self.total_courses     = 0
        self.resolved_count    = 0
        self.negotiation_count = 0
        self.backtrack_count   = 0

    # ── public entry point ────────────────────────────────────────────────────

    def run_scheduling(self):
        self.log.append("[SchedulerAgent] Starting scheduling pipeline...")
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT co.course_id, co.course_name, co.group_id,
                   co.required_room_type, g.group_size,
                   GROUP_CONCAT(ct.teacher_id) as teacher_ids
            FROM Courses co
            JOIN StudentGroups g ON co.group_id = g.group_id
            LEFT JOIN CourseTeachers ct ON co.course_id = ct.course_id
            GROUP BY co.course_id
        """)
        courses = c.fetchall()
        conn.close()

        self.total_courses = len(courses)

        # Clear old schedule
        conn = get_connection()
        conn.execute("DELETE FROM Schedule")
        conn.execute("DELETE FROM ConflictLog")
        conn.commit()
        conn.close()

        self.log.append(f"[SchedulerAgent] {self.total_courses} courses to schedule.")

        for course in courses:
            course_id, course_name, group_id, req_room, group_size, teacher_ids_str = course
            teacher_ids = [int(x) for x in (teacher_ids_str or "").split(",") if x]
            # FIX 2b: shuffle to prevent first-teacher bias across runs
            random.shuffle(teacher_ids)
            self._schedule_course(course_id, course_name, group_id, req_room, group_size, teacher_ids)

        self.log.append(
            f"[SchedulerAgent] Done — {self.resolved_count}/{self.total_courses} scheduled, "
            f"{len(self.conflicts)} conflicts, "
            f"{self.negotiation_count} negotiations, "
            f"{self.backtrack_count} backtracks."
        )

    # ── core scheduling loop ──────────────────────────────────────────────────

    def _schedule_course(self, course_id, course_name, group_id, req_room, group_size, teacher_ids):
        group_agent = self.model.get_group_agent(group_id)
        if not group_agent:
            self.log.append(f"[SchedulerAgent] ERROR: No GroupAgent for course {course_name}")
            return

        if not teacher_ids:
            self.log.append(f"[SchedulerAgent] ERROR: No teachers assigned to {course_name}")
            return

        excluded_slots = []
        preferred_hint = None
        attempts       = 0

        while attempts < MAX_RETRIES:
            attempts += 1

            proposed       = None
            chosen_teacher = None

            for tid in teacher_ids:
                teacher_agent = self.model.get_teacher_agent(tid)
                if not teacher_agent:
                    continue
                if attempts == 1:
                    slot = teacher_agent.propose_slot(course_id, course_name, group_size)
                else:
                    slot = teacher_agent.negotiate(
                        course_id, course_name, excluded_slots,
                        preferred_hint=preferred_hint,
                    )
                    self.negotiation_count += 1
                if slot:
                    proposed       = slot
                    chosen_teacher = teacher_agent
                    break

            if not proposed:
                self.log.append(f"[SchedulerAgent] All teachers unavailable for {course_name}")
                break

            day, time_slot = proposed

            # Group availability check
            group_ok, group_hint = group_agent.check_and_hint(day, time_slot)
            if not group_ok:
                self.log.append(
                    f"[SchedulerAgent] Group conflict for {course_name} at ({day},{time_slot})"
                )
                excluded_slots.append((day, time_slot))
                preferred_hint = group_hint
                continue

            # Room availability check
            room_agent = self.model.find_available_room(req_room, group_size, day, time_slot)
            if not room_agent:
                self.log.append(
                    f"[SchedulerAgent] No room for {course_name} at ({day},{time_slot})"
                )
                excluded_slots.append((day, time_slot))
                preferred_hint = self._get_room_hint(req_room, group_size, day, time_slot)
                continue

            # All checks passed — commit
            self._commit(
                course_id, course_name, group_id, req_room, group_size,
                chosen_teacher, group_agent, room_agent, day, time_slot
            )
            return

        # ── FIX 3: backtracking ───────────────────────────────────────────────
        # Normal negotiation exhausted. Try to find any previously scheduled
        # session that blocks this course and swap it to an alternative slot.
        self.log.append(
            f"[SchedulerAgent] Negotiation exhausted for {course_name} — attempting backtrack..."
        )
        if self._backtrack(course_id, course_name, group_id, req_room, group_size, teacher_ids):
            return  # backtrack succeeded

        # Nothing worked — record as unresolvable conflict
        msg = f"Could not schedule '{course_name}' after {MAX_RETRIES} attempts (backtrack failed)."
        self.conflicts.append(msg)
        self.log.append(f"[SchedulerAgent] ✗ CONFLICT: {msg}")
        conn = get_connection()
        conn.execute("INSERT INTO ConflictLog (description,resolved) VALUES (?,0)", (msg,))
        conn.commit()
        conn.close()

    # ── backtracking ──────────────────────────────────────────────────────────

    def _backtrack(self, course_id, course_name, group_id, req_room, group_size, teacher_ids):
        """
        FIX 3 — Backtracking strategy:
        For each already-committed session that shares a teacher, group, or room
        with this course, try to move that blocker to one of its own alternative
        slots, then retry placing the current course in the freed slot.

        This handles the common case where scheduling order causes a later course
        to run out of options because an earlier course grabbed a slot it didn't
        strictly need.
        """
        group_agent = self.model.get_group_agent(group_id)

        # Gather candidate blocker sessions from the in-memory scheduled list
        # (faster than re-querying the DB for every backtrack attempt)
        blocker_candidates = []
        for sess in self.scheduled:
            # A session is a potential blocker if it uses one of our teachers
            # or our group's time slots
            if sess["teacher_id"] in teacher_ids or sess["group_id"] == group_id:
                blocker_candidates.append(sess)

        for blocker in blocker_candidates:
            b_teacher_agent = self.model.get_teacher_agent(blocker["teacher_id"])
            b_group_agent   = self.model.get_group_agent(blocker["group_id"])
            b_room_agent    = self._get_room_agent(blocker["room_id"])

            if not (b_teacher_agent and b_group_agent and b_room_agent):
                continue

            blocked_slot = (blocker["day"], blocker["time_slot"])

            # Find an alternative slot for the blocker
            alt = self._find_alternative_slot(
                blocker["course_id"], blocker["course_name"],
                blocker["group_id"], blocker["req_room_type"], blocker["group_size"],
                blocker["teacher_ids"],
                exclude=[blocked_slot],
            )
            if alt is None:
                continue  # blocker has nowhere else to go

            alt_day, alt_time, alt_teacher, alt_room = alt

            # Tentatively unbook the blocker
            b_teacher_agent.booked_slots.discard(blocked_slot)
            b_group_agent.booked_slots.discard(blocked_slot)
            b_room_agent.booked_slots.discard(blocked_slot)

            # Try to place the current course in the now-free slot
            for tid in teacher_ids:
                t_agent = self.model.get_teacher_agent(tid)
                if not t_agent or not t_agent.is_slot_free(blocked_slot[0], blocked_slot[1]):
                    continue
                if not group_agent.is_free(blocked_slot[0], blocked_slot[1]):
                    continue
                room = self.model.find_available_room(req_room, group_size, *blocked_slot)
                if not room:
                    continue

                # Place current course in freed slot
                self._commit(
                    course_id, course_name, group_id, req_room, group_size,
                    t_agent, group_agent, room, *blocked_slot
                )

                # Re-commit blocker at its new alternative slot
                alt_group_agent = self.model.get_group_agent(blocker["group_id"])
                self._commit(
                    blocker["course_id"], blocker["course_name"],
                    blocker["group_id"], blocker["req_room_type"], blocker["group_size"],
                    alt_teacher, alt_group_agent, alt_room, alt_day, alt_time,
                    is_rescheduled_blocker=True,
                    old_session_id=blocker["session_id"],
                )

                self.backtrack_count += 1
                self.log.append(
                    f"[SchedulerAgent] ↺ Backtrack: moved '{blocker['course_name']}' "
                    f"from ({blocked_slot}) → ({alt_day},{alt_time}) "
                    f"to free slot for '{course_name}'"
                )
                return True

            # Could not place current course in freed slot — restore blocker
            b_teacher_agent.booked_slots.add(blocked_slot)
            b_group_agent.booked_slots.add(blocked_slot)
            b_room_agent.booked_slots.add(blocked_slot)

        return False

    def _find_alternative_slot(self, course_id, course_name, group_id, req_room, group_size, teacher_ids, exclude):
        """Return (day, time_slot, teacher_agent, room_agent) or None."""
        group_agent = self.model.get_group_agent(group_id)
        if not group_agent:
            return None
        for tid in teacher_ids:
            t = self.model.get_teacher_agent(tid)
            if not t:
                continue
            for slot in t.get_available_slots():
                if slot in exclude:
                    continue
                day, ts = slot
                if not group_agent.is_free(day, ts):
                    continue
                room = self.model.find_available_room(req_room, group_size, day, ts)
                if room:
                    return day, ts, t, room
        return None

    # ── commit helpers ────────────────────────────────────────────────────────

    def _commit(
        self, course_id, course_name, group_id, req_room, group_size,
        teacher_agent, group_agent, room_agent, day, time_slot,
        is_rescheduled_blocker=False, old_session_id=None,
    ):
        """Book slots in-memory and persist to DB."""
        teacher_agent.book_slot(day, time_slot)
        group_agent.accept_slot(day, time_slot, course_name)
        room_agent.book(day, time_slot, course_name)

        conn = get_connection()

        if is_rescheduled_blocker and old_session_id is not None:
            # Update the existing DB row instead of inserting a new one
            conn.execute(
                "UPDATE Schedule SET teacher_id=?,room_id=?,day=?,time_slot=? WHERE session_id=?",
                (teacher_agent.teacher_id, room_agent.room_id, day, time_slot, old_session_id),
            )
            conn.commit()
            conn.close()
            # Update the in-memory record too
            for sess in self.scheduled:
                if sess["session_id"] == old_session_id:
                    sess.update({"teacher": teacher_agent.name, "day": day,
                                 "time_slot": time_slot, "room": room_agent.room_name,
                                 "teacher_id": teacher_agent.teacher_id,
                                 "room_id": room_agent.room_id})
                    break
            return

        cur = conn.execute(
            """INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status)
               VALUES (?,?,?,?,?,'scheduled')""",
            (course_id, teacher_agent.teacher_id, room_agent.room_id, day, time_slot),
        )
        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        record = {
            "session_id":    session_id,
            "course_id":     course_id,
            "course_name":   course_name,
            "group_id":      group_id,
            "req_room_type": req_room,
            "group_size":    group_size,
            "teacher_id":    teacher_agent.teacher_id,
            "teacher_ids":   [teacher_agent.teacher_id],
            "room_id":       room_agent.room_id,
            "teacher":       teacher_agent.name,
            "day":           day,
            "time_slot":     time_slot,
            "room":          room_agent.room_name,
        }
        self.scheduled.append(record)
        self.resolved_count += 1
        self.log.append(
            f"[SchedulerAgent] ✓ {course_name} → {day} {time_slot} "
            f"| {teacher_agent.name} | {room_agent.room_name}"
        )

    # ── utility ───────────────────────────────────────────────────────────────

    def _get_room_hint(self, req_type, group_size, day, time_slot):
        for r in self.model.room_agents:
            ok, hint = r.check_and_hint(req_type, group_size, day, time_slot)
            if hint:
                return hint
        return None

    def _get_room_agent(self, room_id):
        for r in self.model.room_agents:
            if r.room_id == room_id:
                return r
        return None

    def step(self):
        self.run_scheduling()
