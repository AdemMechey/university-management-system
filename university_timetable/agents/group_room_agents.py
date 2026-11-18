"""AGENTS: GroupAgent + RoomAgent — Mesa 3.x"""
from mesa import Agent

ROOM_TYPE_MAP = {"Lab":["Computers"], "Amphi":["Microphone"], "Standard":[]}

_DAYS  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
_TIMES = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]

class GroupAgent(Agent):
    def __init__(self, model, group_id, group_name, program, year, group_size):
        super().__init__(model)
        self.group_id    = group_id
        self.group_name  = group_name
        self.program     = program
        self.year        = year
        self.group_size  = group_size
        self.booked_slots = set()
        self.log          = []

    def is_free(self, day, time_slot):
        return (day, time_slot) not in self.booked_slots

    def accept_slot(self, day, time_slot, course_name):
        if self.is_free(day, time_slot):
            self.booked_slots.add((day, time_slot))
            self.log.append(f"[GroupAgent:{self.group_name}] Accepted ({day},{time_slot}) for {course_name}")
            return True
        return False

    def check_and_hint(self, day, time_slot):
        """Return (is_free, hint). hint is the next free slot after the rejected one."""
        if self.is_free(day, time_slot):
            return True, None
        try:
            di = _DAYS.index(day)
            ti = _TIMES.index(time_slot)
        except ValueError:
            return False, None
        for d_idx in range(di, len(_DAYS)):
            start_t = ti + 1 if d_idx == di else 0
            for t_idx in range(start_t, len(_TIMES)):
                candidate = (_DAYS[d_idx], _TIMES[t_idx])
                if candidate not in self.booked_slots:
                    return False, candidate
        return False, None

    def step(self):
        pass


class RoomAgent(Agent):
    def __init__(self, model, room_id, room_name, capacity, equipment):
        super().__init__(model)
        self.room_id      = room_id
        self.room_name    = room_name
        self.capacity     = capacity
        self.equipment    = [e.strip() for e in equipment.split(",")] if equipment else []
        self.booked_slots = set()
        self.log          = []

    def is_available(self, day, time_slot):
        return (day, time_slot) not in self.booked_slots

    def meets_requirements(self, required_room_type, group_size):
        if group_size > self.capacity:
            return False
        for req in ROOM_TYPE_MAP.get(required_room_type, []):
            if req not in self.equipment:
                return False
        return True

    def book(self, day, time_slot, course_name):
        if self.is_available(day, time_slot):
            self.booked_slots.add((day, time_slot))
            return True
        return False

    def check_and_hint(self, required_room_type, group_size, day, time_slot):
        """Return (available, hint). hint is next free slot, or None if wrong type/capacity."""
        if not self.meets_requirements(required_room_type, group_size):
            return False, None
        if self.is_available(day, time_slot):
            return True, None
        try:
            di = _DAYS.index(day)
            ti = _TIMES.index(time_slot)
        except ValueError:
            return False, None
        for d_idx in range(di, len(_DAYS)):
            start_t = ti + 1 if d_idx == di else 0
            for t_idx in range(start_t, len(_TIMES)):
                candidate = (_DAYS[d_idx], _TIMES[t_idx])
                if candidate not in self.booked_slots:
                    return False, candidate
        return False, None

    def step(self):
        pass
