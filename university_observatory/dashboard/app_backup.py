"""
DASHBOARD v2 — University Observatory
Features: Login, Register, Smart Recommendations, Full Profile
Run: python -m streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection, register_user, login_user
from agents.agent_recommendation import AgentRecommendation

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="University Observatory",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

# ─────────────────────────────────────────────
# HELPER: load data
# ─────────────────────────────────────────────
def load_opportunities():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Opportunities", conn)
    conn.close()
    return df

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

def load_clusters():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM OpportunityClusters", conn)
    conn.close()
    return df

def mark_notifications_read(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Notifications SET status='read' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# AUTH PAGES
# ─────────────────────────────────────────────
def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center'>🎓 University Observatory</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:gray'>Multi-Agent Opportunity Intelligence System</p>", unsafe_allow_html=True)
        st.divider()
        st.subheader("🔐 Login")

        email = st.text_input("Email address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", use_container_width=True, type="primary"):
            if email and password:
                user = login_user(email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    # Generate fresh recommendations on login
                    rec_agent = AgentRecommendation(score_threshold=0.3)
                    rec_agent.recommend_for_user(user["user_id"])
                    st.success(f"Welcome back, {user['name']}! 🎉")
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password.")
            else:
                st.warning("Please fill in all fields.")

        st.divider()
        st.markdown("<p style='text-align:center'>Don't have an account?</p>", unsafe_allow_html=True)
        if st.button("Create Account →", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()


def show_register_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center'>🎓 Create Your Account</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:gray'>Fill in your profile for smart recommendations</p>", unsafe_allow_html=True)
        st.divider()

        # ── Personal Info ──
        st.subheader("👤 Personal Information")
        name = st.text_input("Full Name *")
        email = st.text_input("Email Address *")
        password = st.text_input("Password *", type="password")
        password2 = st.text_input("Confirm Password *", type="password")

        st.divider()

        # ── Academic Profile ──
        st.subheader("🎓 Academic Profile")
        degree = st.selectbox("Degree Level *", [
            "Bachelor", "Master", "PhD", "Postdoc", "Researcher"
        ])
        field_of_study = st.selectbox("Field of Study *", [
            "Computer Science", "Data Science", "Artificial Intelligence",
            "Software Engineering", "Mathematics", "Biomedical",
            "Electronics", "Business", "Other"
        ])
        years_experience = st.slider("Years of Experience", 0, 20, 0)

        st.divider()

        # ── Interests & Skills ──
        st.subheader("💡 Interests & Skills")
        st.caption("Separate multiple values with commas")

        interests = st.text_input(
            "Your Interests *",
            placeholder="e.g. machine learning, nlp, computer vision"
        )
        skills = st.text_input(
            "Your Skills *",
            placeholder="e.g. python, tensorflow, sql, pytorch"
        )

        st.divider()

        if st.button("🚀 Create Account", use_container_width=True, type="primary"):
            # Validation
            if not all([name, email, password, password2, interests, skills]):
                st.error("Please fill in all required fields.")
            elif password != password2:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                success, msg = register_user(
                    name=name,
                    email=email,
                    password=password,
                    degree=degree,
                    field_of_study=field_of_study.lower(),
                    years_experience=years_experience,
                    interests=interests,
                    skills=skills
                )
                if success:
                    st.success("✅ Account created! Please login.")
                    st.session_state.auth_page = "login"
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        if st.button("← Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


# ─────────────────────────────────────────────
# MAIN APP (after login)
# ─────────────────────────────────────────────
def show_main_app():
    user = st.session_state.user

    # ── Sidebar ──
    st.sidebar.image("https://img.icons8.com/color/96/university.png", width=70)
    st.sidebar.title("🎓 Observatory")
    st.sidebar.markdown(f"**{user['name']}**")
    st.sidebar.caption(f"{user['degree']} · {user['field_of_study']}")
    st.sidebar.divider()

    notifs = load_my_notifications(user["user_id"])
    unread = len(notifs[notifs["status"] == "unread"]) if not notifs.empty else 0
    notif_label = f"🔔 Notifications ({unread} new)" if unread > 0 else "🔔 Notifications"

    page = st.sidebar.radio("Navigate", [
        "📊 Dashboard",
        "💡 My Recommendations",
        notif_label,
        "🔍 Browse All",
        "🤖 MAS Agents",
        "🌐 Data Sources",
        "👤 My Profile",
    ])

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    # ────────────────────────────────────────
    # PAGE: DASHBOARD
    # ────────────────────────────────────────
    if page == "📊 Dashboard":
        st.title(f"Welcome back, {user['name']}! 👋")
        st.markdown(f"*{user['degree']} in {user['field_of_study']} · {user['years_experience']} years experience*")
        st.divider()

        opps = load_opportunities()
        recs = load_my_recommendations(user["user_id"])
        clusters = load_clusters()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📋 Total Opportunities", len(opps))
        col2.metric("💡 Your Recommendations", len(recs))
        col3.metric("🗂️ Clusters", len(clusters))
        col4.metric("🔔 Unread Alerts", unread)

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("📂 Opportunities by Type")
            if not opps.empty:
                st.bar_chart(opps["type"].value_counts())

        with col_b:
            st.subheader("💡 Your Top Recommendations")
            if not recs.empty:
                top5 = recs.head(5)[["title", "type", "score"]]
                st.dataframe(top5, use_container_width=True)
            else:
                st.info("No recommendations yet.")

        st.divider()
        st.subheader("⏰ Upcoming Deadlines")
        if not opps.empty:
            opps["deadline"] = pd.to_datetime(opps["deadline"], errors="coerce")
            today = pd.Timestamp.now()
            soon = opps[opps["deadline"] > today].sort_values("deadline").head(6)
            st.dataframe(soon[["title", "type", "source", "deadline"]], use_container_width=True)

    # ────────────────────────────────────────
    # PAGE: MY RECOMMENDATIONS
    # ────────────────────────────────────────
    elif page == "💡 My Recommendations":
        st.title("💡 Your Personalized Recommendations")
        st.markdown("*Scored based on your degree, field of study, experience, skills & interests*")

        recs = load_my_recommendations(user["user_id"])

        if recs.empty:
            st.info("No recommendations yet. The system will generate them on your next login.")
        else:
            # Filter by type
            types = ["All"] + recs["type"].unique().tolist()
            selected_type = st.selectbox("Filter by type", types)
            filtered = recs if selected_type == "All" else recs[recs["type"] == selected_type]

            st.markdown(f"**{len(filtered)} recommendations found**")

            for _, row in filtered.iterrows():
                score_pct = int(row["score"] * 100)
                color = "🟢" if score_pct >= 60 else "🟡" if score_pct >= 40 else "🟠"

                with st.expander(f"{color} **{row['title']}** — Match: {score_pct}%"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {row['type'].capitalize()}")
                        st.write(f"**Source:** {row['source']}")
                        st.write(f"**Location:** {row['location']}")
                        st.write(f"**Eligibility:** {row['eligibility']}")
                        st.write(f"**Deadline:** {row['deadline']}")
                    with col2:
                        # Show score breakdown
                        if row["score_breakdown"]:
                            try:
                                breakdown = json.loads(row["score_breakdown"])
                                st.markdown("**Score Breakdown:**")
                                for factor, val in breakdown.items():
                                    bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
                                    st.caption(f"{factor.capitalize():<12} {bar} {int(val*100)}%")
                            except:
                                pass
                    st.write(f"**Description:** {row['description'][:200] if row['description'] else 'N/A'}...")
                    st.markdown(f"[🔗 View Opportunity]({row['url']})")

    # ────────────────────────────────────────
    # PAGE: NOTIFICATIONS
    # ────────────────────────────────────────
    elif "Notifications" in page:
        st.title("🔔 Notifications")
        notifs = load_my_notifications(user["user_id"])

        if notifs.empty:
            st.info("No notifications yet.")
        else:
            unread_notifs = notifs[notifs["status"] == "unread"]
            if not unread_notifs.empty:
                st.warning(f"You have **{len(unread_notifs)} new** high-match opportunities!")
                if st.button("Mark all as read"):
                    mark_notifications_read(user["user_id"])
                    st.rerun()

            for _, row in notifs.iterrows():
                icon = "🔴" if row["status"] == "unread" else "⚪"
                with st.expander(f"{icon} **{row['title']}** — {row['source']}"):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.write(f"**Type:** {row['type'].capitalize()}")
                        st.write(f"**Source:** {row['source']}")
                        st.write(f"**Deadline:** {row['deadline']}")
                        st.write(f"**Status:** {row['status'].capitalize()}")
                    with col2:
                        opp_url = row['url'] if 'url' in row and row['url'] else "#"
                        st.markdown(f"### [🔗 Open Opportunity]({opp_url})")
                        st.caption("Click to open in browser")

    # ────────────────────────────────────────
    # PAGE: BROWSE ALL
    # ────────────────────────────────────────
    elif page == "🔍 Browse All":
        st.title("🔍 Browse All Opportunities")
        opps = load_opportunities()

        col1, col2, col3 = st.columns(3)
        with col1:
            type_filter = st.selectbox("Filter by Type", ["All"] + sorted(opps["type"].unique().tolist()))
        with col2:
            search = st.text_input("🔎 Search keyword")
        with col3:
            sort_by = st.selectbox("Sort by", ["Deadline (soonest)", "Title A-Z", "Source"])

        filtered = opps.copy()
        if type_filter != "All":
            filtered = filtered[filtered["type"] == type_filter]
        if search:
            mask = (
                filtered["title"].str.contains(search, case=False, na=False) |
                filtered["description"].str.contains(search, case=False, na=False) |
                filtered["source"].str.contains(search, case=False, na=False)
            )
            filtered = filtered[mask]

        if sort_by == "Deadline (soonest)":
            filtered["deadline"] = pd.to_datetime(filtered["deadline"], errors="coerce")
            filtered = filtered.sort_values("deadline")
        elif sort_by == "Title A-Z":
            filtered = filtered.sort_values("title")
        elif sort_by == "Source":
            filtered = filtered.sort_values("source")

        st.markdown(f"**{len(filtered)} opportunities found**")
        st.divider()

        TYPE_ICONS = {"internship": "💼", "scholarship": "🎓", "certification": "📜", "project": "🔬"}

        for _, row in filtered.iterrows():
            icon = TYPE_ICONS.get(row["type"], "📋")
            with st.expander(f"{icon} **{row['title']}** — {row['source']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**📍 Location:** {row['location']}")
                    st.write(f"**🎯 Eligibility:** {row['eligibility']}")
                    st.write(f"**🏢 Source:** {row['source']}")
                    desc = row['description'] or ""
                    if "] " in desc:
                        desc = desc.split("] ")[-1]
                    st.write(f"**📝 Description:** {desc[:250]}...")
                with col2:
                    deadline = str(row["deadline"]) if row["deadline"] else "N/A"
                    st.metric("⏰ Deadline", deadline)
                    st.markdown(f"### [🔗 Open Opportunity]({row['url']})")
                    st.caption("Click the link above to open in your browser")

    # ────────────────────────────────────────
    # PAGE: MAS AGENTS
    # ────────────────────────────────────────
    elif page == "🤖 MAS Agents":
        st.title("🤖 Multi-Agent System Architecture")

        agents_data = [
            {"Agent": "AgentObserver",       "Role": "Data Collection",     "Status": "✅ Active", "Description": "Collects internships, scholarships, certifications, and projects"},
            {"Agent": "AgentClassifier",     "Role": "NLP Classification",  "Status": "✅ Active", "Description": "Tags opportunities by domain (NLP, CV, ML...) and academic level"},
            {"Agent": "AgentCluster",        "Role": "Clustering (KMeans)", "Status": "✅ Active", "Description": "Groups similar opportunities using TF-IDF + KMeans algorithm"},
            {"Agent": "AgentRecommendation", "Role": "Smart Matching",      "Status": "✅ Active", "Description": "Scores using degree (25%), field (25%), skills (20%), interests (20%), experience (10%)"},
            {"Agent": "AgentCoordinator",    "Role": "Orchestration",       "Status": "✅ Active", "Description": "Runs all agents in correct order and logs results"},
        ]
        st.dataframe(pd.DataFrame(agents_data), use_container_width=True)

        st.divider()
        st.subheader("📊 Scoring Weights (AgentRecommendation)")
        weights = {"Degree Level": 25, "Field of Study": 25, "Skills Match": 20, "Interests Match": 20, "Experience": 10}
        st.bar_chart(weights)

        st.divider()
        st.subheader("🗂️ Opportunity Clusters")
        clusters = load_clusters()
        if not clusters.empty:
            for _, row in clusters.iterrows():
                members = row["members"].split(",") if row["members"] else []
                st.info(f"**Cluster {row['cluster_id']}: {row['cluster_name']}** — {len(members)} opportunities")

    # ────────────────────────────────────────
    # PAGE: DATA SOURCES
    # ────────────────────────────────────────
    elif page == "🌐 Data Sources":
        st.title("🌐 Live Data Sources")
        st.markdown("The system collects real opportunities from these sources automatically.")

        sources = [
            {"Source": "arXiv API",       "Type": "API",      "Data": "Research papers & projects (cs.AI, cs.LG, cs.CL)", "Update": "Every 6h", "URL": "https://export.arxiv.org"},
            {"Source": "OpenAlex API",    "Type": "API",      "Data": "Academic works & affiliated institutions",          "Update": "Every 6h", "URL": "https://api.openalex.org"},
            {"Source": "RemoteOK API",    "Type": "API",      "Data": "Remote ML/AI internships & jobs",                  "Update": "Every 6h", "URL": "https://remoteok.com/api"},
            {"Source": "HackerNews API",  "Type": "API",      "Data": "Tech job postings from HN community",              "Update": "Every 6h", "URL": "https://hacker-news.firebaseio.com"},
            {"Source": "Scholars4Dev",    "Type": "Scraping", "Data": "International scholarships & fellowships",         "Update": "Every 6h", "URL": "https://www.scholars4dev.com"},
            {"Source": "AIJobs.net",      "Type": "Scraping", "Data": "AI/ML specific internship listings",               "Update": "Every 6h", "URL": "https://aijobs.net"},
            {"Source": "Static Curated",  "Type": "Built-in", "Data": "Curated high-quality opportunities (fallback)",    "Update": "Always",   "URL": "—"},
        ]
        st.dataframe(pd.DataFrame(sources), use_container_width=True)

        st.divider()
        st.subheader("📊 Database Stats")
        conn = get_connection()
        opps_by_type = pd.read_sql_query("SELECT type, COUNT(*) as count FROM Opportunities GROUP BY type", conn)
        opps_by_source = pd.read_sql_query("SELECT source, COUNT(*) as count FROM Opportunities GROUP BY source ORDER BY count DESC LIMIT 10", conn)
        conn.close()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**By Type**")
            st.bar_chart(opps_by_type.set_index("type")["count"])
        with col2:
            st.markdown("**Top Sources**")
            st.dataframe(opps_by_source, use_container_width=True)

        st.divider()
        st.subheader("🔄 Manual Data Refresh")
        st.info("You can also refresh the database manually without running the scheduler.")
        if st.button("🚀 Run Data Collection Now", type="primary"):
            with st.spinner("Collecting data from all sources..."):
                try:
                    from agents.agent_observer import AgentObserver
                    from agents.agent_classifier import AgentClassifier
                    from agents.agent_cluster import AgentCluster

                    obs = AgentObserver()
                    n_new = obs.collect_all()

                    clf = AgentClassifier()
                    clf.classify_all()

                    clu = AgentCluster(n_clusters=4)
                    clu.cluster_all()

                    rec = AgentRecommendation(score_threshold=0.3)
                    rec.recommend_for_user(user["user_id"])

                    st.success(f"✅ Done! Added {n_new} new opportunities. Recommendations refreshed.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ────────────────────────────────────────
    # PAGE: MY PROFILE
    # ────────────────────────────────────────
    elif page == "👤 My Profile":
        st.title("👤 My Profile")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Personal Info")
            st.write(f"**Name:** {user['name']}")
            st.write(f"**Email:** {user['email']}")
        with col2:
            st.subheader("Academic Profile")
            st.write(f"**Degree:** {user['degree']}")
            st.write(f"**Field:** {user['field_of_study']}")
            st.write(f"**Experience:** {user['years_experience']} years")

        st.divider()
        st.subheader("Interests & Skills")
        st.write(f"**Interests:** {user['interests']}")
        st.write(f"**Skills:** {user['skills']}")

        st.divider()
        st.subheader("🔄 Update Profile")
        with st.expander("Click to update your skills and interests"):
            new_interests = st.text_input("New Interests", value=user["interests"] or "")
            new_skills = st.text_input("New Skills", value=user["skills"] or "")
            new_exp = st.slider("Years of Experience", 0, 20, user["years_experience"] or 0)

            if st.button("Save Changes", type="primary"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE Users SET interests=?, skills=?, years_experience=?
                    WHERE user_id=?
                """, (new_interests, new_skills, new_exp, user["user_id"]))
                conn.commit()
                conn.close()

                # Update session
                st.session_state.user["interests"] = new_interests
                st.session_state.user["skills"] = new_skills
                st.session_state.user["years_experience"] = new_exp

                # Regenerate recommendations
                rec_agent = AgentRecommendation(score_threshold=0.3)
                rec_agent.recommend_for_user(user["user_id"])
                st.success("✅ Profile updated and recommendations refreshed!")
                st.rerun()


# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.auth_page == "login":
        show_login_page()
    else:
        show_register_page()
else:
    show_main_app()
