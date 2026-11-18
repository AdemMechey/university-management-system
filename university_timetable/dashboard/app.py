"""
DASHBOARD v4 — University Timetabling MAS
New features:
  - Admin account approval workflow
  - Session reschedule requests (professors & students)
  - Catch-up session requests
"""
import streamlit as st
import pandas as pd
import sys, os
from datetime import date, datetime
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import (
    get_connection, register_user, login_user,
    add_teacher, update_teacher, delete_teacher,
    add_classroom, update_classroom, delete_classroom,
    add_course, update_course, delete_course,
    get_pending_users, get_all_users, approve_user, reject_user, delete_user,
    submit_reschedule_request, get_reschedule_requests, approve_reschedule, reject_reschedule, get_my_reschedule_requests,
    submit_catchup_request, get_catchup_requests, approve_catchup, reject_catchup, get_my_catchup_requests,
)
from export_utils import export_timetable_excel, export_timetable_pdf, export_timetable_csv
from import_utils import run_import, get_template_bytes, SCHEMAS

st.set_page_config(page_title="University Timetable", page_icon="📅", layout="wide", initial_sidebar_state="expanded")

def _date_input(label, **kwargs):
    """date_input with dd/mm display when Streamlit supports it."""
    try:
        return st.date_input(label, format="DD/MM/YYYY", **kwargs)
    except TypeError:
        return st.date_input(label, **kwargs)

def format_date_ddmmyyyy(val):
    """User-facing calendar date as dd/mm/yyyy (handles ISO strings from DB)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().strftime("%d/%m/%Y")
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()
    if not s or s.lower() == "none":
        return None
    try:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return datetime.strptime(s[:10], "%Y-%m-%d").date().strftime("%d/%m/%Y")
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y").date().strftime("%d/%m/%Y")
    except ValueError:
        return s

def format_date_ddmmyyyy_or_dash(val):
    return format_date_ddmmyyyy(val) or "—"

def parse_to_date(val):
    """Default value for date_input from DB string."""
    if val is None:
        return None
    s = str(val).strip()[:10]
    if not s:
        return None
    try:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        return None

def to_iso_date(d):
    """Store calendar dates in DB as YYYY-MM-DD."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    s = str(d).strip()
    return s or None

def has_partial_slot(day_val, time_val):
    """True when only one of day/time is provided."""
    return bool(day_val) ^ bool(time_val)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Dark background ── */
.stApp { background: #0f1117 !important; }
.main .block-container { background: #0f1117 !important; }

/* ── Global text ── */
html, body, [class*="css"], p, span, div, label { color: #c9cdd8 !important; }
h1,h2,h3,h4,h5,h6 { color: #e8eaf0 !important; }

/* ── Hide chrome ── */
#MainMenu,footer,header{visibility:hidden}
[data-testid="stToolbar"]{display:none}

/* ── Layout ── */
.block-container{max-width:100%!important}
.main .block-container{
  padding: 1.35rem clamp(1rem, 3vw, 2.5rem) 2.5rem !important;
  max-width: 1320px !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

/* ── Streamlit native widgets ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] { background:#1a1d2e !important; border-radius:8px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] button { font-weight:600 !important; font-size:13px !important; color:#8b8fa8 !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] { color:#60a5fa !important; }
[data-testid="stExpander"] details { border:1px solid rgba(255,255,255,0.08) !important; border-radius:12px !important; background:#1a1d2e !important; }
[data-testid="stExpander"] summary { color:#c9cdd8 !important; }
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea { background:#252836 !important; color:#e8eaf0 !important; border-color:rgba(255,255,255,0.1) !important; }
[data-baseweb="select"] > div { background:#252836 !important; color:#e8eaf0 !important; border-color:rgba(255,255,255,0.1) !important; }
[data-baseweb="popover"] li { background:#252836 !important; color:#e8eaf0 !important; }
[data-testid="stNumberInput"] input { background:#252836 !important; color:#e8eaf0 !important; border-color:rgba(255,255,255,0.1) !important; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] { background:#1e3a5f !important; }
.stCheckbox span { color:#c9cdd8 !important; }
[data-testid="stMetricValue"] { color:#60a5fa !important; }
[data-testid="stMetricLabel"] { color:#8b8fa8 !important; }
.stDataFrame { background:#1a1d2e !important; }
[data-testid="stDataFrameContainer"] { background:#1a1d2e !important; }
[data-testid="stRadio"] label { color:#c9cdd8 !important; }
[data-testid="stFormSubmitButton"] button, .stButton button { background:#1e3a5f !important; color:#e8eaf0 !important; border:1px solid rgba(255,255,255,0.12) !important; border-radius:8px !important; }
[data-testid="stFormSubmitButton"] button:hover, .stButton button:hover { background:#185FA5 !important; }
[data-testid="stAlert"] { background:#1a1d2e !important; border-color:rgba(255,255,255,0.1) !important; }
[data-testid="stInfo"] { background:#1e3a5f !important; color:#93c5fd !important; }
[data-testid="stSuccess"] { background:#14301f !important; color:#6ee7b7 !important; }
[data-testid="stWarning"] { background:#2d1f00 !important; color:#fbbf24 !important; }
[data-testid="stError"] { background:#2d0f0f !important; color:#fca5a5 !important; }
hr { border-color: rgba(255,255,255,0.08) !important; }
[data-testid="stCaption"] { color:#6b7280 !important; }
[data-testid="stDivider"] { border-color:rgba(255,255,255,0.08) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"]{background:#042C53!important;border-right:none!important}
[data-testid="stSidebar"] *{color:rgba(255,255,255,0.8)!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#fff!important}
[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,0.12)!important}
[data-testid="stSidebar"] .stButton button{background:rgba(255,255,255,0.07)!important;border:0.5px solid rgba(255,255,255,0.15)!important;color:rgba(255,255,255,0.8)!important;border-radius:8px!important;font-size:13px!important}
[data-testid="stSidebar"] .stButton button:hover{background:rgba(255,255,255,0.14)!important;color:#fff!important}

/* ── Hero ── */
.hero{background:linear-gradient(135deg,#042C53 0%,#185FA5 100%);border-radius:14px;padding:34px 38px;margin-bottom:22px;color:white}
.hero h2{font-size:22px;font-weight:700;margin-bottom:5px;color:#fff!important}
.hero p{font-size:13px;opacity:.7;margin-bottom:20px;color:#fff!important}
.hero-stats{display:flex;gap:32px;flex-wrap:wrap}
.hero-stat .n{font-size:22px;font-weight:700;color:#fff!important}
.hero-stat .l{font-size:11px;opacity:.55;margin-top:1px;color:#fff!important}

/* ── KPI cards ── */
.kpi{background:#1a1d2e;border:0.5px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 18px;text-align:center}
.kpi .n{font-size:26px;font-weight:700;color:#60a5fa!important}
.kpi .l{font-size:12px;color:#6b7280!important;margin-top:1px}
.kpi .b{display:inline-block;margin-top:7px;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:600}

/* ── Badges ── */
.bg{background:#1e3a5f;color:#93c5fd}.gg{background:#14301f;color:#6ee7b7}
.ag{background:#2d1f00;color:#fbbf24}.rg{background:#2d0f0f;color:#fca5a5}.tg{background:#0f2d1f;color:#34d399}
.pg{background:#2d0f2d;color:#f0abfc}.og{background:#2d1500;color:#fb923c}

/* ── Cards ── */
.card{background:#1a1d2e;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 4px 24px rgba(0,0,0,0.3)}
.card h4{font-size:14px;font-weight:700;color:#e8eaf0!important;margin-bottom:3px}
.card p{font-size:12px;color:#8b8fa8!important}

/* ── Pills ── */
.pill{display:inline-block;padding:3px 9px;border-radius:99px;font-size:11px;font-weight:600;margin:2px}
.pd{background:#2d1a5e;color:#c4b5fd}.pt{background:#1e3a5f;color:#93c5fd}
.pr{background:#0f2d1f;color:#6ee7b7}.pte{background:#2d1f00;color:#fbbf24}
.pgr{background:#2d0f2d;color:#f0abfc}.po{background:#2d1500;color:#fb923c}

/* ── Section headers ── */
.sec{font-size:17px;font-weight:700;color:#e8eaf0!important;margin-bottom:3px}
.sub{font-size:13px;color:#6b7280!important;margin-bottom:16px}

/* ── Timetable ── */
.tt-table{width:100%;border-collapse:collapse;font-size:12px}
.tt-table th{background:#042C53;color:white;padding:9px 12px;text-align:center;font-weight:600}
.tt-table td{border:0.5px solid rgba(255,255,255,0.07);padding:7px 9px;vertical-align:top;background:#1a1d2e;min-width:100px}
.tt-cell{background:#1e3a5f;color:#93c5fd;border-radius:6px;padding:4px 7px;margin-bottom:3px;font-size:11px;font-weight:600;line-height:1.4}
.tt-cell-prof{background:#0f2d1f;color:#6ee7b7;border-radius:6px;padding:4px 7px;margin-bottom:3px;font-size:11px;font-weight:600}
.tt-cell-catchup{background:#2d1500;color:#fb923c;border-radius:6px;padding:4px 7px;margin-bottom:3px;font-size:11px;font-weight:600;border-left:3px solid #f97316}

/* ── Request cards ── */
.req-card{background:#1a1d2e;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 4px 24px rgba(0,0,0,0.3)}
.req-card-pending{border-left:4px solid #f59e0b}
.req-card-approved{border-left:4px solid #10b981;background:#0d1f15}
.req-card-rejected{border-left:4px solid #ef4444;background:#1f0d0d}
.req-card-scheduled{border-left:4px solid #6366f1;background:#13143a}

/* ── Status badges ── */
.badge-pending{background:#2d1f00;color:#fbbf24;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.badge-approved{background:#14301f;color:#6ee7b7;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.badge-rejected{background:#2d0f0f;color:#fca5a5;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.badge-scheduled{background:#13143a;color:#a5b4fc;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}

/* ── Misc ── */
.pending-user{background:#1e2a1a;border:0.5px solid rgba(251,191,36,0.3);border-radius:12px;padding:16px 20px;margin-bottom:10px}
.agent-card{background:#1a1d2e;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 4px 24px rgba(0,0,0,0.3)}
.aname{font-size:14px;font-weight:700;color:#60a5fa!important;margin-bottom:2px}
.arole{font-size:12px;color:#1D9E75!important;font-weight:600;margin-bottom:7px}
.adesc{font-size:13px;color:#8b8fa8!important;line-height:1.6}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#1D9E75;margin-right:6px}
.log{background:#060b14;border-radius:10px;padding:15px 17px;font-family:monospace;font-size:12px;color:#9FE1CB;line-height:1.9;max-height:300px;overflow-y:auto;border:1px solid rgba(255,255,255,0.06)}
.conflict{background:#1f0d0d;border:0.5px solid rgba(239,68,68,0.3);border-radius:10px;padding:13px 16px;margin-bottom:9px}
.conflict p{font-size:13px;color:#fca5a5!important}
.role-badge-admin{background:#2d0f0f;color:#fca5a5;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.role-badge-professor{background:#1e3a5f;color:#93c5fd;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.role-badge-student{background:#14301f;color:#6ee7b7;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}
.notif-banner{background:#2d1f00;border:1px solid rgba(251,191,36,0.3);border-radius:10px;padding:12px 18px;margin-bottom:14px;font-size:13px;color:#fbbf24!important;font-weight:600}
</style>
""", unsafe_allow_html=True)

for k,v in [("logged_in",False),("user",None),("auth_page","login"),("sim_ran",False),("sim_result",None)]:
    if k not in st.session_state: st.session_state[k]=v

DAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
TIMES = ["08:00-10:00","10:00-12:00","12:00-14:00","14:00-16:00","16:00-18:00"]

_GROUP_PALETTE = [
    ("#dbeafe", "#1e40af"),
    ("#dcfce7", "#166534"),
    ("#fce7f3", "#9d174d"),
    ("#ede9fe", "#5b21b6"),
    ("#d1fae5", "#065f46"),
    ("#fef3c7", "#92400e"),
    ("#fee2e2", "#991b1b"),
    ("#ffedd5", "#c2410c"),
]

def _group_color(group_id):
    bg, fg = _GROUP_PALETTE[int(group_id) % len(_GROUP_PALETTE)]
    return bg, fg

# ── Data loaders ──────────────────────────────────────────────
@st.cache_data(ttl=8)
def load_schedule():
    conn = get_connection()
    try:
        df = pd.read_sql_query("""
            SELECT s.session_id, s.day, s.time_slot, s.session_type, s.notes, s.specific_date,
                   c.course_name, c.required_room_type, c.course_id,
                   t.name as teacher, t.teacher_id,
                   g.group_name, g.group_id, g.program, g.year, g.group_size,
                   r.room_name, r.room_id, r.capacity
            FROM Schedule s
            JOIN Courses c ON s.course_id=c.course_id
            JOIN Teachers t ON s.teacher_id=t.teacher_id
            JOIN StudentGroups g ON c.group_id=g.group_id
            JOIN Classrooms r ON s.room_id=r.room_id
            ORDER BY s.day, s.time_slot
        """, conn)
    except: df = pd.DataFrame()
    conn.close(); return df

@st.cache_data(ttl=8)
def load_teachers():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Teachers ORDER BY name", conn)
    conn.close(); return df

@st.cache_data(ttl=8)
def load_groups():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM StudentGroups ORDER BY group_name", conn)
    conn.close(); return df

@st.cache_data(ttl=8)
def load_rooms():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Classrooms ORDER BY room_name", conn)
    conn.close(); return df

@st.cache_data(ttl=8)
def load_courses():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT co.course_id, co.course_name, co.required_room_type,
               g.group_name, g.group_id,
               GROUP_CONCAT(t.name, ' / ') as teachers,
               GROUP_CONCAT(ct.teacher_id) as teacher_ids
        FROM Courses co
        JOIN StudentGroups g ON co.group_id=g.group_id
        LEFT JOIN CourseTeachers ct ON co.course_id=ct.course_id
        LEFT JOIN Teachers t ON ct.teacher_id=t.teacher_id
        GROUP BY co.course_id
    """, conn)
    conn.close(); return df

@st.cache_data(ttl=8)
def load_conflicts():
    conn = get_connection()
    try: df = pd.read_sql_query("SELECT * FROM ConflictLog ORDER BY timestamp DESC", conn)
    except: df = pd.DataFrame()
    conn.close(); return df

def clear_cache(): st.cache_data.clear()

def _room_utilization(sched_df, rooms_df):
    if sched_df.empty or rooms_df.empty:
        return 0.0
    total_slots = len(rooms_df) * len(DAYS) * len(TIMES)
    used = len(sched_df[sched_df["session_type"] == "regular"]) if "session_type" in sched_df.columns else len(sched_df)
    return round(min(used / total_slots * 100, 100), 1)

def _avg_teacher_load(sched_df, teachers_df):
    if sched_df.empty or teachers_df.empty:
        return 0.0
    return round(len(sched_df) / len(teachers_df), 1)

# ── Timetable grid ────────────────────────────────────────────
def render_timetable(df, cell_class="tt-cell"):
    if df.empty:
        st.info("No schedule yet. Go to **Run Simulation**.")
        return
    header = "<tr><th style='background:#042C53;color:white;padding:9px 12px'>Time</th>" + \
             "".join(f"<th style='background:#042C53;color:white;padding:9px 12px'>{d}</th>" for d in DAYS) + "</tr>"
    rows = ""
    for ts in TIMES:
        row = f"<tr><td style='font-weight:600;color:#042C53;font-size:12px;white-space:nowrap;background:#f8fafc;padding:9px 12px'>{ts}</td>"
        for day in DAYS:
            sessions = df[(df["day"]==day)&(df["time_slot"]==ts)]
            if sessions.empty:
                row += "<td style='border:0.5px solid #e5e7eb;min-width:110px;text-align:center;color:#ccc;font-size:12px'>—</td>"
            else:
                cells = ""
                for _, s in sessions.iterrows():
                    stype = s.get("session_type", "regular") if "session_type" in s else "regular"
                    sd = s["specific_date"] if "specific_date" in s and pd.notna(s.get("specific_date")) else None
                    date_line = (
                        f'<br><span style="font-size:10px;font-weight:600;opacity:.8">'
                        f'📆 {format_date_ddmmyyyy_or_dash(sd)}</span>'
                        if sd else ""
                    )
                    teacher_line = f'<br><span style="font-size:10px;opacity:.7">👨‍🏫 {s["teacher"]}</span>'
                    if stype == "catchup":
                        cells += (
                            f'<div class="tt-cell-catchup">{s["course_name"]} 🔄'
                            f'<br><span style="font-weight:400;opacity:.8">{s["group_name"]} · {s["room_name"]}</span>'
                            f'{teacher_line}{date_line}</div>'
                        )
                    else:
                        bg, fg = _group_color(s["group_id"])
                        cells += (
                            f'<div style="background:{bg};color:{fg};border-radius:6px;padding:4px 7px;'
                            f'margin-bottom:3px;font-size:11px;font-weight:600;line-height:1.5">'
                            f'{s["course_name"]}'
                            f'<br><span style="font-weight:400;opacity:.8">{s["group_name"]} · {s["room_name"]}</span>'
                            f'{teacher_line}{date_line}</div>'
                        )
                row += f"<td style='border:0.5px solid #e5e7eb;min-width:110px;padding:7px'>{cells}</td>"
        rows += row + "</tr>"
    st.markdown(f'<div style="overflow-x:auto"><table class="tt-table"><thead>{header}</thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

def status_badge(status):
    cls = {"pending":"badge-pending","approved":"badge-approved","rejected":"badge-rejected","scheduled":"badge-scheduled"}.get(status,"badge-pending")
    return f'<span class="{cls}">{status.upper()}</span>'

# ────────────────────────────────────────────────────────────
# AUTH
# ────────────────────────────────────────────────────────────
def show_login():
    col1,col2,col3 = st.columns([1,1.4,1])
    with col2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:28px">
          <div style="font-size:48px;margin-bottom:8px">📅</div>
          <h1 style="font-size:20px;font-weight:700;color:#1a1a2e">University Timetabling MAS</h1>
          <p style="font-size:13px;color:#888;margin-top:4px">Multi-Agent Scheduling · Mesa Framework</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Sign in")
        email    = st.text_input("Email", placeholder="admin@univ.tn")
        password = st.text_input("Password", type="password")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign In →", use_container_width=True, type="primary"):
            user = login_user(email, password)
            if user:
                if user["status"] == "pending":
                    st.warning("⏳ Your account is pending admin approval. Please check back later.")
                elif user["status"] == "rejected":
                    st.error("❌ Your account request was rejected. Please contact administration.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
            else:
                st.error("Invalid credentials.")
        st.divider()
        st.markdown("<p style='text-align:center;font-size:13px;color:#888'>Don't have an account?</p>", unsafe_allow_html=True)
        if st.button("Create Account", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()
        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:12px;color:#aaa">
          <b>Admin:</b> admin@univ.tn &nbsp;|&nbsp;
          <b>Prof:</b> ali@univ.tn &nbsp;|&nbsp;
          <b>Student:</b> alice@univ.tn<br>
          <span style="opacity:.7">All passwords: password123</span>
        </div>
        """, unsafe_allow_html=True)

def show_register():
    groups_df = load_groups()
    teachers_df = load_teachers()
    col1,col2,col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:24px">
          <div style="font-size:40px;margin-bottom:6px">📋</div>
          <h2 style="font-size:18px;font-weight:700;color:#1a1a2e">Create Account</h2>
          <p style="font-size:12px;color:#888">Your account will be reviewed by an admin before activation.</p>
        </div>
        """, unsafe_allow_html=True)
        name  = st.text_input("Full Name *")
        email = st.text_input("Email *")
        role  = st.selectbox("Role *", ["student","professor"])
        teacher_id, group_id = None, None
        if role == "professor":
            opts = {row["name"]: row["teacher_id"] for _, row in teachers_df.iterrows()}
            sel = st.selectbox("Link to Teacher Profile", list(opts.keys()))
            teacher_id = opts.get(sel)
        elif role == "student":
            opts = {row["group_name"]: row["group_id"] for _, row in groups_df.iterrows()}
            sel = st.selectbox("Your Student Group", list(opts.keys()))
            group_id = opts.get(sel)
        col_a,col_b = st.columns(2)
        with col_a: pwd  = st.text_input("Password *", type="password")
        with col_b: pwd2 = st.text_input("Confirm *",  type="password")
        if st.button("Submit Registration →", use_container_width=True, type="primary"):
            if not all([name,email,pwd,pwd2]):
                st.error("Fill all required fields.")
            elif pwd != pwd2:
                st.error("Passwords don't match.")
            else:
                ok, result = register_user(name, email, pwd, role, teacher_id, group_id)
                if ok:
                    st.success("✅ Registration submitted! An admin will review your account shortly.")
                    st.info("You will be able to sign in once your account is approved.")
                    st.session_state.auth_page = "login"
                    st.rerun()
                else:
                    st.error(result)
        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state.auth_page = "login"; st.rerun()

# ────────────────────────────────────────────────────────────
# SHARED SIDEBAR
# ────────────────────────────────────────────────────────────
def build_sidebar(user, nav_items):
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:6px 0 14px">
          <div style="font-size:26px;margin-bottom:7px">📅</div>
          <div style="font-size:13px;font-weight:700;color:white">Timetabling MAS</div>
          <div style="font-size:11px;color:rgba(255,255,255,.4)">Mesa · Multi-Agent</div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:rgba(255,255,255,.07);border-radius:10px;padding:11px 13px;margin-bottom:12px">
          <div style="font-size:13px;font-weight:600;color:white">{user['name']}</div>
          <div style="margin-top:3px"><span class="role-badge-{user['role']}">{user['role'].capitalize()}</span></div>
          <div style="font-size:11px;color:rgba(255,255,255,.4);margin-top:4px">{user['email']}</div>
        </div>""", unsafe_allow_html=True)
        page = st.radio("", nav_items, label_visibility="collapsed")
        st.divider()
        if st.button("Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    return page

# ────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ────────────────────────────────────────────────────────────
def show_admin():
    user = st.session_state.user
    pending_users = get_pending_users()
    pending_reschedules = get_reschedule_requests("pending")
    pending_catchups = get_catchup_requests("pending")
    total_pending = len(pending_users) + len(pending_reschedules) + len(pending_catchups)

    page = build_sidebar(user, [
        "🏠  Dashboard", "📅  Timetable", "▶️  Run Simulation",
        "👨‍🏫  Manage Professors", "🏛️  Manage Classrooms",
        "📋  Manage Courses", "🔔  Approvals",
        "🔄  Reschedule Requests", "📚  Catch-up Requests",
        "👥  User Management", "🤖  Agents", "⚠️  Conflicts",
        "📤  Export Timetable", "📥  Import Dataset",
    ])

    sched = load_schedule()
    conflicts = load_conflicts()
    teachers = load_teachers()
    rooms = load_rooms()
    groups = load_groups()
    courses = load_courses()

    with st.container():

        # ── DASHBOARD ──
        if page == "🏠  Dashboard":
            st.markdown(f"""
            <div class="hero">
              <h2>Admin Dashboard 🎓</h2>
              <p>University Timetabling · Multi-Agent System · Full control</p>
              <div class="hero-stats">
                <div class="hero-stat"><div class="n">{len(sched)}</div><div class="l">Sessions</div></div>
                <div class="hero-stat"><div class="n">{len(teachers)}</div><div class="l">Professors</div></div>
                <div class="hero-stat"><div class="n">{len(groups)}</div><div class="l">Groups</div></div>
                <div class="hero-stat"><div class="n">{len(pending_users)}</div><div class="l">Pending Accounts</div></div>
                <div class="hero-stat"><div class="n">{len(pending_reschedules)}</div><div class="l">Reschedule Requests</div></div>
                <div class="hero-stat"><div class="n">{len(pending_catchups)}</div><div class="l">Catch-up Requests</div></div>
              </div>
            </div>""", unsafe_allow_html=True)
            if total_pending > 0:
                st.markdown(f'<div class="notif-banner">🔔 You have {total_pending} pending item(s) requiring your attention.</div>', unsafe_allow_html=True)
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            util = _room_utilization(sched, rooms)
            load = _avg_teacher_load(sched, teachers)
            c1.markdown(f'<div class="kpi"><div class="n">{len(sched)}</div><div class="l">Sessions</div><span class="b gg">Scheduled</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="kpi"><div class="n">{len(teachers)}</div><div class="l">Professors</div><span class="b bg">Agents</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="kpi"><div class="n">{len(groups)}</div><div class="l">Groups</div><span class="b tg">Active</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="kpi"><div class="n">{util}%</div><div class="l">Room Utilization</div><span class="b {"gg" if util >= 50 else "ag"}">{"Good" if util >= 50 else "Low"}</span></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="kpi"><div class="n">{load}</div><div class="l">Avg Load/Prof</div><span class="b bg">Sessions</span></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="kpi"><div class="n">{len(conflicts)}</div><div class="l">Conflicts</div><span class="b {"rg" if len(conflicts)>0 else "gg"}">{"Found" if len(conflicts)>0 else "None"}</span></div>', unsafe_allow_html=True)
            if not sched.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:10px">Sessions by Day</p>', unsafe_allow_html=True)
                day_counts = sched["day"].value_counts().reindex(DAYS).fillna(0)
                max_count  = max(day_counts.max(), 1)
                bars_html  = ""
                for d, cnt in day_counts.items():
                    pct = int(cnt / max_count * 100)
                    bars_html += (
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
                        f'<div style="width:80px;font-size:12px;color:#555">{d}</div>'
                        f'<div style="flex:1;background:#f0f4f8;border-radius:4px;height:18px">'
                        f'<div style="width:{pct}%;background:#185FA5;border-radius:4px;height:18px"></div></div>'
                        f'<div style="width:24px;font-size:12px;font-weight:700;color:#042C53">{int(cnt)}</div>'
                        f'</div>'
                    )
                st.markdown(f'<div style="margin-top:8px">{bars_html}</div>', unsafe_allow_html=True)

        # ── TIMETABLE ──
        elif page == "📅  Timetable":
            st.markdown('<div class="sec">Full Timetable</div><div class="sub">All scheduled sessions · 🔄 = catch-up session</div>', unsafe_allow_html=True)
            filter_group = st.selectbox("Filter by group", ["All Groups"] + sorted(sched["group_name"].unique().tolist()) if not sched.empty else ["All Groups"])
            df = sched if filter_group == "All Groups" else sched[sched["group_name"]==filter_group]
            render_timetable(df)

        # ── RUN SIMULATION ──
        elif page == "▶️  Run Simulation":
            st.markdown('<div class="sec">Run Scheduling Simulation</div><div class="sub">Executes the Mesa MAS — agents negotiate to build the timetable</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="card">
              <h4>Negotiation Protocol</h4>
              <p style="line-height:1.9;margin-top:6px">
                1. <b>SchedulerAgent</b> iterates over all courses<br>
                2. For each course, tries its assigned teachers (multi-teacher support)<br>
                3. <b>TeacherAgent</b> proposes a slot (preferred time first)<br>
                4. <b>GroupAgent</b> validates — rejects if group is already busy<br>
                5. <b>RoomAgent</b> checks capacity + equipment requirements<br>
                6. On conflict → negotiation retries up to 5× with excluded slots<br>
                7. Results saved to DB · conflicts logged
              </p>
            </div>""", unsafe_allow_html=True)
            if st.button("▶️  Run Now", type="primary", use_container_width=True):
                with st.spinner("Running Mesa simulation..."):
                    try:
                        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
                        from timetable_model import TimetableModel
                        model = TimetableModel()
                        model.step()
                        sc = model.scheduler
                        st.session_state.sim_ran = True
                        st.session_state.sim_result = {
                            "scheduled": sc.resolved_count, "total": sc.total_courses,
                            "conflicts": len(sc.conflicts), "negotiations": sc.negotiation_count,
                            "logs": model.get_all_logs()[-40:]
                        }
                        clear_cache()
                        st.success(f"✅ Done! {sc.resolved_count}/{sc.total_courses} sessions scheduled.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        import traceback; st.code(traceback.format_exc())
            if st.session_state.sim_ran and st.session_state.sim_result:
                r = st.session_state.sim_result
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Scheduled", r["scheduled"])
                c2.metric("Total", r["total"])
                c3.metric("Conflicts", r["conflicts"])
                c4.metric("Negotiations", r["negotiations"])
                log_html = "<br>".join(
                    f'<span style="color:{"#5DCAA5" if "✓" in l else "#F09595" if "✗" in l or "CONFLICT" in l else "#9FE1CB"}">{l}</span>'
                    for l in r["logs"])
                st.markdown(f'<div class="log">{log_html}</div>', unsafe_allow_html=True)

        # ── APPROVALS ──
        elif "Approvals" in page:
            st.markdown(f'<div class="sec">Pending Approvals ({total_pending})</div><div class="sub">Review and action all pending items</div>', unsafe_allow_html=True)

            tab1, tab2, tab3 = st.tabs([f"👤 Account Requests ({len(pending_users)})",
                                         f"🔄 Reschedule ({len(pending_reschedules)})",
                                         f"📚 Catch-up ({len(pending_catchups)})"])
            with tab1:
                if not pending_users:
                    st.success("✅ No pending account requests.")
                for u in pending_users:
                    uid, uname, uemail, urole, ucreated = u
                    with st.container():
                        st.markdown(f"""
                        <div class="pending-user">
                          <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                              <div style="font-weight:700;font-size:14px;color:#1a1a2e">{uname}</div>
                              <div style="font-size:12px;color:#666">{uemail} · <span class="role-badge-{urole}">{urole.capitalize()}</span></div>
                              <div style="font-size:11px;color:#aaa;margin-top:4px">Requested: {ucreated}</div>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)
                        col_a, col_b, col_c = st.columns([2,1,1])
                        with col_b:
                            if st.button("✅ Approve", key=f"ap_{uid}", use_container_width=True, type="primary"):
                                approve_user(uid); clear_cache(); st.rerun()
                        with col_c:
                            if st.button("❌ Reject", key=f"rj_{uid}", use_container_width=True):
                                reject_user(uid); clear_cache(); st.rerun()

            with tab2:
                if not pending_reschedules:
                    st.success("✅ No pending reschedule requests.")
                for req in pending_reschedules:
                    (req_id, sess_id, reason, prop_day, prop_time, prop_exact, status, admin_note,
                     created_at, by_role, requester, course, group, teacher, curr_day, curr_time, curr_exact, room) = req
                    with st.expander(f"🔄 {course} — {group} | Requested by {requester} ({by_role})"):
                        c1, c2 = st.columns(2)
                        with c1:
                            ce = f" · 📆 **{format_date_ddmmyyyy_or_dash(curr_exact)}**" if curr_exact else ""
                            pe = f" · 📆 **{format_date_ddmmyyyy_or_dash(prop_exact)}**" if prop_exact else ""
                            st.markdown(f"**Current:** {curr_day}, {curr_time}{ce}")
                            st.markdown(f"**Proposed:** {prop_day or 'Not specified'}, {prop_time or 'Not specified'}{pe}")
                            st.markdown(f"**Reason:** {reason}")
                        with c2:
                            new_day = st.selectbox("Approved Day", DAYS, key=f"rday_{req_id}",
                                                   index=DAYS.index(prop_day) if prop_day in DAYS else 0)
                            new_time = st.selectbox("Approved Time", TIMES, key=f"rtime_{req_id}",
                                                    index=TIMES.index(prop_time) if prop_time in TIMES else 0)
                            new_exact = _date_input(
                                "Exact date (dd/mm/yyyy, optional)",
                                key=f"rexact_{req_id}",
                                value=parse_to_date(prop_exact),
                            )
                        note = st.text_input("Admin Note (optional)", key=f"rnote_{req_id}")
                        confirm_reschedule = st.checkbox("I confirm applying this reschedule", key=f"rconfirm_{req_id}")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Approve & Reschedule", key=f"rap_{req_id}", type="primary", use_container_width=True):
                                if not confirm_reschedule:
                                    st.error("Please confirm before approving this reschedule.")
                                else:
                                    approve_reschedule(req_id, new_day, new_time, to_iso_date(new_exact), note)
                                    clear_cache(); st.success("Rescheduled!"); st.rerun()
                        with col_b:
                            if st.button("❌ Reject", key=f"rrj_{req_id}", use_container_width=True):
                                reject_reschedule(req_id, note)
                                clear_cache(); st.warning("Rejected."); st.rerun()

            with tab3:
                if not pending_catchups:
                    st.success("✅ No pending catch-up requests.")
                for cu in pending_catchups:
                    (cu_id, reason, pref_day, pref_time, pref_exact, status, admin_note, created_at,
                     by_role, requester, course, group, teacher, course_id, teacher_id, session_id) = cu
                    with st.expander(f"📚 Catch-up: {course} — {group} | by {requester} ({by_role})"):
                        st.markdown(f"**Reason:** {reason}")
                        pref_date_txt = format_date_ddmmyyyy_or_dash(pref_exact) if pref_exact else "Not specified"
                        st.markdown(f"**Preferred slot:** {pref_day or 'Any day'}, {pref_time or 'Any time'}  \n**Preferred calendar date (dd/mm/yyyy):** {pref_date_txt}")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            cu_day = st.selectbox("Day *", DAYS, key=f"cday_{cu_id}",
                                                  index=DAYS.index(pref_day) if pref_day in DAYS else 0)
                        with c2:
                            cu_time = st.selectbox("Time *", TIMES, key=f"ctime_{cu_id}",
                                                   index=TIMES.index(pref_time) if pref_time in TIMES else 0)
                        with c3:
                            room_opts = {r["room_name"]: r["room_id"] for _, r in rooms.iterrows()}
                            cu_room = st.selectbox("Room *", list(room_opts.keys()), key=f"croom_{cu_id}")
                        with c4:
                            cu_exact = _date_input(
                                "Session calendar date (dd/mm/yyyy) *",
                                key=f"cexact_{cu_id}",
                                value=parse_to_date(pref_exact) or date.today(),
                            )
                        cu_note = st.text_input("Admin Note (optional)", key=f"cnote_{cu_id}")
                        confirm_catchup = st.checkbox("I confirm scheduling this catch-up session", key=f"cconfirm_{cu_id}")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Schedule Catch-up", key=f"cap_{cu_id}", type="primary", use_container_width=True):
                                if cu_exact is None:
                                    st.error("Choose the session calendar date (dd/mm/yyyy).")
                                elif not confirm_catchup:
                                    st.error("Please confirm before scheduling this catch-up session.")
                                else:
                                    approve_catchup(cu_id, cu_day, cu_time, room_opts[cu_room], to_iso_date(cu_exact), cu_note)
                                    clear_cache(); st.success("Catch-up session scheduled!"); st.rerun()
                        with col_b:
                            if st.button("❌ Reject", key=f"crj_{cu_id}", use_container_width=True):
                                reject_catchup(cu_id, cu_note)
                                clear_cache(); st.warning("Rejected."); st.rerun()

        # ── RESCHEDULE HISTORY ──
        elif page == "🔄  Reschedule Requests":
            st.markdown('<div class="sec">Reschedule Requests</div><div class="sub">All session reschedule requests</div>', unsafe_allow_html=True)
            filter_status = st.selectbox("Filter by status", ["All", "pending", "approved", "rejected"])
            reqs = get_reschedule_requests(None if filter_status == "All" else filter_status)
            if not reqs:
                st.info("No requests found.")
            for req in reqs:
                (req_id, sess_id, reason, prop_day, prop_time, prop_exact, status, admin_note,
                 created_at, by_role, requester, course, group, teacher, curr_day, curr_time, curr_exact, room) = req
                card_class = f"req-card req-card-{status}"
                st.markdown(f"""
                <div class="{card_class}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:14px;font-weight:700;color:#1a1a2e">{course} — {group}</div>
                      <div style="font-size:12px;color:#666;margin-top:2px">👨‍🏫 {teacher} · 🏛️ {room}</div>
                      <div style="font-size:12px;color:#888;margin-top:4px">
                        <b>Current:</b> {curr_day}, {curr_time}{f" · 📆 {format_date_ddmmyyyy_or_dash(curr_exact)}" if curr_exact else ""} &nbsp;→&nbsp;
                        <b>Proposed:</b> {prop_day or '—'}, {prop_time or '—'}{f" · 📆 {format_date_ddmmyyyy_or_dash(prop_exact)}" if prop_exact else ""}
                      </div>
                      <div style="font-size:12px;color:#555;margin-top:4px"><b>Reason:</b> {reason}</div>
                      <div style="font-size:11px;color:#aaa;margin-top:4px">By {requester} ({by_role}) · {created_at}</div>
                      {f'<div style="font-size:12px;color:#555;margin-top:3px"><b>Admin note:</b> {admin_note}</div>' if admin_note else ''}
                    </div>
                    <div>{status_badge(status)}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # ── CATCH-UP HISTORY ──
        elif page == "📚  Catch-up Requests":
            st.markdown('<div class="sec">Catch-up Session Requests</div><div class="sub">All makeup session requests</div>', unsafe_allow_html=True)
            filter_status = st.selectbox("Filter by status", ["All", "pending", "scheduled", "rejected"])
            catchups = get_catchup_requests(None if filter_status == "All" else filter_status)
            if not catchups:
                st.info("No catch-up requests found.")
            for cu in catchups:
                (cu_id, reason, pref_day, pref_time, pref_exact, status, admin_note, created_at,
                 by_role, requester, course, group, teacher, course_id, teacher_id, session_id) = cu
                card_class = f"req-card req-card-{status if status!='scheduled' else 'scheduled'}"
                st.markdown(f"""
                <div class="{card_class}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:14px;font-weight:700;color:#1a1a2e">📚 {course} — {group}</div>
                      <div style="font-size:12px;color:#666;margin-top:2px">👨‍🏫 {teacher}</div>
                      <div style="font-size:12px;color:#888;margin-top:4px"><b>Preferred:</b> {pref_day or 'Any'}, {pref_time or 'Any'} · <b>Date:</b> {format_date_ddmmyyyy_or_dash(pref_exact) if pref_exact else 'Not specified'}</div>
                      <div style="font-size:12px;color:#555;margin-top:4px"><b>Reason:</b> {reason}</div>
                      <div style="font-size:11px;color:#aaa;margin-top:4px">By {requester} ({by_role}) · {created_at}</div>
                      {f'<div style="font-size:12px;color:#555;margin-top:3px"><b>Admin note:</b> {admin_note}</div>' if admin_note else ''}
                    </div>
                    <div>{status_badge(status)}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # ── USER MANAGEMENT ──
        elif page == "👥  User Management":
            st.markdown('<div class="sec">User Management</div><div class="sub">All accounts and their approval status</div>', unsafe_allow_html=True)
            all_users = get_all_users()
            status_filter = st.selectbox("Filter by status", ["All", "approved", "pending", "rejected"])
            for u in all_users:
                uid, uname, uemail, urole, ustatus, ucreated = u
                if status_filter != "All" and ustatus != status_filter:
                    continue
                badge_cls = {"approved": "gg", "pending": "ag", "rejected": "rg"}.get(ustatus, "ag")
                with st.expander(f"{uname} — {uemail} [{ustatus.upper()}]"):
                    c1, c2, c3 = st.columns([3,1,1])
                    with c1:
                        st.markdown(f'<span class="role-badge-{urole}">{urole.capitalize()}</span> &nbsp; <span class="b {badge_cls}">{ustatus.upper()}</span>', unsafe_allow_html=True)
                        st.caption(f"Registered: {ucreated}")
                    with c2:
                        if ustatus != "approved":
                            if st.button("✅ Approve", key=f"uap_{uid}", use_container_width=True, type="primary"):
                                approve_user(uid); clear_cache(); st.rerun()
                    with c3:
                        confirm_delete_user = st.checkbox("Confirm", key=f"udel_confirm_{uid}")
                        if st.button("🗑️ Delete", key=f"udel_{uid}", use_container_width=True):
                            if not confirm_delete_user:
                                st.error("Tick confirm to delete this user.")
                            else:
                                delete_user(uid); clear_cache(); st.rerun()

        # ── MANAGE PROFESSORS ──
        elif page == "👨‍🏫  Manage Professors":
            st.markdown('<div class="sec">Manage Professors</div><div class="sub">Add, edit or delete teacher profiles</div>', unsafe_allow_html=True)
            with st.expander("➕ Add New Professor", expanded=False):
                with st.form("add_teacher"):
                    c1,c2 = st.columns(2)
                    with c1:
                        n_name = st.text_input("Full Name *")
                        n_email = st.text_input("Email")
                        n_subject = st.text_input("Subject / Specialty")
                    with c2:
                        day_opts = st.multiselect("Available Days *", DAYS, default=DAYS[:4])
                        n_pref = st.selectbox("Preferred Time Slot", TIMES)
                    if st.form_submit_button("Add Professor", type="primary"):
                        if n_name and day_opts:
                            add_teacher(n_name, n_email, ",".join(day_opts), n_pref, n_subject)
                            clear_cache(); st.success(f"Professor '{n_name}' added!"); st.rerun()
                        else: st.error("Name and available days are required.")
            st.divider()
            for _, t in teachers.iterrows():
                with st.expander(f"👨‍🏫 {t['name']} — {t['subject'] or 'N/A'}"):
                    with st.form(f"edit_t_{t['teacher_id']}"):
                        c1,c2 = st.columns(2)
                        with c1:
                            e_name    = st.text_input("Name", value=t["name"])
                            e_email   = st.text_input("Email", value=t["email"] or "")
                            e_subject = st.text_input("Subject", value=t["subject"] or "")
                        with c2:
                            current_days = [d.strip() for d in (t["available_days"] or "").split(",")]
                            e_days = st.multiselect("Available Days", DAYS, default=[d for d in current_days if d in DAYS])
                            e_pref = st.selectbox("Preferred Time", TIMES, index=TIMES.index(t["preferred_time"]) if t["preferred_time"] in TIMES else 0)
                        col_s, col_d = st.columns([3,1])
                        with col_s:
                            if st.form_submit_button("💾 Save Changes", type="primary"):
                                update_teacher(t["teacher_id"], e_name, e_email, ",".join(e_days), e_pref, e_subject)
                                clear_cache(); st.success("Updated!"); st.rerun()
                        with col_d:
                            confirm_delete_teacher = st.checkbox("Confirm delete", key=f"del_t_confirm_{t['teacher_id']}")
                            if st.form_submit_button("🗑️ Delete"):
                                if not confirm_delete_teacher:
                                    st.error("Tick confirm delete first.")
                                else:
                                    delete_teacher(t["teacher_id"])
                                    clear_cache(); st.warning(f"Deleted {t['name']}"); st.rerun()

        # ── MANAGE CLASSROOMS ──
        elif page == "🏛️  Manage Classrooms":
            st.markdown('<div class="sec">Manage Classrooms</div><div class="sub">Add, edit or delete classrooms</div>', unsafe_allow_html=True)
            with st.expander("➕ Add New Classroom", expanded=False):
                with st.form("add_room"):
                    c1,c2,c3 = st.columns(3)
                    with c1: r_name = st.text_input("Room Name *")
                    with c2: r_cap  = st.number_input("Capacity *", min_value=1, value=30)
                    with c3: r_equip = st.text_input("Equipment", placeholder="Projector,Computers")
                    if st.form_submit_button("Add Classroom", type="primary"):
                        if r_name:
                            add_classroom(r_name, r_cap, r_equip)
                            clear_cache(); st.success(f"Room '{r_name}' added!"); st.rerun()
                        else: st.error("Room name is required.")
            st.divider()
            for _, r in rooms.iterrows():
                with st.expander(f"🏛️ {r['room_name']} — Capacity: {r['capacity']}"):
                    with st.form(f"edit_r_{r['room_id']}"):
                        c1,c2,c3 = st.columns(3)
                        with c1: e_rname = st.text_input("Name", value=r["room_name"])
                        with c2: e_rcap  = st.number_input("Capacity", min_value=1, value=int(r["capacity"]))
                        with c3: e_reqp  = st.text_input("Equipment", value=r["equipment"] or "")
                        col_s, col_d = st.columns([3,1])
                        with col_s:
                            if st.form_submit_button("💾 Save", type="primary"):
                                update_classroom(r["room_id"], e_rname, e_rcap, e_reqp)
                                clear_cache(); st.success("Updated!"); st.rerun()
                        with col_d:
                            confirm_delete_room = st.checkbox("Confirm delete", key=f"del_r_confirm_{r['room_id']}")
                            if st.form_submit_button("🗑️ Delete"):
                                if not confirm_delete_room:
                                    st.error("Tick confirm delete first.")
                                else:
                                    delete_classroom(r["room_id"])
                                    clear_cache(); st.warning(f"Deleted {r['room_name']}"); st.rerun()

        # ── MANAGE COURSES ──
        elif page == "📋  Manage Courses":
            st.markdown('<div class="sec">Manage Courses</div><div class="sub">Assign multiple teachers per course</div>', unsafe_allow_html=True)
            teacher_opts  = {row["name"]: row["teacher_id"] for _, row in teachers.iterrows()}
            group_opts    = {row["group_name"]: row["group_id"] for _, row in groups.iterrows()}
            with st.expander("➕ Add New Course", expanded=False):
                with st.form("add_course"):
                    c1,c2 = st.columns(2)
                    with c1:
                        c_name  = st.text_input("Course Name *")
                        c_group = st.selectbox("Student Group *", list(group_opts.keys()))
                        c_rtype = st.selectbox("Room Type *", ["Standard","Lab","Amphi"])
                    with c2:
                        c_teachers = st.multiselect("Assign Teachers * (can be multiple)", list(teacher_opts.keys()))
                    if st.form_submit_button("Add Course", type="primary"):
                        if c_name and c_teachers:
                            tids = [teacher_opts[t] for t in c_teachers]
                            add_course(c_name, group_opts[c_group], c_rtype, tids)
                            clear_cache(); st.success(f"Course '{c_name}' added!"); st.rerun()
                        else: st.error("Name and at least one teacher required.")
            st.divider()
            for _, co in courses.iterrows():
                teacher_list = co["teachers"] or "No teachers"
                with st.expander(f"📋 {co['course_name']} — {co['group_name']} — Teachers: {teacher_list}"):
                    conn = get_connection()
                    cur_tids = [r[0] for r in conn.execute(
                        "SELECT teacher_id FROM CourseTeachers WHERE course_id=?", (co["course_id"],)).fetchall()]
                    conn.close()
                    cur_tnames = [n for n,tid in teacher_opts.items() if tid in cur_tids]
                    with st.form(f"edit_c_{co['course_id']}"):
                        c1,c2 = st.columns(2)
                        with c1:
                            e_cname  = st.text_input("Name", value=co["course_name"])
                            e_cgroup = st.selectbox("Group", list(group_opts.keys()),
                                index=list(group_opts.keys()).index(co["group_name"]) if co["group_name"] in group_opts else 0)
                            e_crtype = st.selectbox("Room Type", ["Standard","Lab","Amphi"],
                                index=["Standard","Lab","Amphi"].index(co["required_room_type"]) if co["required_room_type"] in ["Standard","Lab","Amphi"] else 0)
                        with c2:
                            e_cteachers = st.multiselect("Teachers (multiple allowed)", list(teacher_opts.keys()), default=cur_tnames)
                        col_s,col_d = st.columns([3,1])
                        with col_s:
                            if st.form_submit_button("💾 Save", type="primary"):
                                tids = [teacher_opts[t] for t in e_cteachers]
                                update_course(co["course_id"], e_cname, group_opts[e_cgroup], e_crtype, tids)
                                clear_cache(); st.success("Updated!"); st.rerun()
                        with col_d:
                            confirm_delete_course = st.checkbox("Confirm delete", key=f"del_c_confirm_{co['course_id']}")
                            if st.form_submit_button("🗑️ Delete"):
                                if not confirm_delete_course:
                                    st.error("Tick confirm delete first.")
                                else:
                                    delete_course(co["course_id"])
                                    clear_cache(); st.warning(f"Deleted"); st.rerun()

        # ── AGENTS ──
        elif page == "🤖  Agents":
            st.markdown('<div class="sec">Agent Architecture</div><div class="sub">6 Mesa agents — all active</div>', unsafe_allow_html=True)
            agents_info = [
                ("SchedulerAgent", "Master Coordinator",
                 "Orchestrates the full pipeline. Picks the best available teacher per course, coordinates negotiation using counter-proposal hints from GroupAgent and RoomAgent, saves the schedule, and logs conflicts."),
                ("TeacherAgent", "Availability & Preferences",
                 "One per teacher. Proposes slots ranked by PreferenceAgent scores (learned across simulation runs). Accepts counter-proposal hints during negotiation to converge faster."),
                ("GroupAgent", "Conflict Prevention",
                 "One per student group. Prevents double-booking. On rejection, returns a counter-proposal hint — the group's next free slot — so SchedulerAgent can steer the next negotiation round."),
                ("RoomAgent", "Resource Management",
                 "One per classroom. Validates capacity vs group size and equipment requirements (Lab→Computers, Amphi→Microphone). Returns a hint slot when rejected."),
                ("ConstraintAgent", "Post-Scheduling Auditor",
                 "Runs after SchedulerAgent completes. Detects and logs four violation types: teacher double-booking, room double-booking, group overlap, and capacity violations. Results appear in the Conflicts log."),
                ("PreferenceAgent", "Adaptive Slot Scorer",
                 "Single shared agent. Maintains a preference score per (teacher, day, time_slot). Rewards preferred-slot usage (+0.2), decays forced negotiation slots (−0.1), clamped [0.1–3.0]. Scores persist across runs in the PreferenceScores table."),
            ]
            c1,c2 = st.columns(2)
            for i,(n,r,d) in enumerate(agents_info):
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div class="agent-card"><div class="aname"><span class="dot"></span>{n}</div><div class="arole">{r}</div><div class="adesc">{d}</div></div>', unsafe_allow_html=True)

        # ── CONFLICTS ──
        elif page == "⚠️  Conflicts":
            st.markdown('<div class="sec">Conflict Log</div><div class="sub">Unresolved scheduling conflicts</div>', unsafe_allow_html=True)
            if conflicts.empty:
                st.success("✅ No conflicts — all courses scheduled successfully!")
            else:
                for _, r in conflicts.iterrows():
                    st.markdown(f'<div class="conflict"><p>⚠️ {r["description"]}</p><p style="font-size:11px;color:#888;margin-top:3px">{r["timestamp"]}</p></div>', unsafe_allow_html=True)


        # ── EXPORT TIMETABLE ──
        elif page == "📤  Export Timetable":
            st.markdown('<div class="sec">Export Timetable</div><div class="sub">Download the schedule as Excel, PDF or CSV</div>', unsafe_allow_html=True)

            if sched.empty:
                st.warning("⚠️ No schedule to export. Run the simulation first.")
            else:
                st.markdown(f"""
                <div class="card">
                  <h4>📊 Schedule Summary</h4>
                  <p>{len(sched)} sessions across {sched["day"].nunique()} days · {sched["group_name"].nunique()} groups · {sched["teacher"].nunique()} professors</p>
                </div>""", unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("""
                    <div class="card" style="border-left:4px solid #1D9E75">
                      <h4>📗 Excel (.xlsx)</h4>
                      <p>Full timetable grid · Per-group sheets · Complete session list</p>
                    </div>""", unsafe_allow_html=True)
                    try:
                        xlsx_bytes = export_timetable_excel(sched, title="University Timetable")
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=xlsx_bytes,
                            file_name="timetable.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True, type="primary"
                        )
                    except Exception as e:
                        st.error(f"Excel error: {e}")

                with col2:
                    st.markdown("""
                    <div class="card" style="border-left:4px solid #D85A30">
                      <h4>📕 PDF (.pdf)</h4>
                      <p>Printable landscape timetable grid — ready to share</p>
                    </div>""", unsafe_allow_html=True)
                    try:
                        pdf_bytes = export_timetable_pdf(sched, title="University Timetable")
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name="timetable.pdf",
                            mime="application/pdf",
                            use_container_width=True, type="primary"
                        )
                    except Exception as e:
                        st.error(f"PDF error: {e}")

                with col3:
                    st.markdown("""
                    <div class="card" style="border-left:4px solid #185FA5">
                      <h4>📘 CSV (.csv)</h4>
                      <p>Raw session data — open in Excel, Google Sheets, or Python</p>
                    </div>""", unsafe_allow_html=True)
                    try:
                        csv_bytes = export_timetable_csv(sched)
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv_bytes,
                            file_name="timetable.csv",
                            mime="text/csv",
                            use_container_width=True, type="primary"
                        )
                    except Exception as e:
                        st.error(f"CSV error: {e}")

                st.divider()
                st.markdown("**Per-Group Export**", unsafe_allow_html=True)
                st.markdown('<div class="sub">Download timetable for a specific student group</div>', unsafe_allow_html=True)
                grp_list = sorted(sched["group_name"].unique().tolist())
                sel_grp = st.selectbox("Select group", grp_list)
                grp_df = sched[sched["group_name"] == sel_grp]
                col_a, col_b = st.columns(2)
                with col_a:
                    try:
                        grp_xlsx = export_timetable_excel(grp_df, title=f"Timetable — {sel_grp}")
                        st.download_button(f"⬇️ {sel_grp} — Excel", grp_xlsx,
                                           f"timetable_{sel_grp}.xlsx",
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                           use_container_width=True)
                    except Exception as e:
                        st.error(f"Error: {e}")
                with col_b:
                    try:
                        grp_csv = export_timetable_csv(grp_df)
                        st.download_button(f"⬇️ {sel_grp} — CSV", grp_csv,
                                           f"timetable_{sel_grp}.csv", "text/csv",
                                           use_container_width=True)
                    except Exception as e:
                        st.error(f"Error: {e}")

        # ── IMPORT DATASET ──
        elif page == "📥  Import Dataset":
            st.markdown('<div class="sec">Import Dataset</div><div class="sub">Bulk-import teachers, groups, classrooms or courses from CSV / Excel</div>', unsafe_allow_html=True)

            st.markdown("""
            <div class="card">
              <h4>📋 How it works</h4>
              <p>
                1. Download the CSV template for the data type you want to import<br>
                2. Fill in your data following the column format (keep headers exactly as shown)<br>
                3. Upload the filled file — the system will validate and import each row<br>
                4. Duplicate entries are skipped automatically<br>
                5. After importing, re-run the simulation to schedule new courses
              </p>
            </div>""", unsafe_allow_html=True)

            st.divider()

            entity_labels = {
                "teachers":   "👨‍🏫 Teachers",
                "groups":     "👥 Student Groups",
                "classrooms": "🏛️ Classrooms",
                "courses":    "📋 Courses",
            }

            sel_entity = st.radio("What do you want to import?",
                                   list(entity_labels.values()),
                                   horizontal=True)
            entity_key = {v: k for k, v in entity_labels.items()}[sel_entity]
            schema = SCHEMAS[entity_key]

            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown(f"**Required columns:** {', '.join(f'' for c in schema['required'])}")
                if schema["optional"]:
                    st.markdown(f"**Optional columns:** {', '.join(f'' for c in schema['optional'])}")

                template_csv = get_template_bytes(entity_key)
                st.download_button(
                    label=f"⬇️ Download {sel_entity} Template (CSV)",
                    data=template_csv,
                    file_name=f"template_{entity_key}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with col_right:
                st.markdown("**Preview of expected format:**")
                st.dataframe(schema["example"], use_container_width=True, hide_index=True)

            st.divider()
            st.markdown(f"**Upload your {sel_entity} file:**")
            uploaded = st.file_uploader(
                f"Choose CSV or Excel file",
                type=["csv", "xlsx", "xls"],
                key=f"import_{entity_key}",
                label_visibility="collapsed"
            )

            if uploaded:
                file_bytes = uploaded.read()
                st.info(f"📄 File: **{uploaded.name}** ({len(file_bytes):,} bytes) — ready to import")

                if st.button(f"🚀 Import {sel_entity.title()}", type="primary", use_container_width=True):
                    with st.spinner(f"Validating and importing {entity_key}..."):
                        imported, skipped, errors = run_import(entity_key, file_bytes, uploaded.name)

                    if imported > 0:
                        st.success(f"✅ Successfully imported **{imported}** {entity_key}.")
                    if skipped > 0:
                        st.warning(f"⏭️ Skipped **{skipped}** rows (duplicates or invalid data).")
                    if errors:
                        with st.expander(f"⚠️ {len(errors)} warning(s) / error(s)"):
                            for e in errors:
                                st.markdown(f"- {e}")
                    if imported > 0:
                        clear_cache()
                        st.info("💡 Re-run the simulation to schedule the newly imported courses.")

# ────────────────────────────────────────────────────────────
# PROFESSOR DASHBOARD
# ────────────────────────────────────────────────────────────
def show_professor():
    user = st.session_state.user
    tid  = user.get("teacher_id")
    uid  = user.get("user_id")
    my_reschedule_reqs = get_my_reschedule_requests(uid)
    my_catchup_reqs = get_my_catchup_requests(uid)

    page = build_sidebar(user, [
        "📅  My Timetable", "⚙️  My Availability", "📋  My Courses",
        "🔄  Request Reschedule", "📚  Request Catch-up", "📊  My Requests"
    ])

    sched = load_schedule()
    my_sched = sched[sched["teacher_id"]==tid] if not sched.empty and tid else pd.DataFrame()

    with st.container():

        if page == "📅  My Timetable":
            st.markdown(f'<div class="sec">My Timetable</div><div class="sub">Your scheduled sessions · 🔄 = catch-up</div>', unsafe_allow_html=True)
            render_timetable(my_sched, "tt-cell-prof")
            if not my_sched.empty:
                st.divider()
                disp_cols = ["course_name", "group_name", "day", "time_slot", "room_name", "session_type"]
                disp = my_sched[disp_cols + (["specific_date"] if "specific_date" in my_sched.columns else [])].copy()
                if "specific_date" in disp.columns:
                    disp["Calendar (dd/mm/yyyy)"] = disp["specific_date"].map(
                        lambda x: format_date_ddmmyyyy_or_dash(x) if pd.notna(x) and str(x).strip() else "—")
                    disp = disp.drop(columns=["specific_date"])
                st.dataframe(disp, use_container_width=True, hide_index=True)

        elif page == "⚙️  My Availability":
            st.markdown('<div class="sec">My Availability</div><div class="sub">Update your available days and preferred time slot</div>', unsafe_allow_html=True)
            if tid:
                conn = get_connection()
                row = conn.execute("SELECT * FROM Teachers WHERE teacher_id=?", (tid,)).fetchone()
                conn.close()
                if row:
                    with st.form("update_avail"):
                        current_days = [d.strip() for d in (row[3] or "").split(",")]
                        new_days = st.multiselect("Available Days", DAYS, default=[d for d in current_days if d in DAYS])
                        new_pref = st.selectbox("Preferred Time Slot", TIMES, index=TIMES.index(row[4]) if row[4] in TIMES else 0)
                        if st.form_submit_button("💾 Save Availability", type="primary"):
                            update_teacher(tid, row[1], row[2], ",".join(new_days), new_pref, row[5])
                            clear_cache()
                            st.success("Availability updated! Run the simulation to regenerate the timetable.")

        elif page == "📋  My Courses":
            st.markdown('<div class="sec">My Courses</div><div class="sub">Courses assigned to you</div>', unsafe_allow_html=True)
            conn = get_connection()
            my_courses = pd.read_sql_query("""
                SELECT co.course_name, g.group_name, g.program, g.year, co.required_room_type
                FROM CourseTeachers ct
                JOIN Courses co ON ct.course_id=co.course_id
                JOIN StudentGroups g ON co.group_id=g.group_id
                WHERE ct.teacher_id=?
            """, conn, params=(tid,))
            conn.close()
            if my_courses.empty:
                st.info("No courses assigned to you yet.")
            else:
                for _, c in my_courses.iterrows():
                    st.markdown(f"""
                    <div class="card">
                      <h4>{c['course_name']}</h4>
                      <p>{c['group_name']} · {c['program']} Year {c['year']}</p>
                      <span class="pill pr">{c['required_room_type']}</span>
                    </div>""", unsafe_allow_html=True)

        elif page == "🔄  Request Reschedule":
            st.markdown('<div class="sec">Request Session Reschedule</div><div class="sub">Ask admin to move one of your sessions to a different slot</div>', unsafe_allow_html=True)
            if my_sched.empty:
                st.info("No sessions found. The simulation must run first.")
            else:
                session_labels = {
                    f"{r['course_name']} | {r['day']} {r['time_slot']} | {r['room_name']}": r["session_id"]
                    for _, r in my_sched.iterrows()
                }
                sel_label = st.selectbox("Select Session to Reschedule", list(session_labels.keys()))
                sel_session_id = session_labels[sel_label]
                c1, c2, c3 = st.columns(3)
                with c1: prop_day = st.selectbox("Proposed New Day", [""] + DAYS)
                with c2: prop_time = st.selectbox("Proposed New Time", [""] + TIMES)
                with c3: prop_exact = _date_input("Target calendar date (dd/mm/yyyy, optional)", value=None)
                reason = st.text_area("Reason for Reschedule *", placeholder="Explain why this session needs to be moved...")
                if st.button("Submit Reschedule Request →", type="primary", use_container_width=True):
                    if not reason.strip():
                        st.error("Please provide a reason.")
                    elif has_partial_slot(prop_day, prop_time):
                        st.error("Provide both day and time, or leave both empty.")
                    else:
                        submit_reschedule_request(sel_session_id, uid, "professor", reason,
                                                  prop_day or None, prop_time or None, to_iso_date(prop_exact))
                        st.success("✅ Request submitted! Admin will review it shortly.")

        elif page == "📚  Request Catch-up":
            st.markdown('<div class="sec">Request Catch-up Session</div><div class="sub">Ask admin to schedule an extra makeup session for a course</div>', unsafe_allow_html=True)
            conn = get_connection()
            my_courses_cu = pd.read_sql_query("""
                SELECT co.course_id, co.course_name, g.group_name
                FROM CourseTeachers ct
                JOIN Courses co ON ct.course_id=co.course_id
                JOIN StudentGroups g ON co.group_id=g.group_id
                WHERE ct.teacher_id=?
            """, conn, params=(tid,))
            conn.close()
            if my_courses_cu.empty:
                st.info("No courses assigned to you.")
            else:
                course_opts = {f"{r['course_name']} — {r['group_name']}": (r["course_id"], tid) for _, r in my_courses_cu.iterrows()}
                sel_course_label = st.selectbox("Select Course *", list(course_opts.keys()))
                sel_course_id, sel_teacher_id = course_opts[sel_course_label]
                c1, c2, c3 = st.columns(3)
                with c1: cu_day = st.selectbox("Preferred Day", [""] + DAYS)
                with c2: cu_time = st.selectbox("Preferred Time", [""] + TIMES)
                with c3: cu_exact = _date_input("Preferred calendar date (dd/mm/yyyy) *", value=date.today())
                st.caption("The calendar date helps the office place the catch-up on the correct week.")
                cu_reason = st.text_area("Reason *", placeholder="E.g. Session cancelled due to national holiday, need makeup session...")
                if st.button("Submit Catch-up Request →", type="primary", use_container_width=True):
                    if not cu_reason.strip():
                        st.error("Please provide a reason.")
                    elif cu_exact is None:
                        st.error("Choose the preferred calendar date (dd/mm/yyyy).")
                    else:
                        submit_catchup_request(sel_course_id, sel_teacher_id, uid, "professor", cu_reason,
                                               cu_day or None, cu_time or None, to_iso_date(cu_exact))
                        st.success("✅ Catch-up request submitted! Admin will schedule it.")

        elif page == "📊  My Requests":
            st.markdown('<div class="sec">My Requests</div><div class="sub">Track all your submitted requests</div>', unsafe_allow_html=True)
            tab1, tab2 = st.tabs([f"🔄 Reschedule ({len(my_reschedule_reqs)})", f"📚 Catch-up ({len(my_catchup_reqs)})"])
            with tab1:
                if not my_reschedule_reqs:
                    st.info("You haven't submitted any reschedule requests.")
                for r in my_reschedule_reqs:
                    (req_id, reason, prop_day, prop_time, prop_exact, status, admin_note, created_at, course, curr_day, curr_time, curr_exact) = r
                    card_class = f"req-card req-card-{status}"
                    ce = f" · 📆 {format_date_ddmmyyyy_or_dash(curr_exact)}" if curr_exact else ""
                    pe = f" · 📆 {format_date_ddmmyyyy_or_dash(prop_exact)}" if prop_exact else ""
                    st.markdown(f"""
                    <div class="{card_class}">
                      <div style="font-size:14px;font-weight:700;color:#1a1a2e">{course}</div>
                      <div style="font-size:12px;color:#666;margin-top:3px">Current: {curr_day}, {curr_time}{ce} → Proposed: {prop_day or '—'}, {prop_time or '—'}{pe}</div>
                      <div style="font-size:12px;color:#555;margin-top:3px">Reason: {reason}</div>
                      {f'<div style="font-size:12px;color:#444;margin-top:3px">Admin note: {admin_note}</div>' if admin_note else ''}
                      <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
                        {status_badge(status)}
                        <span style="font-size:11px;color:#aaa">{created_at}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
            with tab2:
                if not my_catchup_reqs:
                    st.info("You haven't submitted any catch-up requests.")
                for cu in my_catchup_reqs:
                    (cu_id, reason, pref_day, pref_time, pref_exact, status, admin_note, created_at, course,
                     sched_day, sched_time, sched_exact, sched_room) = cu
                    card_class = f"req-card req-card-{'scheduled' if status=='scheduled' else status}"
                    pref_date = format_date_ddmmyyyy_or_dash(pref_exact) if pref_exact else "—"
                    sched_html = ""
                    if status == "scheduled" and sched_day:
                        sd = format_date_ddmmyyyy_or_dash(sched_exact) if sched_exact else "—"
                        sched_html = f'<div style="font-size:12px;color:#166534;margin-top:4px;font-weight:600">✓ Scheduled: {sched_day}, {sched_time} · 📆 {sd} · 🏛️ {sched_room or "—"}</div>'
                    st.markdown(f"""
                    <div class="{card_class}">
                      <div style="font-size:14px;font-weight:700;color:#1a1a2e">📚 {course}</div>
                      <div style="font-size:12px;color:#666;margin-top:3px">Preferred: {pref_day or 'Any'}, {pref_time or 'Any'} · 📆 <b>{pref_date}</b></div>
                      {sched_html}
                      <div style="font-size:12px;color:#555;margin-top:3px">Reason: {reason}</div>
                      {f'<div style="font-size:12px;color:#444;margin-top:3px">Admin note: {admin_note}</div>' if admin_note else ''}
                      <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
                        {status_badge(status)}
                        <span style="font-size:11px;color:#aaa">{created_at}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────
# STUDENT DASHBOARD
# ────────────────────────────────────────────────────────────
def show_student():
    user = st.session_state.user
    gid  = user.get("group_id")
    uid  = user.get("user_id")
    my_reschedule_reqs = get_my_reschedule_requests(uid)
    my_catchup_reqs = get_my_catchup_requests(uid)

    page = build_sidebar(user, [
        "📅  My Timetable", "📋  My Courses", "👨‍🏫  My Professors",
        "🔄  Request Reschedule", "📚  Request Catch-up", "📊  My Requests"
    ])

    sched = load_schedule()
    my_sched = sched[sched["group_id"]==gid] if not sched.empty and gid else pd.DataFrame()

    conn = get_connection()
    grp = conn.execute("SELECT * FROM StudentGroups WHERE group_id=?", (gid,)).fetchone() if gid else None
    # For catch-up: get my courses
    my_courses_cu = pd.read_sql_query("""
        SELECT DISTINCT co.course_id, co.course_name, ct.teacher_id, t.name as teacher_name
        FROM Courses co
        JOIN CourseTeachers ct ON co.course_id=ct.course_id
        JOIN Teachers t ON ct.teacher_id=t.teacher_id
        WHERE co.group_id=?
    """, conn, params=(gid,)) if gid else pd.DataFrame()
    conn.close()

    with st.container():

        if page == "📅  My Timetable":
            grp_name = grp[1] if grp else "Your Group"
            st.markdown(f'<div class="sec">My Timetable — {grp_name}</div><div class="sub">Your weekly class schedule · 🔄 = catch-up session</div>', unsafe_allow_html=True)
            if not my_sched.empty:
                st.markdown(f"""
                <div style="background:#E1F5EE;border-radius:10px;padding:12px 18px;margin-bottom:16px;display:flex;gap:24px">
                  <div><span style="font-size:11px;color:#065f46">GROUP</span><div style="font-size:14px;font-weight:700;color:#042C53">{grp[1] if grp else "—"}</div></div>
                  <div><span style="font-size:11px;color:#065f46">PROGRAM</span><div style="font-size:14px;font-weight:700;color:#042C53">{grp[2] if grp else "—"} · Year {grp[3] if grp else "—"}</div></div>
                  <div><span style="font-size:11px;color:#065f46">SESSIONS</span><div style="font-size:14px;font-weight:700;color:#042C53">{len(my_sched)} this week</div></div>
                </div>""", unsafe_allow_html=True)
            render_timetable(my_sched)

        elif page == "📋  My Courses":
            st.markdown('<div class="sec">My Courses</div><div class="sub">All courses scheduled for your group</div>', unsafe_allow_html=True)
            if my_sched.empty:
                st.info("No schedule yet.")
            else:
                unique = my_sched.drop_duplicates("course_name")
                for _, c in unique.iterrows():
                    sessions = my_sched[my_sched["course_name"]==c["course_name"]]
                    regular = sessions[sessions["session_type"]=="regular"] if "session_type" in sessions else sessions
                    catchups = sessions[sessions["session_type"]=="catchup"] if "session_type" in sessions else pd.DataFrame()
                    st.markdown(f"""
                    <div class="card">
                      <h4>{c['course_name']}</h4>
                      <p>👨‍🏫 {c['teacher']} · 🏛️ {c['room_name']}</p>
                      <div style="margin-top:8px">
                        {''.join(f'<span class="pill pd">{s["day"]}</span><span class="pill pt">{s["time_slot"]}</span>' for _,s in regular.iterrows())}
                        {''.join(f'<span class="pill po">🔄 {s["day"]}</span><span class="pill po">{s["time_slot"]}</span>' for _,s in catchups.iterrows())}
                      </div>
                    </div>""", unsafe_allow_html=True)

        elif page == "👨‍🏫  My Professors":
            st.markdown('<div class="sec">My Professors</div><div class="sub">Teachers of your courses</div>', unsafe_allow_html=True)
            if not my_sched.empty:
                profs = my_sched.drop_duplicates("teacher")[["teacher","course_name"]]
                for _, p in profs.iterrows():
                    st.markdown(f"""
                    <div class="card">
                      <h4>👨‍🏫 {p['teacher']}</h4>
                      <p>{p['course_name']}</p>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No professors found. Schedule not generated yet.")

        elif page == "🔄  Request Reschedule":
            st.markdown('<div class="sec">Request Session Reschedule</div><div class="sub">Ask admin to move a class to a different slot</div>', unsafe_allow_html=True)
            if my_sched.empty:
                st.info("No sessions found. Simulation must run first.")
            else:
                session_labels = {
                    f"{r['course_name']} | {r['day']} {r['time_slot']} | {r['room_name']}": r["session_id"]
                    for _, r in my_sched.iterrows()
                }
                sel_label = st.selectbox("Select Session", list(session_labels.keys()))
                sel_session_id = session_labels[sel_label]
                c1, c2, c3 = st.columns(3)
                with c1: prop_day = st.selectbox("Suggested New Day (optional)", [""] + DAYS)
                with c2: prop_time = st.selectbox("Suggested New Time (optional)", [""] + TIMES)
                with c3: prop_exact = _date_input("Target calendar date (dd/mm/yyyy, optional)", value=None)
                reason = st.text_area("Reason *", placeholder="E.g. Group has an exam conflict on that day...")
                if st.button("Submit Request →", type="primary", use_container_width=True):
                    if not reason.strip():
                        st.error("Please provide a reason.")
                    elif has_partial_slot(prop_day, prop_time):
                        st.error("Provide both day and time, or leave both empty.")
                    else:
                        submit_reschedule_request(sel_session_id, uid, "student", reason,
                                                  prop_day or None, prop_time or None, to_iso_date(prop_exact))
                        st.success("✅ Request submitted! Admin will review it.")

        elif page == "📚  Request Catch-up":
            st.markdown('<div class="sec">Request Catch-up Session</div><div class="sub">Ask admin to schedule a makeup session for a missed class</div>', unsafe_allow_html=True)
            if my_courses_cu.empty:
                st.info("No courses found for your group.")
            else:
                course_opts = {
                    f"{r['course_name']} — {r['teacher_name']}": (r["course_id"], r["teacher_id"])
                    for _, r in my_courses_cu.iterrows()
                }
                sel_label = st.selectbox("Select Course *", list(course_opts.keys()))
                sel_course_id, sel_teacher_id = course_opts[sel_label]
                c1, c2, c3 = st.columns(3)
                with c1: cu_day = st.selectbox("Preferred Day", [""] + DAYS)
                with c2: cu_time = st.selectbox("Preferred Time", [""] + TIMES)
                with c3: cu_exact = _date_input("Preferred calendar date (dd/mm/yyyy) *", value=date.today())
                st.caption("The calendar date helps the office place the catch-up on the correct week.")
                cu_reason = st.text_area("Reason *", placeholder="E.g. Last session was cancelled, we need to make up for it...")
                if st.button("Submit Catch-up Request →", type="primary", use_container_width=True):
                    if not cu_reason.strip():
                        st.error("Please provide a reason.")
                    elif cu_exact is None:
                        st.error("Choose the preferred calendar date (dd/mm/yyyy).")
                    else:
                        submit_catchup_request(sel_course_id, sel_teacher_id, uid, "student", cu_reason,
                                               cu_day or None, cu_time or None, to_iso_date(cu_exact))
                        st.success("✅ Catch-up request submitted!")

        elif page == "📊  My Requests":
            st.markdown('<div class="sec">My Requests</div><div class="sub">Track all your submitted requests</div>', unsafe_allow_html=True)
            tab1, tab2 = st.tabs([f"🔄 Reschedule ({len(my_reschedule_reqs)})", f"📚 Catch-up ({len(my_catchup_reqs)})"])
            with tab1:
                if not my_reschedule_reqs:
                    st.info("No reschedule requests submitted yet.")
                for r in my_reschedule_reqs:
                    (req_id, reason, prop_day, prop_time, prop_exact, status, admin_note, created_at, course, curr_day, curr_time, curr_exact) = r
                    card_class = f"req-card req-card-{status}"
                    ce = f" · 📆 {format_date_ddmmyyyy_or_dash(curr_exact)}" if curr_exact else ""
                    pe = f" · 📆 {format_date_ddmmyyyy_or_dash(prop_exact)}" if prop_exact else ""
                    st.markdown(f"""
                    <div class="{card_class}">
                      <div style="font-size:14px;font-weight:700;color:#1a1a2e">{course}</div>
                      <div style="font-size:12px;color:#666;margin-top:3px">Current: {curr_day}, {curr_time}{ce} → Suggested: {prop_day or '—'}, {prop_time or '—'}{pe}</div>
                      <div style="font-size:12px;color:#555;margin-top:3px">Reason: {reason}</div>
                      {f'<div style="font-size:12px;color:#444;margin-top:3px">Admin note: {admin_note}</div>' if admin_note else ''}
                      <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
                        {status_badge(status)}
                        <span style="font-size:11px;color:#aaa">{created_at}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
            with tab2:
                if not my_catchup_reqs:
                    st.info("No catch-up requests submitted yet.")
                for cu in my_catchup_reqs:
                    (cu_id, reason, pref_day, pref_time, pref_exact, status, admin_note, created_at, course,
                     sched_day, sched_time, sched_exact, sched_room) = cu
                    card_class = f"req-card req-card-{'scheduled' if status=='scheduled' else status}"
                    pref_date = format_date_ddmmyyyy_or_dash(pref_exact) if pref_exact else "—"
                    sched_html = ""
                    if status == "scheduled" and sched_day:
                        sd = format_date_ddmmyyyy_or_dash(sched_exact) if sched_exact else "—"
                        sched_html = f'<div style="font-size:12px;color:#166534;margin-top:4px;font-weight:600">✓ Scheduled: {sched_day}, {sched_time} · 📆 {sd} · 🏛️ {sched_room or "—"}</div>'
                    st.markdown(f"""
                    <div class="{card_class}">
                      <div style="font-size:14px;font-weight:700;color:#1a1a2e">📚 {course}</div>
                      <div style="font-size:12px;color:#666;margin-top:3px">Preferred: {pref_day or 'Any'}, {pref_time or 'Any'} · 📆 <b>{pref_date}</b></div>
                      {sched_html}
                      <div style="font-size:12px;color:#555;margin-top:3px">Reason: {reason}</div>
                      {f'<div style="font-size:12px;color:#444;margin-top:3px">Admin note: {admin_note}</div>' if admin_note else ''}
                      <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
                        {status_badge(status)}
                        <span style="font-size:11px;color:#aaa">{created_at}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────
# ROUTER
# ────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.auth_page == "login": show_login()
    else: show_register()
else:
    role = st.session_state.user["role"]
    if role == "admin":     show_admin()
    elif role == "professor": show_professor()
    else:                   show_student()
