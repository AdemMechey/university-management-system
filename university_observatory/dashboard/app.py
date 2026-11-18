"""
DASHBOARD v4 — University Observatory (Professional Design)
Run: python -m streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection, register_user, login_user
from agents.agent_recommendation import AgentRecommendation

st.set_page_config(
    page_title="University Observatory",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── GLOBAL CSS ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {visibility: hidden;}
[data-testid="stToolbar"] {display: none;}
.block-container {padding: 0 !important; max-width: 100% !important;}

/* ── Sidebar styling ── */
[data-testid="stSidebar"] {
    background: #042C53 !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * {color: rgba(255,255,255,0.75) !important;}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {color: #ffffff !important;}
[data-testid="stSidebar"] .stRadio label {
    color: rgba(255,255,255,0.75) !important;
    font-size: 14px;
}
[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,0.1) !important;}
[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.06) !important;
    border: 0.5px solid rgba(255,255,255,0.15) !important;
    color: rgba(255,255,255,0.75) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.12) !important;
    color: white !important;
}

/* ── Main background ── */
.main .block-container, [data-testid="stAppViewContainer"] > .main {
    background: #f0f2f6 !important;
}

/* ── Cards ── */
.pro-card {
    background: white;
    border: 0.5px solid #e0e0e0;
    border-radius: 12px;
    padding: 22px 24px;
    margin-bottom: 14px;
}
.pro-card h3 {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a2e;
    margin-bottom: 4px;
}

/* ── Hero banner ── */
.hero-banner {
    background: linear-gradient(135deg, #042C53 0%, #185FA5 100%);
    border-radius: 14px;
    padding: 36px 40px;
    margin-bottom: 22px;
    color: white;
}
.hero-banner h2 {font-size: 24px; font-weight: 700; margin-bottom: 6px;}
.hero-banner p {font-size: 14px; opacity: 0.7; margin-bottom: 24px;}

/* ── KPI cards ── */
.kpi-card {
    background: white;
    border: 0.5px solid #e8e8e8;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.kpi-card .kpi-num {font-size: 28px; font-weight: 700; color: #042C53;}
.kpi-card .kpi-lbl {font-size: 12px; color: #888; margin-top: 2px;}
.kpi-card .kpi-badge {
    display: inline-block; margin-top: 8px;
    padding: 2px 10px; border-radius: 99px;
    font-size: 11px; font-weight: 600;
}
.badge-blue {background: #dbeafe; color: #1e40af;}
.badge-green {background: #dcfce7; color: #166534;}
.badge-amber {background: #fef3c7; color: #92400e;}
.badge-teal {background: #d1fae5; color: #065f46;}
.badge-red {background: #fee2e2; color: #991b1b;}

/* ── Opportunity cards ── */
.opp-card {
    background: white;
    border: 0.5px solid #e0e0e0;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 10px;
    transition: transform 0.1s, border-color 0.15s;
    cursor: pointer;
}
.opp-card:hover {border-color: #185FA5;}
.opp-header {display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;}
.opp-title {font-size: 15px; font-weight: 600; color: #1a1a2e;}
.opp-sub {font-size: 12px; color: #666; margin-top: 3px;}
.pill {
    display: inline-block; padding: 3px 10px;
    border-radius: 99px; font-size: 11px; font-weight: 600;
    margin-right: 5px; margin-top: 8px;
}
.pill-type-internship {background:#dbeafe; color:#1e40af;}
.pill-type-scholarship {background:#dcfce7; color:#166534;}
.pill-type-certification {background:#fef3c7; color:#92400e;}
.pill-type-project {background:#fce7f3; color:#9d174d;}
.pill-deadline {background:#fee2e2; color:#991b1b;}
.pill-source {background:#f3f4f6; color:#374151;}
.pill-location {background:#ede9fe; color:#5b21b6;}

.match-pct {
    font-size: 20px; font-weight: 700; color: #1D9E75;
    text-align: right; white-space: nowrap;
}
.match-lbl {font-size: 10px; color: #888; text-align: right;}
.open-btn {
    display: inline-block;
    background: #042C53; color: white;
    padding: 7px 18px; border-radius: 8px;
    font-size: 12px; font-weight: 600;
    text-decoration: none; margin-top: 12px;
}
.open-btn:hover {background: #185FA5; color: white;}

/* ── Score bars ── */
.score-row {display: flex; align-items: center; gap: 10px; margin-bottom: 6px;}
.score-label {width: 80px; font-size: 12px; color: #666; flex-shrink: 0;}
.score-track {flex: 1; height: 5px; background: #e5e7eb; border-radius: 3px; overflow: hidden;}
.score-fill-green {height: 100%; border-radius: 3px; background: #1D9E75;}
.score-fill-amber {height: 100%; border-radius: 3px; background: #BA7517;}
.score-pct-lbl {width: 32px; font-size: 12px; font-weight: 600; color: #333; text-align: right;}

/* ── Agent cards ── */
.agent-card {
    background: white; border: 0.5px solid #e0e0e0;
    border-radius: 12px; padding: 18px 20px; margin-bottom: 12px;
}
.agent-name {font-size: 14px; font-weight: 700; color: #042C53; margin-bottom: 4px;}
.agent-role {font-size: 12px; color: #1D9E75; font-weight: 600; margin-bottom: 8px;}
.agent-desc {font-size: 13px; color: #555; line-height: 1.6;}
.status-active {display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #1D9E75; margin-right: 6px;}

/* ── Section titles ── */
.section-title {
    font-size: 18px; font-weight: 700; color: #1a1a2e;
    margin-bottom: 4px;
}
.section-sub {font-size: 13px; color: #888; margin-bottom: 18px;}

/* ── Terminal log ── */
.log-box {
    background: #042C53; border-radius: 10px;
    padding: 16px 18px; font-family: monospace;
    font-size: 12px; color: #9FE1CB; line-height: 1.9;
}

/* ── Deadline rows ── */
.deadline-row {
    display: flex; align-items: center; gap: 14px;
    padding: 12px 0; border-bottom: 0.5px solid #f0f0f0;
}
.deadline-date-box {
    width: 42px; height: 42px; background: #f3f4f6;
    border-radius: 8px; display: flex; flex-direction: column;
    align-items: center; justify-content: center; flex-shrink: 0;
}
.deadline-date-box .dd {font-size: 15px; font-weight: 700; color: #1a1a2e; line-height: 1;}
.deadline-date-box .dm {font-size: 10px; color: #888; margin-top: 1px;}

/* ── Profile ── */
.profile-header-card {
    background: white; border: 0.5px solid #e0e0e0;
    border-radius: 14px; padding: 28px 32px;
    display: flex; gap: 22px; align-items: center;
    margin-bottom: 20px;
}

/* ── Auth pages ── */
.auth-container {
    max-width: 480px; margin: 60px auto; padding: 0 20px;
}
.auth-card {
    background: white; border: 0.5px solid #e0e0e0;
    border-radius: 16px; padding: 40px 40px;
}
.auth-logo {
    text-align: center; margin-bottom: 28px;
}
.auth-logo .logo-circle {
    width: 52px; height: 52px; background: #042C53;
    border-radius: 14px; display: flex; align-items: center;
    justify-content: center; margin: 0 auto 12px; font-size: 22px;
}
.auth-logo h1 {font-size: 20px; font-weight: 700; color: #1a1a2e;}
.auth-logo p {font-size: 13px; color: #888; margin-top: 4px;}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

# ── DATA LOADERS ───────────────────────────────────────────
@st.cache_data(ttl=30)
def load_opportunities():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Opportunities", conn)
    conn.close()
    return df

@st.cache_data(ttl=30)
def load_my_recommendations(user_id):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT r.score, r.score_breakdown, o.title, o.type, o.source,
               o.location, o.eligibility, o.deadline, o.url, o.description
        FROM Recommendations r
        JOIN Opportunities o ON r.opportunity_id = o.id
        WHERE r.user_id = ?
        ORDER BY r.score DESC
    """, conn, params=(user_id,))
    conn.close()
    return df

@st.cache_data(ttl=30)
def load_my_notifications(user_id):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT n.notification_id, o.title, o.type, o.source, o.deadline, o.url, n.status
        FROM Notifications n
        JOIN Opportunities o ON n.opportunity_id = o.id
        WHERE n.user_id = ?
        ORDER BY n.timestamp DESC
    """, conn, params=(user_id,))
    conn.close()
    return df

@st.cache_data(ttl=30)
def load_clusters():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM OpportunityClusters", conn)
    conn.close()
    return df

def mark_notifications_read(user_id):
    conn = get_connection()
    conn.execute("UPDATE Notifications SET status='read' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

TYPE_ICONS = {"internship": "💼", "scholarship": "🎓", "certification": "📜", "project": "🔬"}
TYPE_COLORS = {"internship": "pill-type-internship", "scholarship": "pill-type-scholarship",
               "certification": "pill-type-certification", "project": "pill-type-project"}

# ── AUTH PAGES ─────────────────────────────────────────────
def show_login():
    st.markdown("""
    <div class="auth-container">
      <div class="auth-logo">
        <div class="logo-circle">🎓</div>
        <h1>University Observatory</h1>
        <p>Multi-Agent Opportunity Intelligence</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.container():
            st.markdown("### Sign in to your account")
            email = st.text_input("Email address", placeholder="you@university.tn")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign In →", use_container_width=True, type="primary"):
                if email and password:
                    user = login_user(email, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        rec_agent = AgentRecommendation(score_threshold=0.3)
                        rec_agent.recommend_for_user(user["user_id"])
                        st.success(f"Welcome back, {user['name']}!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.warning("Please enter your credentials.")
            st.divider()
            st.markdown("<p style='text-align:center;font-size:13px;color:#888'>Don't have an account?</p>", unsafe_allow_html=True)
            if st.button("Create Account", use_container_width=True):
                st.session_state.auth_page = "register"
                st.rerun()
            st.markdown("<br><p style='text-align:center;font-size:12px;color:#aaa'>Demo: alice@univ.tn / password123</p>", unsafe_allow_html=True)


def show_register():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("### Create your account")
        st.caption("Fill in your academic profile for personalized recommendations")
        st.divider()

        st.markdown("**Personal Information**")
        name = st.text_input("Full Name *", placeholder="e.g. Alice Ben Salah")
        email = st.text_input("Email Address *", placeholder="you@university.tn")
        col_a, col_b = st.columns(2)
        with col_a:
            password = st.text_input("Password *", type="password")
        with col_b:
            password2 = st.text_input("Confirm Password *", type="password")

        st.divider()
        st.markdown("**Academic Profile**")
        col_a, col_b = st.columns(2)
        with col_a:
            degree = st.selectbox("Degree Level *", ["Bachelor", "Master", "PhD", "Postdoc", "Researcher"])
        with col_b:
            field_of_study = st.selectbox("Field of Study *", [
                "Computer Science", "Data Science", "Artificial Intelligence",
                "Software Engineering", "Mathematics", "Biomedical", "Electronics", "Business", "Other"
            ])
        years_exp = st.slider("Years of Experience", 0, 20, 0)

        st.divider()
        st.markdown("**Interests & Skills** *(comma-separated)*")
        interests = st.text_input("Interests *", placeholder="machine learning, nlp, computer vision")
        skills = st.text_input("Skills *", placeholder="python, tensorflow, pytorch, sql")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Create Account →", use_container_width=True, type="primary"):
            if not all([name, email, password, password2, interests, skills]):
                st.error("Please fill in all required fields.")
            elif password != password2:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, msg = register_user(name, email, password, degree,
                                        field_of_study.lower(), years_exp, interests, skills)
                if ok:
                    st.success("Account created! Please sign in.")
                    st.session_state.auth_page = "login"
                    st.rerun()
                else:
                    st.error(msg)

        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


# ── MAIN APP ───────────────────────────────────────────────
def show_app():
    user = st.session_state.user
    opps = load_opportunities()
    recs = load_my_recommendations(user["user_id"])
    notifs = load_my_notifications(user["user_id"])
    clusters = load_clusters()
    unread = len(notifs[notifs["status"] == "unread"]) if not notifs.empty else 0

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:8px 0 16px">
          <div style="width:38px;height:38px;background:#1D9E75;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:10px">🎓</div>
          <div style="font-size:13px;font-weight:700;color:white">University Observatory</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:2px">Multi-Agent Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.06);border-radius:10px;padding:12px 14px;margin-bottom:14px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;background:#185FA5;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:white;flex-shrink:0">{user['name'][:2].upper()}</div>
          <div>
            <div style="font-size:13px;font-weight:600;color:white">{user['name'].split()[0]}</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.4)">{user['degree']} · {user.get('field_of_study','')[:15]}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        notif_label = f"🔔 Notifications  ({unread} new)" if unread > 0 else "🔔 Notifications"
        page = st.radio("", [
            "🏠  Home",
            "💡  My Recommendations",
            "🔍  Browse All",
            "🤖  Agents Status",
            "🌐  Data Sources",
            notif_label,
            "👤  My Profile",
        ], label_visibility="collapsed")

        st.divider()
        if st.button("Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

    # ── PAGE CONTENT ──
    pad = st.container()
    with pad:
        st.markdown('<div style="padding: 28px 36px;">', unsafe_allow_html=True)

        # ─────────────── HOME ───────────────
        if page == "🏠  Home":
            st.markdown(f"""
            <div class="hero-banner">
              <h2>Welcome back, {user['name'].split()[0]} 👋</h2>
              <p>Your personalized opportunity feed · {user['degree']} in {user.get('field_of_study','')}</p>
              <div style="display:flex;gap:36px">
                <div><div style="font-size:24px;font-weight:700">{len(opps)}</div><div style="font-size:11px;opacity:0.55">Opportunities</div></div>
                <div><div style="font-size:24px;font-weight:700">{len(recs)}</div><div style="font-size:11px;opacity:0.55">Recommended</div></div>
                <div><div style="font-size:24px;font-weight:700">{len(clusters)}</div><div style="font-size:11px;opacity:0.55">Clusters</div></div>
                <div><div style="font-size:24px;font-weight:700">{unread}</div><div style="font-size:11px;opacity:0.55">New Alerts</div></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            type_counts = opps["type"].value_counts() if not opps.empty else {}
            with c1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-num">{type_counts.get("internship",0)}</div><div class="kpi-lbl">Internships</div><span class="kpi-badge badge-blue">Active</span></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-num">{type_counts.get("scholarship",0)}</div><div class="kpi-lbl">Scholarships</div><span class="kpi-badge badge-green">Open</span></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-num">{type_counts.get("certification",0)}</div><div class="kpi-lbl">Certifications</div><span class="kpi-badge badge-amber">Enroll</span></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="kpi-card"><div class="kpi-num">{type_counts.get("project",0)}</div><div class="kpi-lbl">Projects</div><span class="kpi-badge badge-teal">Research</span></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown('<p style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:12px">Top Matches For You</p>', unsafe_allow_html=True)
                if not recs.empty:
                    for _, r in recs.head(3).iterrows():
                        pct = int(r["score"] * 100)
                        tc = TYPE_COLORS.get(r["type"], "pill-source")
                        icon = TYPE_ICONS.get(r["type"], "📋")
                        st.markdown(f"""
                        <div class="opp-card">
                          <div class="opp-header">
                            <div>
                              <div class="opp-title">{icon} {r['title']}</div>
                              <div class="opp-sub">{r['source']} · {r['location']}</div>
                              <span class="pill {tc}">{r['type'].capitalize()}</span>
                              <span class="pill pill-deadline">{r['deadline']}</span>
                            </div>
                            <div>
                              <div class="match-pct">{pct}%</div>
                              <div class="match-lbl">match</div>
                            </div>
                          </div>
                          <a href="{r['url']}" target="_blank" class="open-btn">Open →</a>
                        </div>
                        """, unsafe_allow_html=True)

            with col_b:
                st.markdown('<p style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:12px">Upcoming Deadlines</p>', unsafe_allow_html=True)
                if not opps.empty:
                    opps_copy = opps.copy()
                    opps_copy["deadline_dt"] = pd.to_datetime(opps_copy["deadline"], errors="coerce")
                    today = pd.Timestamp.now()
                    upcoming = opps_copy[opps_copy["deadline_dt"] > today].sort_values("deadline_dt").head(5)
                    for _, r in upcoming.iterrows():
                        try:
                            dd = r["deadline_dt"].strftime("%d")
                            dm = r["deadline_dt"].strftime("%b")
                            days_left = (r["deadline_dt"] - today).days
                            urgency_color = "#fee2e2" if days_left < 30 else "#fef3c7" if days_left < 60 else "#dcfce7"
                            urgency_text = "#991b1b" if days_left < 30 else "#92400e" if days_left < 60 else "#166534"
                        except:
                            dd, dm, days_left = "?", "?", 999
                            urgency_color, urgency_text = "#f3f4f6", "#374151"
                        st.markdown(f"""
                        <div class="deadline-row">
                          <div class="deadline-date-box"><div class="dd">{dd}</div><div class="dm">{dm}</div></div>
                          <div style="flex:1"><div style="font-size:13px;font-weight:600;color:#1a1a2e">{r['title'][:45]}</div><div style="font-size:11px;color:#888">{r['source']}</div></div>
                          <span style="background:{urgency_color};color:{urgency_text};padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600;white-space:nowrap">{days_left}d</span>
                        </div>
                        """, unsafe_allow_html=True)

        # ─────────────── RECOMMENDATIONS ───────────────
        elif page == "💡  My Recommendations":
            st.markdown('<div class="section-title">My Recommendations</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Matched using degree · field of study · skills · interests · experience</div>', unsafe_allow_html=True)

            if recs.empty:
                st.info("No recommendations yet. Sign out and sign back in to refresh.")
            else:
                types = ["All"] + sorted(recs["type"].unique().tolist())
                col1, col2 = st.columns([2, 4])
                with col1:
                    selected_type = st.selectbox("Filter by type", types, label_visibility="collapsed")
                filtered = recs if selected_type == "All" else recs[recs["type"] == selected_type]

                for _, r in filtered.iterrows():
                    pct = int(r["score"] * 100)
                    icon = TYPE_ICONS.get(r["type"], "📋")
                    tc = TYPE_COLORS.get(r["type"], "pill-source")
                    color = "#1D9E75" if pct >= 60 else "#BA7517" if pct >= 40 else "#D85A30"
                    desc = (r["description"] or "")
                    if "] " in desc:
                        desc = desc.split("] ")[-1]

                    breakdown_html = ""
                    if r.get("score_breakdown"):
                        try:
                            bd = json.loads(r["score_breakdown"])
                            rows = ""
                            for factor, val in bd.items():
                                w = int(val * 100)
                                fill_cls = "score-fill-green" if val >= 0.5 else "score-fill-amber"
                                rows += f'<div class="score-row"><span class="score-label">{factor.capitalize()}</span><div class="score-track"><div class="{fill_cls}" style="width:{w}%"></div></div><span class="score-pct-lbl">{w}%</span></div>'
                            breakdown_html = f'<div style="margin-top:14px;padding-top:14px;border-top:0.5px solid #f0f0f0">{rows}</div>'
                        except:
                            pass

                    st.markdown(f"""
                    <div class="opp-card">
                      <div class="opp-header">
                        <div style="flex:1">
                          <div class="opp-title">{icon} {r['title']}</div>
                          <div class="opp-sub">{r['source']} · {r['location']} · {r['eligibility']}</div>
                          <span class="pill {tc}">{r['type'].capitalize()}</span>
                          <span class="pill pill-deadline">Deadline: {r['deadline']}</span>
                          <span class="pill pill-location">📍 {r['location']}</span>
                          <p style="font-size:12px;color:#666;margin-top:10px;line-height:1.6">{desc[:200]}...</p>
                          {breakdown_html}
                          <a href="{r['url']}" target="_blank" class="open-btn">Open Opportunity →</a>
                        </div>
                        <div style="text-align:right;flex-shrink:0;padding-left:16px">
                          <div style="font-size:28px;font-weight:700;color:{color}">{pct}%</div>
                          <div style="font-size:11px;color:#888">match score</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

        # ─────────────── BROWSE ALL ───────────────
        elif page == "🔍  Browse All":
            st.markdown('<div class="section-title">Browse All Opportunities</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="section-sub">{len(opps)} opportunities from multiple sources</div>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1.5, 2, 1.5])
            with col1:
                type_f = st.selectbox("Type", ["All", "Internship", "Scholarship", "Certification", "Project"], label_visibility="collapsed")
            with col2:
                search = st.text_input("Search", placeholder="🔎  Search by title, source, keyword...", label_visibility="collapsed")
            with col3:
                sort = st.selectbox("Sort", ["Deadline ↑", "Title A–Z", "Source"], label_visibility="collapsed")

            filtered = opps.copy()
            if type_f != "All":
                filtered = filtered[filtered["type"] == type_f.lower()]
            if search:
                mask = (filtered["title"].str.contains(search, case=False, na=False) |
                        filtered["source"].str.contains(search, case=False, na=False) |
                        filtered["description"].str.contains(search, case=False, na=False))
                filtered = filtered[mask]
            if sort == "Deadline ↑":
                filtered["_dt"] = pd.to_datetime(filtered["deadline"], errors="coerce")
                filtered = filtered.sort_values("_dt")
            elif sort == "Title A–Z":
                filtered = filtered.sort_values("title")
            elif sort == "Source":
                filtered = filtered.sort_values("source")

            st.markdown(f"<p style='font-size:13px;color:#888;margin-bottom:12px'>{len(filtered)} results</p>", unsafe_allow_html=True)

            for _, r in filtered.iterrows():
                icon = TYPE_ICONS.get(r["type"], "📋")
                tc = TYPE_COLORS.get(r["type"], "pill-source")
                desc = (r["description"] or "")
                if "] " in desc:
                    desc = desc.split("] ")[-1]
                st.markdown(f"""
                <div class="opp-card">
                  <div class="opp-header">
                    <div style="flex:1">
                      <div class="opp-title">{icon} {r['title']}</div>
                      <div class="opp-sub">{r['source']} · {r['location']}</div>
                      <span class="pill {tc}">{r['type'].capitalize()}</span>
                      <span class="pill pill-source">{r['source']}</span>
                      <span class="pill pill-location">📍 {r['location']}</span>
                      <span class="pill pill-deadline">⏰ {r['deadline']}</span>
                      <p style="font-size:12px;color:#666;margin-top:8px">{desc[:180]}...</p>
                    </div>
                    <div style="flex-shrink:0;padding-left:16px;display:flex;flex-direction:column;align-items:flex-end;gap:8px">
                      <span class="pill pill-source">🎯 {r['eligibility']}</span>
                      <a href="{r['url']}" target="_blank" class="open-btn">Open →</a>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # ─────────────── AGENTS ───────────────
        elif page == "🤖  Agents Status":
            st.markdown('<div class="section-title">Multi-Agent System</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">5 active agents — all systems operational</div>', unsafe_allow_html=True)

            agents = [
                ("AgentObserver", "Data Collection", "Collects real data from 7 sources: arXiv API, OpenAlex API, RemoteOK API, HackerNews API, Scholars4Dev scraping, AIJobs scraping, and curated static data. Deduplication prevents duplicate entries.", "20 collected"),
                ("AgentClassifier", "NLP Classification", "Keyword-based NLP engine tags each opportunity with domain labels (NLP, Computer Vision, Machine Learning, Data Science, AI Ethics...) and academic level (Beginner, Intermediate, Advanced).", "20 classified"),
                ("AgentCluster", "KMeans Clustering", "TF-IDF vectorization converts opportunity text into feature vectors. KMeans groups them into 4 semantic clusters: Internships, Scholarships, Certifications, and Research Projects.", f"{len(clusters)} clusters"),
                ("AgentRecommendation", "Smart Matching", "Multi-factor weighted scoring system: Degree Level (25%) + Field of Study (25%) + Skills (20%) + Interests (20%) + Experience (10%). Top 8 matches per user.", f"{len(recs)} recommendations"),
                ("AgentCoordinator", "Orchestration", "Master orchestrator that runs all agents in the correct pipeline order. Handles initialization, error recovery, and scheduling coordination with the auto-scheduler.", "Always active"),
            ]

            col1, col2 = st.columns(2)
            for i, (name, role, desc, stat) in enumerate(agents):
                with (col1 if i % 2 == 0 else col2):
                    st.markdown(f"""
                    <div class="agent-card">
                      <div class="agent-name"><span class="status-active"></span>{name}</div>
                      <div class="agent-role">{role}</div>
                      <div class="agent-desc">{desc}</div>
                      <div style="margin-top:10px">
                        <span class="pill badge-green">{stat}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown('<div class="section-title" style="margin-top:8px">Pipeline Log</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="log-box">
              [AgentCoordinator] Starting pipeline...<br>
              [AgentObserver]    Collecting from arXiv, OpenAlex, RemoteOK...<br>
              [AgentObserver]    Collecting from HackerNews, Scholars4Dev, AIJobs...<br>
              [AgentObserver]    Done — opportunities collected ✓<br>
              [AgentClassifier]  NLP tagging — domains and levels assigned ✓<br>
              [AgentCluster]     TF-IDF + KMeans — 4 clusters created ✓<br>
              [AgentRecommendation] Weighted scoring complete ✓<br>
              [AgentCoordinator] Pipeline complete ✓
            </div>
            """, unsafe_allow_html=True)

        # ─────────────── DATA SOURCES ───────────────
        elif page == "🌐  Data Sources":
            st.markdown('<div class="section-title">Data Sources</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Live collection from 7 sources — auto-updated every 6 hours via scheduler.py</div>', unsafe_allow_html=True)

            sources = [
                ("arXiv API", "Free API · No key needed", "Research papers in cs.AI, cs.LG, cs.CL — latest submissions", "badge-teal", "https://export.arxiv.org"),
                ("OpenAlex API", "Free API · No key needed", "Academic works and affiliated institution data worldwide", "badge-teal", "https://api.openalex.org"),
                ("RemoteOK API", "Free API · No key needed", "Remote ML/AI internship and job listings", "badge-teal", "https://remoteok.com/api"),
                ("HackerNews API", "Free API · No key needed", "Tech job postings from HN Who is Hiring threads", "badge-teal", "https://hacker-news.firebaseio.com"),
                ("Scholars4Dev", "Web Scraping", "International scholarships and fellowships for students", "badge-amber", "https://www.scholars4dev.com"),
                ("AIJobs.net", "Web Scraping", "AI/ML specific internship listings from companies worldwide", "badge-amber", "https://aijobs.net"),
                ("Static Curated", "Built-in Fallback", "20 hand-picked high-quality opportunities — always available", "badge-blue", "#"),
            ]

            col1, col2 = st.columns(2)
            for i, (name, stype, desc, badge, url) in enumerate(sources):
                with (col1 if i % 2 == 0 else col2):
                    st.markdown(f"""
                    <div class="agent-card">
                      <div class="agent-name">{name}</div>
                      <span class="kpi-badge {badge}" style="font-size:11px">{stype}</span>
                      <div class="agent-desc" style="margin-top:8px">{desc}</div>
                      <a href="{url}" target="_blank" style="font-size:12px;color:#185FA5;margin-top:8px;display:inline-block">Visit source →</a>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            st.markdown("**Manual Refresh**")
            if st.button("🔄 Run Data Collection Now", type="primary"):
                with st.spinner("Collecting from all sources..."):
                    try:
                        from agents.agent_observer import AgentObserver
                        from agents.agent_classifier import AgentClassifier
                        from agents.agent_cluster import AgentCluster
                        n = AgentObserver().collect_all()
                        AgentClassifier().classify_all()
                        AgentCluster(n_clusters=4).cluster_all()
                        AgentRecommendation(score_threshold=0.3).recommend_for_user(user["user_id"])
                        st.success(f"✅ Done! {n} new opportunities added.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error: {e}")

        # ─────────────── NOTIFICATIONS ───────────────
        elif "Notifications" in page:
            st.markdown('<div class="section-title">Notifications</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="section-sub">{unread} unread alerts</div>', unsafe_allow_html=True)

            if notifs.empty:
                st.info("No notifications yet. High-match opportunities will appear here.")
            else:
                if unread > 0:
                    if st.button("Mark all as read"):
                        mark_notifications_read(user["user_id"])
                        st.cache_data.clear()
                        st.rerun()

                for _, r in notifs.iterrows():
                    border_color = "#D85A30" if r["status"] == "unread" else "#e0e0e0"
                    icon = TYPE_ICONS.get(r["type"], "📋")
                    tc = TYPE_COLORS.get(r["type"], "pill-source")
                    opp_url = r["url"] if r.get("url") else "#"
                    st.markdown(f"""
                    <div class="opp-card" style="border-left: 3px solid {border_color}; border-radius: 0 12px 12px 0;">
                      <div class="opp-header">
                        <div style="flex:1">
                          <div class="opp-title">{icon} {r['title']}</div>
                          <div class="opp-sub">{r['source']} · Deadline: {r['deadline']}</div>
                          <span class="pill {tc}">{r['type'].capitalize()}</span>
                          <span class="pill {'badge-red' if r['status']=='unread' else 'pill-source'}">{r['status'].capitalize()}</span>
                        </div>
                        <a href="{opp_url}" target="_blank" class="open-btn">Open →</a>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

        # ─────────────── PROFILE ───────────────
        elif page == "👤  My Profile":
            st.markdown('<div class="section-title">My Profile</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="pro-card" style="display:flex;gap:20px;align-items:center;margin-bottom:20px">
              <div style="width:60px;height:60px;background:#042C53;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;color:white;flex-shrink:0">{user['name'][:2].upper()}</div>
              <div>
                <h3 style="font-size:18px;margin-bottom:3px">{user['name']}</h3>
                <p style="color:#888;font-size:13px">{user['email']}</p>
                <p style="color:#185FA5;font-size:13px;font-weight:600">{user['degree']} in {user.get('field_of_study','').title()} · {user.get('years_experience',0)} years experience</p>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="pro-card">
                  <h3>Interests</h3>
                  <p style="color:#666;font-size:13px;margin-top:6px">{user.get('interests','—')}</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="pro-card">
                  <h3>Skills</h3>
                  <p style="color:#666;font-size:13px;margin-top:6px">{user.get('skills','—')}</p>
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            st.markdown("**Update your profile**")
            with st.form("update_form"):
                new_interests = st.text_input("Interests", value=user.get("interests",""))
                new_skills = st.text_input("Skills", value=user.get("skills",""))
                new_exp = st.slider("Experience (years)", 0, 20, user.get("years_experience",0))
                if st.form_submit_button("Save & Refresh Recommendations", type="primary"):
                    conn = get_connection()
                    conn.execute("UPDATE Users SET interests=?, skills=?, years_experience=? WHERE user_id=?",
                                 (new_interests, new_skills, new_exp, user["user_id"]))
                    conn.commit()
                    conn.close()
                    st.session_state.user["interests"] = new_interests
                    st.session_state.user["skills"] = new_skills
                    st.session_state.user["years_experience"] = new_exp
                    AgentRecommendation(score_threshold=0.3).recommend_for_user(user["user_id"])
                    st.cache_data.clear()
                    st.success("Profile updated! Recommendations refreshed.")
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# ── ROUTER ─────────────────────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.auth_page == "login":
        show_login()
    else:
        show_register()
else:
    show_app()
