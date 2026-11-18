"""AGENT: PreferenceAgent — teacher slot preference scorer"""
try:
    from mesa import Agent as _MesaAgent
    import inspect as _inspect
    _sig = _inspect.signature(_MesaAgent.__init__)
    _MESA3 = "unique_id" not in _sig.parameters
except Exception:
    _MESA3 = False

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

_MIN_SCORE = 0.1
_MAX_SCORE = 3.0


class _StandaloneBase:
    """Fallback base when Mesa model wiring is not available."""
    def __init__(self, model):
        self.model = model


try:
    from mesa import Agent as _MesaAgent

    class _CompatAgent(_MesaAgent):
        def __init__(self, model):
            try:
                super().__init__(model)
            except (AttributeError, TypeError):
                # Mesa 3.x with a bare MockModel — bypass Mesa registration
                _StandaloneBase.__init__(self, model)

except ImportError:
    _CompatAgent = _StandaloneBase


class PreferenceAgent(_CompatAgent):
    def __init__(self, model):
        super().__init__(model)
        self.log = []
        self._cache = {}
        self._load_scores()

    def _load_scores(self):
        conn = get_connection()
        rows = conn.execute(
            "SELECT teacher_id, day, time_slot, score FROM PreferenceScores"
        ).fetchall()
        conn.close()
        for tid, day, ts, score in rows:
            self._cache[(tid, day, ts)] = score

    def get_score(self, teacher_id, day, time_slot):
        return self._cache.get((teacher_id, day, time_slot), 1.0)

    def rank_slots(self, teacher_id, slots):
        return sorted(
            slots,
            key=lambda s: self.get_score(teacher_id, s[0], s[1]),
            reverse=True,
        )

    def record_used(self, teacher_id, day, time_slot, was_preferred, was_negotiated):
        key = (teacher_id, day, time_slot)
        score = self._cache.get(key, 1.0)
        if was_preferred and not was_negotiated:
            score = min(_MAX_SCORE, score + 0.2)
        elif was_negotiated:
            score = max(_MIN_SCORE, score - 0.1)
        self._cache[key] = score

    def update_scores(self):
        conn = get_connection()
        for (tid, day, ts), score in self._cache.items():
            conn.execute(
                """INSERT INTO PreferenceScores (teacher_id, day, time_slot, score)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(teacher_id, day, time_slot)
                   DO UPDATE SET score = excluded.score""",
                (tid, day, ts, score),
            )
        conn.commit()
        conn.close()
        self.log.append(
            f"[PreferenceAgent] Scores persisted ({len(self._cache)} entries)."
        )

    def step(self):
        self.update_scores()
