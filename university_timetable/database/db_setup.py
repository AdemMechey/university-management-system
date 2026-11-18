"""
DATABASE SETUP v3 — University Timetabling MAS
New features:
  - Account approval workflow (admin must approve new registrations)
  - Session reschedule requests (professors & students can request changes)
  - Catch-up sessions (scheduling makeup/extra sessions)
"""

import sqlite3, os, hashlib, secrets

DB_PATH = os.path.join(os.path.dirname(__file__), "timetable.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def hash_password(p, salt=None):
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt.
    Returns 'salt$hash' so the salt is stored alongside the hash.
    If salt is provided (for verification), uses it instead of generating one.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 260_000)
    return f"{salt}${dk.hex()}"

def verify_password(p, stored):
    """Verify a plaintext password against a stored 'salt$hash' value.
    Also accepts legacy bare SHA-256 hashes (no '$') for backwards compatibility.
    """
    if "$" not in stored:
        # Legacy bare SHA-256 — still accept but don't upgrade here
        return hashlib.sha256(p.encode()).hexdigest() == stored
    salt, _ = stored.split("$", 1)
    return hash_password(p, salt) == stored

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS Users (
        user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role          TEXT NOT NULL DEFAULT 'student',
        status        TEXT NOT NULL DEFAULT 'pending',
        teacher_id    INTEGER,
        group_id      INTEGER,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS Teachers (
        teacher_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT NOT NULL,
        email          TEXT,
        available_days TEXT NOT NULL DEFAULT 'Monday,Tuesday,Wednesday,Thursday,Friday',
        preferred_time TEXT DEFAULT '08:00-10:00',
        subject        TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS StudentGroups (
        group_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name  TEXT NOT NULL,
        program     TEXT NOT NULL,
        year        INTEGER NOT NULL,
        group_size  INTEGER NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS Classrooms (
        room_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name  TEXT NOT NULL,
        capacity   INTEGER NOT NULL,
        equipment  TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS Courses (
        course_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name        TEXT NOT NULL,
        group_id           INTEGER,
        required_room_type TEXT DEFAULT 'Standard',
        duration_slots     INTEGER DEFAULT 1,
        FOREIGN KEY (group_id) REFERENCES StudentGroups(group_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS CourseTeachers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id  INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        FOREIGN KEY (course_id)  REFERENCES Courses(course_id),
        FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id),
        UNIQUE(course_id, teacher_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS Schedule (
        session_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id    INTEGER,
        teacher_id   INTEGER,
        room_id      INTEGER,
        day          TEXT,
        time_slot    TEXT,
        specific_date TEXT,
        status       TEXT DEFAULT 'scheduled',
        session_type TEXT DEFAULT 'regular',
        notes        TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id)  REFERENCES Courses(course_id),
        FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id),
        FOREIGN KEY (room_id)    REFERENCES Classrooms(room_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ConflictLog (
        conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        resolved    INTEGER DEFAULT 0,
        timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS PreferenceScores (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        day        TEXT NOT NULL,
        time_slot  TEXT NOT NULL,
        score      REAL NOT NULL DEFAULT 1.0,
        UNIQUE(teacher_id, day, time_slot),
        FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS RescheduleRequests (
        request_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id        INTEGER NOT NULL,
        requested_by      INTEGER NOT NULL,
        requested_by_role TEXT NOT NULL,
        reason            TEXT NOT NULL,
        proposed_day      TEXT,
        proposed_time     TEXT,
        proposed_exact_date TEXT,
        status            TEXT NOT NULL DEFAULT 'pending',
        admin_note        TEXT,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at       TIMESTAMP,
        FOREIGN KEY (session_id)   REFERENCES Schedule(session_id),
        FOREIGN KEY (requested_by) REFERENCES Users(user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS CatchupRequests (
        catchup_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id         INTEGER NOT NULL,
        teacher_id        INTEGER NOT NULL,
        requested_by      INTEGER NOT NULL,
        requested_by_role TEXT NOT NULL,
        reason            TEXT NOT NULL,
        preferred_day     TEXT,
        preferred_time    TEXT,
        preferred_exact_date TEXT,
        status            TEXT NOT NULL DEFAULT 'pending',
        session_id        INTEGER,
        admin_note        TEXT,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at       TIMESTAMP,
        FOREIGN KEY (course_id)    REFERENCES Courses(course_id),
        FOREIGN KEY (teacher_id)   REFERENCES Teachers(teacher_id),
        FOREIGN KEY (requested_by) REFERENCES Users(user_id),
        FOREIGN KEY (session_id)   REFERENCES Schedule(session_id)
    )""")

    conn.commit()
    conn.close()
    print("[DB] Tables created.")

# ── Auth ─────────────────────────────────────────────────────

def register_user(name, email, password, role="student", teacher_id=None, group_id=None, auto_approve=False):
    conn = get_connection()
    status = "approved" if (role == "admin" or auto_approve) else "pending"
    try:
        conn.execute("""INSERT INTO Users (name,email,password_hash,role,status,teacher_id,group_id)
                        VALUES (?,?,?,?,?,?,?)""",
                     (name, email, hash_password(password), role, status, teacher_id, group_id))
        conn.commit()
        return True, status
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()

def login_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT user_id,name,email,role,status,teacher_id,group_id,password_hash
                 FROM Users WHERE email=?""",
              (email,))
    row = c.fetchone()
    conn.close()
    if row and verify_password(password, row[7]):
        return {"user_id": row[0], "name": row[1], "email": row[2],
                "role": row[3], "status": row[4], "teacher_id": row[5], "group_id": row[6]}
    return None

# ── User Management ───────────────────────────────────────────

def get_pending_users():
    conn = get_connection()
    rows = conn.execute("""SELECT user_id,name,email,role,created_at FROM Users
                           WHERE status='pending' ORDER BY created_at""").fetchall()
    conn.close()
    return rows

def get_all_users():
    conn = get_connection()
    rows = conn.execute("""SELECT user_id,name,email,role,status,created_at FROM Users
                           ORDER BY created_at DESC""").fetchall()
    conn.close()
    return rows

def approve_user(user_id):
    conn = get_connection()
    conn.execute("UPDATE Users SET status='approved' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def reject_user(user_id):
    conn = get_connection()
    conn.execute("UPDATE Users SET status='rejected' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM Users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ── CRUD: Teachers ────────────────────────────────────────────

def get_all_teachers():
    conn = get_connection()
    df_rows = conn.execute("SELECT * FROM Teachers ORDER BY name").fetchall()
    conn.close()
    return df_rows

def add_teacher(name, email, available_days, preferred_time, subject):
    conn = get_connection()
    conn.execute("INSERT INTO Teachers (name,email,available_days,preferred_time,subject) VALUES (?,?,?,?,?)",
                 (name, email, available_days, preferred_time, subject))
    conn.commit()
    conn.close()

def update_teacher(teacher_id, name, email, available_days, preferred_time, subject):
    conn = get_connection()
    conn.execute("""UPDATE Teachers SET name=?,email=?,available_days=?,preferred_time=?,subject=?
                    WHERE teacher_id=?""",
                 (name, email, available_days, preferred_time, subject, teacher_id))
    conn.commit()
    conn.close()

def delete_teacher(teacher_id):
    conn = get_connection()
    conn.execute("DELETE FROM CourseTeachers WHERE teacher_id=?", (teacher_id,))
    conn.execute("DELETE FROM Teachers WHERE teacher_id=?", (teacher_id,))
    conn.commit()
    conn.close()

# ── CRUD: Classrooms ──────────────────────────────────────────

def add_classroom(room_name, capacity, equipment):
    conn = get_connection()
    conn.execute("INSERT INTO Classrooms (room_name,capacity,equipment) VALUES (?,?,?)",
                 (room_name, capacity, equipment))
    conn.commit()
    conn.close()

def update_classroom(room_id, room_name, capacity, equipment):
    conn = get_connection()
    conn.execute("UPDATE Classrooms SET room_name=?,capacity=?,equipment=? WHERE room_id=?",
                 (room_name, capacity, equipment, room_id))
    conn.commit()
    conn.close()

def delete_classroom(room_id):
    conn = get_connection()
    conn.execute("DELETE FROM Classrooms WHERE room_id=?", (room_id,))
    conn.commit()
    conn.close()

# ── CRUD: Courses ─────────────────────────────────────────────

def add_course(course_name, group_id, required_room_type, teacher_ids):
    conn = get_connection()
    cur = conn.execute("INSERT INTO Courses (course_name,group_id,required_room_type) VALUES (?,?,?)",
                       (course_name, group_id, required_room_type))
    course_id = cur.lastrowid
    for tid in teacher_ids:
        conn.execute("INSERT OR IGNORE INTO CourseTeachers (course_id,teacher_id) VALUES (?,?)",
                     (course_id, tid))
    conn.commit()
    conn.close()

def update_course(course_id, course_name, group_id, required_room_type, teacher_ids):
    conn = get_connection()
    conn.execute("UPDATE Courses SET course_name=?,group_id=?,required_room_type=? WHERE course_id=?",
                 (course_name, group_id, required_room_type, course_id))
    conn.execute("DELETE FROM CourseTeachers WHERE course_id=?", (course_id,))
    for tid in teacher_ids:
        conn.execute("INSERT OR IGNORE INTO CourseTeachers (course_id,teacher_id) VALUES (?,?)",
                     (course_id, tid))
    conn.commit()
    conn.close()

def delete_course(course_id):
    conn = get_connection()
    conn.execute("DELETE FROM CourseTeachers WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM Schedule WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM Courses WHERE course_id=?", (course_id,))
    conn.commit()
    conn.close()

# ── Reschedule Requests ───────────────────────────────────────

def submit_reschedule_request(session_id, user_id, role, reason, proposed_day=None, proposed_time=None, proposed_exact_date=None):
    conn = get_connection()
    conn.execute("""INSERT INTO RescheduleRequests
                    (session_id,requested_by,requested_by_role,reason,proposed_day,proposed_time,proposed_exact_date)
                    VALUES (?,?,?,?,?,?,?)""",
                 (session_id, user_id, role, reason, proposed_day, proposed_time, proposed_exact_date))
    conn.commit()
    conn.close()

def get_reschedule_requests(status=None):
    conn = get_connection()
    query = """
        SELECT rr.request_id, rr.session_id, rr.reason,
               rr.proposed_day, rr.proposed_time, rr.proposed_exact_date, rr.status,
               rr.admin_note, rr.created_at, rr.requested_by_role,
               u.name as requester_name,
               c.course_name, g.group_name,
               t.name as teacher_name,
               s.day as current_day, s.time_slot as current_time, s.specific_date as current_exact_date,
               r.room_name
        FROM RescheduleRequests rr
        JOIN Users u ON rr.requested_by = u.user_id
        JOIN Schedule s ON rr.session_id = s.session_id
        JOIN Courses c ON s.course_id = c.course_id
        JOIN StudentGroups g ON c.group_id = g.group_id
        JOIN Teachers t ON s.teacher_id = t.teacher_id
        JOIN Classrooms r ON s.room_id = r.room_id
    """
    params = []
    if status:
        query += " WHERE rr.status = ?"
        params.append(status)
    query += " ORDER BY rr.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows

def approve_reschedule(request_id, new_day, new_time, new_exact_date=None, admin_note=""):
    conn = get_connection()
    row = conn.execute("SELECT session_id, proposed_day, proposed_time, proposed_exact_date FROM RescheduleRequests WHERE request_id=?",
                       (request_id,)).fetchone()
    if row:
        session_id = row[0]
        day = new_day or row[1]
        time = new_time or row[2]
        exact_date = new_exact_date or row[3]
        conn.execute("UPDATE Schedule SET day=?, time_slot=?, specific_date=? WHERE session_id=?", (day, time, exact_date, session_id))
        conn.execute("""UPDATE RescheduleRequests SET status='approved', admin_note=?,
                        resolved_at=CURRENT_TIMESTAMP WHERE request_id=?""",
                     (admin_note, request_id))
        conn.commit()
    conn.close()

def reject_reschedule(request_id, admin_note=""):
    conn = get_connection()
    conn.execute("""UPDATE RescheduleRequests SET status='rejected', admin_note=?,
                    resolved_at=CURRENT_TIMESTAMP WHERE request_id=?""",
                 (admin_note, request_id))
    conn.commit()
    conn.close()

def get_my_reschedule_requests(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT rr.request_id, rr.reason, rr.proposed_day, rr.proposed_time, rr.proposed_exact_date,
               rr.status, rr.admin_note, rr.created_at,
               c.course_name, s.day, s.time_slot, s.specific_date
        FROM RescheduleRequests rr
        JOIN Schedule s ON rr.session_id = s.session_id
        JOIN Courses c ON s.course_id = c.course_id
        WHERE rr.requested_by = ?
        ORDER BY rr.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows

# ── Catch-up Session Requests ─────────────────────────────────

def submit_catchup_request(course_id, teacher_id, user_id, role, reason, preferred_day=None, preferred_time=None, preferred_exact_date=None):
    conn = get_connection()
    conn.execute("""INSERT INTO CatchupRequests
                    (course_id,teacher_id,requested_by,requested_by_role,reason,preferred_day,preferred_time,preferred_exact_date)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (course_id, teacher_id, user_id, role, reason, preferred_day, preferred_time, preferred_exact_date))
    conn.commit()
    conn.close()

def get_catchup_requests(status=None):
    conn = get_connection()
    query = """
        SELECT cr.catchup_id, cr.reason, cr.preferred_day, cr.preferred_time, cr.preferred_exact_date,
               cr.status, cr.admin_note, cr.created_at, cr.requested_by_role,
               u.name as requester_name,
               c.course_name, g.group_name,
               t.name as teacher_name,
               cr.course_id, cr.teacher_id, cr.session_id
        FROM CatchupRequests cr
        JOIN Users u ON cr.requested_by = u.user_id
        JOIN Courses c ON cr.course_id = c.course_id
        JOIN StudentGroups g ON c.group_id = g.group_id
        JOIN Teachers t ON cr.teacher_id = t.teacher_id
    """
    params = []
    if status:
        query += " WHERE cr.status = ?"
        params.append(status)
    query += " ORDER BY cr.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows

def approve_catchup(catchup_id, day, time_slot, room_id, exact_date=None, admin_note=""):
    conn = get_connection()
    row = conn.execute("SELECT course_id, teacher_id FROM CatchupRequests WHERE catchup_id=?",
                       (catchup_id,)).fetchone()
    if row:
        course_id, teacher_id = row
        cur = conn.execute("""INSERT INTO Schedule (course_id,teacher_id,room_id,day,time_slot,specific_date,status,session_type,notes)
                              VALUES (?,?,?,?,?,?,'scheduled','catchup','Catch-up session')""",
                           (course_id, teacher_id, room_id, day, time_slot, exact_date))
        new_session_id = cur.lastrowid
        conn.execute("""UPDATE CatchupRequests SET status='scheduled', session_id=?, admin_note=?,
                        resolved_at=CURRENT_TIMESTAMP WHERE catchup_id=?""",
                     (new_session_id, admin_note, catchup_id))
        conn.commit()
    conn.close()

def reject_catchup(catchup_id, admin_note=""):
    conn = get_connection()
    conn.execute("""UPDATE CatchupRequests SET status='rejected', admin_note=?,
                    resolved_at=CURRENT_TIMESTAMP WHERE catchup_id=?""",
                 (admin_note, catchup_id))
    conn.commit()
    conn.close()

def get_my_catchup_requests(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT cr.catchup_id, cr.reason, cr.preferred_day, cr.preferred_time, cr.preferred_exact_date,
               cr.status, cr.admin_note, cr.created_at,
               c.course_name,
               s.day, s.time_slot, s.specific_date, r.room_name
        FROM CatchupRequests cr
        JOIN Courses c ON cr.course_id = c.course_id
        LEFT JOIN Schedule s ON cr.session_id = s.session_id
        LEFT JOIN Classrooms r ON s.room_id = r.room_id
        WHERE cr.requested_by = ?
        ORDER BY cr.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows

# ── Seed demo data ────────────────────────────────────────────

def seed_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Teachers")
    if c.fetchone()[0] > 0:
        conn.close()
        print("[DB] Data already seeded.")
        return
    conn.close()

    teachers = [
        ("Dr. Ali Mansour",    "ali@univ.tn",    "Monday,Tuesday,Wednesday,Thursday", "08:00-10:00", "Machine Learning"),
        ("Dr. Sara Chaabane",  "sara@univ.tn",   "Monday,Wednesday,Friday",           "10:00-12:00", "Data Structures"),
        ("Prof. Karim Bouzid", "karim@univ.tn",  "Tuesday,Thursday",                  "14:00-16:00", "Algorithms"),
        ("Dr. Leila Trabelsi", "leila@univ.tn",  "Monday,Tuesday,Wednesday",          "08:00-10:00", "Databases"),
        ("Prof. Nour Ezzine",  "nour@univ.tn",   "Wednesday,Thursday,Friday",         "10:00-12:00", "Networks"),
        ("Dr. Maher Jlassi",   "maher@univ.tn",  "Monday,Tuesday,Friday",             "08:00-10:00", "AI Ethics"),
    ]
    conn = get_connection()
    for t in teachers:
        conn.execute("INSERT INTO Teachers (name,email,available_days,preferred_time,subject) VALUES (?,?,?,?,?)", t)

    groups = [
        ("CS-2A",  "Computer Science", 2, 35),
        ("CS-2B",  "Computer Science", 2, 30),
        ("DS-3A",  "Data Science",     3, 28),
        ("AI-1A",  "AI Engineering",   1, 40),
        ("NET-2A", "Networks",         2, 32),
    ]
    for g in groups:
        conn.execute("INSERT INTO StudentGroups (group_name,program,year,group_size) VALUES (?,?,?,?)", g)

    rooms = [
        ("Room A101", 40, "Projector,Whiteboard"),
        ("Room B202", 35, "Projector,Computers"),
        ("Lab C301",  30, "Computers,Projector"),
        ("Amphi D",   80, "Projector,Microphone"),
        ("Room E105", 32, "Whiteboard"),
    ]
    for r in rooms:
        conn.execute("INSERT INTO Classrooms (room_name,capacity,equipment) VALUES (?,?,?)", r)

    conn.commit()

    courses = [
        ("Machine Learning",  1, "Lab",      [1, 6]),
        ("Machine Learning",  2, "Lab",      [1]),
        ("Data Structures",   1, "Standard", [2]),
        ("Data Structures",   4, "Standard", [2, 3]),
        ("Algorithms",        3, "Standard", [3]),
        ("Algorithms",        5, "Standard", [3]),
        ("Databases",         2, "Lab",      [4]),
        ("Databases",         3, "Lab",      [4]),
        ("Networks",          5, "Standard", [5]),
        ("AI Ethics",         4, "Amphi",    [6, 1]),
        ("AI Ethics",         1, "Amphi",    [6]),
    ]
    for (cname, gid, rtype, tids) in courses:
        cur = conn.execute("INSERT INTO Courses (course_name,group_id,required_room_type) VALUES (?,?,?)",
                           (cname, gid, rtype))
        cid = cur.lastrowid
        for tid in tids:
            conn.execute("INSERT OR IGNORE INTO CourseTeachers (course_id,teacher_id) VALUES (?,?)", (cid, tid))

    conn.commit()
    conn.close()

    register_user("Admin",             "admin@univ.tn",  "password123", "admin",     auto_approve=True)
    register_user("Dr. Ali Mansour",   "ali@univ.tn",    "password123", "professor", teacher_id=1, auto_approve=True)
    register_user("Dr. Sara Chaabane", "sara@univ.tn",   "password123", "professor", teacher_id=2, auto_approve=True)
    register_user("Alice Student",     "alice@univ.tn",  "password123", "student",   group_id=1, auto_approve=True)
    register_user("Bob Student",       "bob@univ.tn",    "password123", "student",   group_id=3, auto_approve=True)

    print("[DB] Demo data seeded.")
    print("  Admin:     admin@univ.tn / password123")
    print("  Professor: ali@univ.tn   / password123")
    print("  Student:   alice@univ.tn / password123")

if __name__ == "__main__":
    create_tables()
    seed_data()
