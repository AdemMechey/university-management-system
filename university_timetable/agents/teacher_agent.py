"""AGENT: TeacherAgent — Mesa 3.x (fixed)"""
from mesa import Agent

TIME_SLOTS = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]


class TeacherAgent(Agent):
    def __init__(self, model, teacher_id, name, available_days, preferred_time, subject):
        super().__init__(model)
        self.teacher_id     = teacher_id
        self.name           = name
        self.available_days = [d.strip() for d in available_days.split(",")]
        self.preferred_time = preferred_time
        self.subject        = subject
        self.booked_slots   = set()
        self.log            = []

    def get_available_slots(self):
        return [
            (d, t) for d in self.available_days for t in TIME_SLOTS
            if (d, t) not in self.booked_slots
        ]

    def is_slot_free(self, day, time_slot):
        """Used by the backtracking logic in SchedulerAgent."""
        return (day, time_slot) not in self.booked_slots

    def propose_slot(self, course_id, course_name, group_size):
        available = self.get_available_slots()
        if not available:
            return None
        pref = getattr(self.model, "preference_agent", None)
        if pref:
            ranked = pref.rank_slots(self.teacher_id, available)
        else:
            preferred = [(d, t) for (d, t) in available if t == self.preferred_time]
            ranked = preferred + [s for s in available if s not in preferred]
        chosen = ranked[0]
        if pref:
            pref.record_used(
                self.teacher_id, chosen[0], chosen[1],
                was_preferred=(chosen[1] == self.preferred_time),
                was_negotiated=False,
            )
        self.log.append(
            f"[TeacherAgent:{self.name}] Proposes ({chosen[0]},{chosen[1]}) for {course_name}"
        )
        return chosen

    def book_slot(self, day, time_slot):
        if (day, time_slot) not in self.booked_slots:
            self.booked_slots.add((day, time_slot))
            return True
        return False

    def negotiate(self, course_id, course_name, excluded_slots, preferred_hint=None):
        available = [
            (d, t) for (d, t) in self.get_available_slots()
            if (d, t) not in excluded_slots
        ]
        if not available:
            return None
        if preferred_hint and preferred_hint in available:
            chosen = preferred_hint
        else:
            pref = getattr(self.model, "preference_agent", None)
            if pref:
                ranked = pref.rank_slots(self.teacher_id, available)
            else:
                ranked = available
            chosen = ranked[0]
        pref = getattr(self.model, "preference_agent", None)
        if pref:
            pref.record_used(
                self.teacher_id, chosen[0], chosen[1],
                was_preferred=(chosen[1] == self.preferred_time),
                was_negotiated=True,
            )
        self.log.append(
            f"[TeacherAgent:{self.name}] Negotiated → ({chosen[0]},{chosen[1]}) for {course_name}"
        )
        return chosen

    def step(self):
        pass
