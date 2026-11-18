import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


class MockModel:
    def register_agent(self, agent): pass


def _seed_base(conn):
    conn.execute("INSERT INTO Teachers (name,email,available_days,preferred_time,subject) VALUES ('T1','t1@x.com','Monday','08:00-10:00','Math')")
    conn.execute("INSERT INTO StudentGroups (group_name,program,year,group_size) VALUES ('G1','CS',1,20)")
    conn.execute("INSERT INTO StudentGroups (group_name,program,year,group_size) VALUES ('G2','CS',2,20)")
    conn.execute("INSERT INTO Classrooms (room_name,capacity,equipment) VALUES ('R1',30,'Projector')")
    conn.execute("INSERT INTO Courses (course_name,group_id,required_room_type) VALUES ('CourseA',1,'Standard')")
    conn.execute("INSERT INTO Courses (course_name,group_id,required_room_type) VALUES ('CourseB',2,'Standard')")
    conn.commit()


def test_detects_teacher_double_booking(use_test_db):
    from agents.constraint_agent import ConstraintAgent
    conn = get_connection()
    _seed_base(conn)
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (1,1,1,'Monday','08:00-10:00','scheduled')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (2,1,1,'Monday','08:00-10:00','scheduled')")
    conn.commit(); conn.close()
    agent = ConstraintAgent(MockModel())
    agent.audit()
    assert any("TEACHER CONFLICT" in v for v in agent.violations)


def test_detects_room_double_booking(use_test_db):
    from agents.constraint_agent import ConstraintAgent
    conn = get_connection()
    _seed_base(conn)
    conn.execute("INSERT INTO Teachers (name,email,available_days,preferred_time,subject) VALUES ('T2','t2@x.com','Monday','08:00-10:00','Sci')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (1,1,1,'Monday','08:00-10:00','scheduled')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (2,2,1,'Monday','08:00-10:00','scheduled')")
    conn.commit(); conn.close()
    agent = ConstraintAgent(MockModel())
    agent.audit()
    assert any("ROOM CONFLICT" in v for v in agent.violations)


def test_detects_group_double_booking(use_test_db):
    from agents.constraint_agent import ConstraintAgent
    conn = get_connection()
    _seed_base(conn)
    conn.execute("INSERT INTO Classrooms (room_name,capacity,equipment) VALUES ('R2',30,'Projector')")
    conn.execute("INSERT INTO Teachers (name,email,available_days,preferred_time,subject) VALUES ('T2','t2@x.com','Monday','08:00-10:00','Sci')")
    conn.execute("INSERT INTO Courses (course_name,group_id,required_room_type) VALUES ('CourseC',1,'Standard')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (1,1,1,'Monday','08:00-10:00','scheduled')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (3,2,2,'Monday','08:00-10:00','scheduled')")
    conn.commit(); conn.close()
    agent = ConstraintAgent(MockModel())
    agent.audit()
    assert any("GROUP CONFLICT" in v for v in agent.violations)


def test_detects_capacity_violation(use_test_db):
    from agents.constraint_agent import ConstraintAgent
    conn = get_connection()
    _seed_base(conn)
    conn.execute("INSERT INTO Classrooms (room_name,capacity,equipment) VALUES ('TinyRoom',10,'Projector')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (1,1,2,'Monday','08:00-10:00','scheduled')")
    conn.commit(); conn.close()
    agent = ConstraintAgent(MockModel())
    agent.audit()
    assert any("CAPACITY VIOLATION" in v for v in agent.violations)


def test_no_violations_on_clean_schedule(use_test_db):
    from agents.constraint_agent import ConstraintAgent
    conn = get_connection()
    _seed_base(conn)
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (1,1,1,'Monday','08:00-10:00','scheduled')")
    conn.commit(); conn.close()
    agent = ConstraintAgent(MockModel())
    agent.audit()
    assert agent.violations == []


def test_violations_written_to_conflict_log(use_test_db):
    from agents.constraint_agent import ConstraintAgent
    conn = get_connection()
    _seed_base(conn)
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (1,1,1,'Monday','08:00-10:00','scheduled')")
    conn.execute("INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,status) VALUES (2,1,1,'Monday','08:00-10:00','scheduled')")
    conn.commit(); conn.close()
    agent = ConstraintAgent(MockModel())
    agent.audit()
    conn = get_connection()
    rows = conn.execute("SELECT description FROM ConflictLog WHERE resolved=0").fetchall()
    conn.close()
    assert len(rows) > 0
