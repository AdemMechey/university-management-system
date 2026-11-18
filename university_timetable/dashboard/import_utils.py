"""
IMPORT UTILITIES — University Timetabling MAS
Handles CSV / Excel dataset imports for bulk data entry.
Supported: Teachers, Student Groups, Classrooms, Courses
"""
import pandas as pd
import io
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

# ── Expected column schemas ───────────────────────────────────
SCHEMAS = {
    "teachers": {
        "required": ["name", "available_days", "preferred_time", "subject"],
        "optional": ["email"],
        "example": pd.DataFrame([
            {"name": "Dr. Ali Mansour",   "email": "ali@univ.tn",
             "available_days": "Monday,Tuesday,Wednesday",
             "preferred_time": "08:00-10:00", "subject": "Machine Learning"},
            {"name": "Dr. Sara Chaabane", "email": "sara@univ.tn",
             "available_days": "Monday,Wednesday,Friday",
             "preferred_time": "10:00-12:00", "subject": "Data Structures"},
        ])
    },
    "groups": {
        "required": ["group_name", "program", "year", "group_size"],
        "optional": [],
        "example": pd.DataFrame([
            {"group_name": "CS-2A", "program": "Computer Science", "year": 2, "group_size": 35},
            {"group_name": "DS-3A", "program": "Data Science",     "year": 3, "group_size": 28},
        ])
    },
    "classrooms": {
        "required": ["room_name", "capacity"],
        "optional": ["equipment"],
        "example": pd.DataFrame([
            {"room_name": "Room A101", "capacity": 40, "equipment": "Projector,Whiteboard"},
            {"room_name": "Lab C301",  "capacity": 30, "equipment": "Computers,Projector"},
        ])
    },
    "courses": {
        "required": ["course_name", "group_name", "required_room_type", "teacher_names"],
        "optional": [],
        "example": pd.DataFrame([
            {"course_name": "Machine Learning", "group_name": "CS-2A",
             "required_room_type": "Lab", "teacher_names": "Dr. Ali Mansour"},
            {"course_name": "Algorithms",       "group_name": "DS-3A",
             "required_room_type": "Standard", "teacher_names": "Dr. Sara Chaabane / Dr. Ali Mansour"},
        ])
    },
}

VALID_DAYS  = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
VALID_TIMES = {"08:00-10:00","10:00-12:00","12:00-14:00","14:00-16:00","16:00-18:00"}
VALID_ROOM_TYPES = {"Standard", "Lab", "Amphi"}


def get_template_bytes(entity_type):
    """Return a downloadable CSV template for the given entity type."""
    schema = SCHEMAS.get(entity_type)
    if not schema:
        return b""
    return schema["example"].to_csv(index=False).encode("utf-8")


def parse_uploaded_file(file_bytes, filename):
    """Parse uploaded CSV or Excel file into a DataFrame."""
    fname = filename.lower()
    try:
        if fname.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            return None, "Unsupported file type. Please upload CSV or Excel (.xlsx)."
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df, None
    except Exception as e:
        return None, f"Could not parse file: {e}"


def validate_and_import_teachers(df):
    """Validate and import teachers from a DataFrame."""
    errors = []; imported = 0; skipped = 0
    required = ["name", "available_days", "preferred_time", "subject"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return 0, 0, [f"Missing columns: {', '.join(missing)}"]

    conn = get_connection()
    existing = {r[0].lower() for r in conn.execute("SELECT name FROM Teachers").fetchall()}

    for i, row in df.iterrows():
        name = str(row.get("name","")).strip()
        if not name:
            errors.append(f"Row {i+2}: Empty name — skipped.")
            skipped += 1; continue
        if name.lower() in existing:
            errors.append(f"Row {i+2}: '{name}' already exists — skipped.")
            skipped += 1; continue

        # Validate days
        avail = str(row.get("available_days","")).strip()
        days  = [d.strip() for d in avail.split(",")]
        bad_days = [d for d in days if d not in VALID_DAYS]
        if bad_days:
            errors.append(f"Row {i+2}: Invalid days {bad_days} — skipped.")
            skipped += 1; continue

        # Validate time
        pref = str(row.get("preferred_time","08:00-10:00")).strip()
        if pref not in VALID_TIMES:
            errors.append(f"Row {i+2}: Invalid preferred_time '{pref}' — using default.")
            pref = "08:00-10:00"

        email   = str(row.get("email","")).strip()
        subject = str(row.get("subject","")).strip()
        conn.execute("INSERT INTO Teachers (name,email,available_days,preferred_time,subject) VALUES (?,?,?,?,?)",
                     (name, email, ",".join(days), pref, subject))
        existing.add(name.lower())
        imported += 1

    conn.commit(); conn.close()
    return imported, skipped, errors


def validate_and_import_groups(df):
    errors = []; imported = 0; skipped = 0
    required = ["group_name", "program", "year", "group_size"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return 0, 0, [f"Missing columns: {', '.join(missing)}"]

    conn = get_connection()
    existing = {r[0].lower() for r in conn.execute("SELECT group_name FROM StudentGroups").fetchall()}

    for i, row in df.iterrows():
        gname = str(row.get("group_name","")).strip()
        if not gname:
            skipped += 1; continue
        if gname.lower() in existing:
            errors.append(f"Row {i+2}: '{gname}' already exists — skipped.")
            skipped += 1; continue
        try:
            year = int(row.get("year", 1))
            size = int(row.get("group_size", 30))
        except (ValueError, TypeError):
            errors.append(f"Row {i+2}: year and group_size must be numbers — skipped.")
            skipped += 1; continue

        program = str(row.get("program","")).strip()
        conn.execute("INSERT INTO StudentGroups (group_name,program,year,group_size) VALUES (?,?,?,?)",
                     (gname, program, year, size))
        existing.add(gname.lower())
        imported += 1

    conn.commit(); conn.close()
    return imported, skipped, errors


def validate_and_import_classrooms(df):
    errors = []; imported = 0; skipped = 0
    required = ["room_name", "capacity"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return 0, 0, [f"Missing columns: {', '.join(missing)}"]

    conn = get_connection()
    existing = {r[0].lower() for r in conn.execute("SELECT room_name FROM Classrooms").fetchall()}

    for i, row in df.iterrows():
        rname = str(row.get("room_name","")).strip()
        if not rname:
            skipped += 1; continue
        if rname.lower() in existing:
            errors.append(f"Row {i+2}: '{rname}' already exists — skipped.")
            skipped += 1; continue
        try:
            cap = int(row.get("capacity", 30))
        except (ValueError, TypeError):
            errors.append(f"Row {i+2}: capacity must be a number — skipped.")
            skipped += 1; continue

        equip = str(row.get("equipment","")).strip()
        conn.execute("INSERT INTO Classrooms (room_name,capacity,equipment) VALUES (?,?,?)",
                     (rname, cap, equip))
        existing.add(rname.lower())
        imported += 1

    conn.commit(); conn.close()
    return imported, skipped, errors


def validate_and_import_courses(df):
    errors = []; imported = 0; skipped = 0
    required = ["course_name", "group_name", "required_room_type", "teacher_names"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return 0, 0, [f"Missing columns: {', '.join(missing)}"]

    conn = get_connection()
    # Build lookup maps
    groups   = {r[1].lower(): r[0] for r in conn.execute("SELECT group_id,group_name FROM StudentGroups").fetchall()}
    teachers = {r[1].lower(): r[0] for r in conn.execute("SELECT teacher_id,name FROM Teachers").fetchall()}

    for i, row in df.iterrows():
        cname = str(row.get("course_name","")).strip()
        gname = str(row.get("group_name","")).strip().lower()
        rtype = str(row.get("required_room_type","Standard")).strip()
        tnames_raw = str(row.get("teacher_names","")).strip()

        if not cname:
            skipped += 1; continue

        if gname not in groups:
            errors.append(f"Row {i+2}: Group '{gname}' not found — skipped. Import groups first.")
            skipped += 1; continue

        if rtype not in VALID_ROOM_TYPES:
            errors.append(f"Row {i+2}: Invalid room type '{rtype}' — using Standard.")
            rtype = "Standard"

        # Parse teacher names (separated by / or ,)
        tnames = [t.strip().lower() for t in tnames_raw.replace("/",",").split(",") if t.strip()]
        tids   = []
        for tname in tnames:
            if tname in teachers:
                tids.append(teachers[tname])
            else:
                # Try partial match
                match = [tid for tkey, tid in teachers.items() if tname in tkey]
                if match:
                    tids.append(match[0])
                else:
                    errors.append(f"Row {i+2}: Teacher '{tname}' not found — ignored.")

        if not tids:
            errors.append(f"Row {i+2}: No valid teachers for '{cname}' — skipped.")
            skipped += 1; continue

        gid = groups[gname]
        cur = conn.execute("INSERT INTO Courses (course_name,group_id,required_room_type) VALUES (?,?,?)",
                           (cname, gid, rtype))
        cid = cur.lastrowid
        for tid in tids:
            conn.execute("INSERT OR IGNORE INTO CourseTeachers (course_id,teacher_id) VALUES (?,?)", (cid, tid))
        imported += 1

    conn.commit(); conn.close()
    return imported, skipped, errors


# ── Dispatcher ───────────────────────────────────────────────
IMPORTERS = {
    "teachers":   validate_and_import_teachers,
    "groups":     validate_and_import_groups,
    "classrooms": validate_and_import_classrooms,
    "courses":    validate_and_import_courses,
}

def run_import(entity_type, file_bytes, filename):
    """Main entry point called from the dashboard."""
    df, parse_error = parse_uploaded_file(file_bytes, filename)
    if parse_error:
        return 0, 0, [parse_error]
    importer = IMPORTERS.get(entity_type)
    if not importer:
        return 0, 0, [f"Unknown entity type: {entity_type}"]
    return importer(df)
