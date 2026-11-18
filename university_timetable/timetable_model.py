"""MESA MODEL: TimetableModel v3 — fixed"""
from mesa import Model
import sys, os
sys.path.append(os.path.dirname(__file__))
from agents.teacher_agent import TeacherAgent
from agents.group_room_agents import GroupAgent, RoomAgent
from agents.scheduler_agent import SchedulerAgent
from agents.constraint_agent import ConstraintAgent
from agents.preference_agent import PreferenceAgent
from database.db_setup import get_connection

class TimetableModel(Model):
    def __init__(self, seed=None):
        super().__init__(seed=seed)
        self.teacher_agents = {}
        self.group_agents   = {}
        self.room_agents    = []
        self._load_agents()
        self._hydrate_booked_slots()       # FIX 1: sync in-memory state from DB
        self.preference_agent = PreferenceAgent(self)
        self.scheduler        = SchedulerAgent(self)
        self.constraint_agent = ConstraintAgent(self)

    def _load_agents(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT teacher_id,name,available_days,preferred_time,subject FROM Teachers")
        for row in c.fetchall():
            tid, name, avail, pref, subj = row
            self.teacher_agents[tid] = TeacherAgent(
                self, tid, name, avail, pref or "08:00-10:00", subj
            )
        c.execute("SELECT group_id,group_name,program,year,group_size FROM StudentGroups")
        for row in c.fetchall():
            gid, gname, prog, year, size = row
            self.group_agents[gid] = GroupAgent(self, gid, gname, prog, year, size)
        c.execute("SELECT room_id,room_name,capacity,equipment FROM Classrooms")
        for row in c.fetchall():
            rid, rname, cap, equip = row
            self.room_agents.append(RoomAgent(self, rid, rname, cap, equip or ""))
        conn.close()
        print(
            f"[Model] {len(self.teacher_agents)} teachers | "
            f"{len(self.group_agents)} groups | "
            f"{len(self.room_agents)} rooms"
        )

    def _hydrate_booked_slots(self):
        """
        FIX 1 — Read any existing scheduled sessions from the DB and replay
        them into each agent's in-memory booked_slots set.

        Without this, a second run (or a run that doesn't DELETE the schedule
        first) would have agents with empty booked_slots while the DB already
        contained committed sessions, allowing double-bookings on re-run.

        The SchedulerAgent clears the Schedule table at the start of
        run_scheduling(), so this only matters if the model is instantiated
        without immediately running a fresh schedule (e.g. dashboard queries).

        NOTE: the session_type column was introduced in schema v3. To guard
        against older DB files that lack it, we check for its presence first.
        """
        conn = get_connection()

        # Schema guard — check whether session_type column exists
        col_names = {row[1] for row in conn.execute("PRAGMA table_info(Schedule)").fetchall()}
        session_type_filter = "AND session_type = 'regular'" if "session_type" in col_names else ""

        sessions = conn.execute(
            f"""SELECT s.teacher_id, s.room_id, s.day, s.time_slot, c.group_id
               FROM Schedule s
               JOIN Courses c ON s.course_id = c.course_id
               WHERE s.status = 'scheduled'
                 {session_type_filter}"""
        ).fetchall()
        conn.close()

        teacher_slots = {}   # teacher_id → set of (day, time_slot)
        room_slots    = {}   # room_id    → set of (day, time_slot)
        group_slots   = {}   # group_id   → set of (day, time_slot)

        for teacher_id, room_id, day, time_slot, group_id in sessions:
            teacher_slots.setdefault(teacher_id, set()).add((day, time_slot))
            room_slots.setdefault(room_id,    set()).add((day, time_slot))
            group_slots.setdefault(group_id,  set()).add((day, time_slot))

        for tid, agent in self.teacher_agents.items():
            agent.booked_slots.update(teacher_slots.get(tid, set()))

        for agent in self.room_agents:
            agent.booked_slots.update(room_slots.get(agent.room_id, set()))

        for gid, agent in self.group_agents.items():
            agent.booked_slots.update(group_slots.get(gid, set()))

        total = sum(len(v) for v in teacher_slots.values())
        if total:
            print(f"[Model] Hydrated {total} existing session(s) into agent state.")

    def get_teacher_agent(self, tid): return self.teacher_agents.get(tid)
    def get_group_agent(self, gid):   return self.group_agents.get(gid)

    def find_available_room(self, req_type, group_size, day, time_slot):
        candidates = [
            r for r in self.room_agents
            if r.is_available(day, time_slot) and r.meets_requirements(req_type, group_size)
        ]
        candidates.sort(key=lambda r: r.capacity)
        return candidates[0] if candidates else None

    def step(self):
        for a in self.teacher_agents.values(): a.step()
        for a in self.group_agents.values():   a.step()
        for a in self.room_agents:             a.step()
        self.scheduler.step()
        self.constraint_agent.step()
        self.preference_agent.step()

    def get_all_logs(self):
        logs = list(self.scheduler.log)
        logs.extend(self.constraint_agent.log)
        logs.extend(self.preference_agent.log)
        for a in self.teacher_agents.values(): logs.extend(a.log)
        for a in self.group_agents.values():   logs.extend(a.log)
        return logs
