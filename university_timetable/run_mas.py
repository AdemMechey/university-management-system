"""RUN_MAS.PY — University Timetabling MAS entry point"""
import sys, os
sys.path.append(os.path.dirname(__file__))
from database.db_setup import create_tables, seed_data
from timetable_model import TimetableModel

def run():
    print("="*60)
    print("  UNIVERSITY TIMETABLING — MULTI-AGENT SYSTEM")
    print("="*60)
    create_tables()
    seed_data()
    print("\n[Mesa] Initializing agents...")
    model = TimetableModel()
    print("[Mesa] Running simulation step...")
    model.step()
    s = model.scheduler
    print(f"\n{'='*60}")
    print(f"  Scheduled   : {s.resolved_count}/{s.total_courses}")
    print(f"  Conflicts   : {len(s.conflicts)}")
    print(f"  Negotiations: {s.negotiation_count}")
    print(f"{'='*60}")
    for sess in s.scheduled:
        print(f"  {sess['day']:12} {sess['time_slot']}  {sess['course_name']:25} {sess['teacher']:22} {sess['room']}")
    if s.conflicts:
        print("\n  CONFLICTS:")
        for c in s.conflicts: print(f"  ✗ {c}")
    print(f"\n  Dashboard: python -m streamlit run dashboard/app.py")
    print("="*60)

if __name__ == "__main__":
    run()
