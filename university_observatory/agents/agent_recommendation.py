"""
AGENT 4: AgentRecommendation (v2 — Intelligent)
Role: Smart matching using degree, field, experience, skills, and interests.
Each factor contributes a weighted score for precise personalization.
"""

import sqlite3
import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

# ─────────────────────────────────────────────
# SCORING WEIGHTS (must sum to 1.0)
# ─────────────────────────────────────────────
WEIGHTS = {
    "degree":      0.25,   # Does the degree match eligibility?
    "field":       0.25,   # Does field of study match opportunity domain?
    "skills":      0.20,   # Do skills appear in the opportunity text?
    "interests":   0.20,   # Do interests match opportunity content?
    "experience":  0.10,   # Does experience level fit the opportunity level?
}

# Degree hierarchy: higher index = higher level
DEGREE_LEVELS = {
    "Bachelor": 1,
    "Master": 2,
    "PhD": 3,
    "Postdoc": 4,
    "Researcher": 4,
}

# Eligibility keywords mapped to minimum degree level required
ELIGIBILITY_DEGREE_MAP = {
    "bachelor": 1, "undergraduate": 1, "all levels": 1, "beginner": 1,
    "master": 2, "graduate": 2, "intermediate": 2,
    "phd": 3, "doctoral": 3, "advanced": 3,
    "postdoc": 4, "researcher": 4,
}

# Field of study → related keywords in opportunities
FIELD_KEYWORDS = {
    "computer science":    ["ai", "machine learning", "algorithm", "software", "computing", "nlp", "vision"],
    "data science":        ["data", "analytics", "statistics", "visualization", "pandas", "sql", "dashboard"],
    "artificial intelligence": ["ai", "neural", "deep learning", "nlp", "vision", "model", "transformer"],
    "software engineering":["software", "development", "engineering", "system", "cloud", "devops"],
    "mathematics":         ["statistics", "optimization", "algorithm", "numerical", "mathematical"],
    "biomedical":          ["health", "medical", "clinical", "biology", "biomedical", "patient"],
    "electronics":         ["iot", "embedded", "sensor", "hardware", "circuit", "signal"],
    "business":            ["management", "strategy", "business", "finance", "entrepreneurship"],
}

# Experience level brackets
def experience_to_level(years):
    if years == 0:
        return "beginner"
    elif years <= 2:
        return "intermediate"
    else:
        return "advanced"


def score_degree(user_degree, eligibility_text):
    """Score based on whether user's degree matches eligibility."""
    eligibility_lower = (eligibility_text or "").lower()
    user_level = DEGREE_LEVELS.get(user_degree, 1)

    required_level = 1  # default: open to all
    for keyword, level in ELIGIBILITY_DEGREE_MAP.items():
        if keyword in eligibility_lower:
            required_level = max(required_level, level)

    if user_level >= required_level:
        # Perfect match if exact level, slightly less if overqualified
        if user_level == required_level:
            return 1.0
        else:
            return 0.7  # overqualified but still eligible
    else:
        return 0.0  # not eligible


def score_field(user_field, opp_title, opp_description):
    """Score based on how well user's field of study matches the opportunity."""
    if not user_field:
        return 0.5  # neutral if no field set
    opp_text = f"{opp_title} {opp_description}".lower()
    user_field_lower = user_field.lower()

    # Direct field mention
    if user_field_lower in opp_text:
        return 1.0

    # Keyword-based match
    related_keywords = FIELD_KEYWORDS.get(user_field_lower, [])
    matches = sum(1 for kw in related_keywords if kw in opp_text)
    if not related_keywords:
        return 0.3
    return min(matches / len(related_keywords) * 1.5, 1.0)


def score_skills(user_skills, opp_text):
    """Score based on skill keyword overlap."""
    if not user_skills:
        return 0.0
    skills = [s.strip().lower() for s in user_skills.split(",") if s.strip()]
    if not skills:
        return 0.0
    matches = sum(1 for skill in skills if skill in opp_text.lower())
    return min(matches / len(skills) * 2, 1.0)


def score_interests(user_interests, opp_text):
    """Score based on interest keyword overlap."""
    if not user_interests:
        return 0.0
    interests = [i.strip().lower() for i in user_interests.split(",") if i.strip()]
    if not interests:
        return 0.0
    matches = sum(1 for interest in interests if interest in opp_text.lower())
    return min(matches / len(interests) * 2, 1.0)


def score_experience(years_experience, opp_title, opp_description, opp_type):
    """Score based on experience level fit."""
    opp_text = f"{opp_title} {opp_description} {opp_type}".lower()
    user_level = experience_to_level(years_experience)

    # Certifications and internships favor less experience
    if opp_type in ["certification", "internship"]:
        if user_level == "beginner":
            return 1.0
        elif user_level == "intermediate":
            return 0.8
        else:
            return 0.5

    # Research projects and scholarships favor more experience
    if opp_type in ["project", "scholarship"]:
        if user_level == "advanced":
            return 1.0
        elif user_level == "intermediate":
            return 0.7
        else:
            return 0.4

    return 0.5  # neutral


def compute_smart_score(user, opportunity):
    """
    Computes a weighted multi-factor relevance score.
    Returns (total_score, breakdown_dict)
    """
    opp_id, opp_type, opp_title, opp_desc, opp_eligibility = opportunity
    opp_text = f"{opp_title} {opp_desc or ''}"

    breakdown = {
        "degree":     score_degree(user["degree"], opp_eligibility),
        "field":      score_field(user["field_of_study"], opp_title, opp_desc or ""),
        "skills":     score_skills(user["skills"], opp_text),
        "interests":  score_interests(user["interests"], opp_text),
        "experience": score_experience(user["years_experience"], opp_title, opp_desc or "", opp_type),
    }

    total = sum(WEIGHTS[k] * v for k, v in breakdown.items())
    return round(total, 3), breakdown


class AgentRecommendation:
    """
    Intelligent Recommendation Agent v2.
    Uses weighted multi-factor scoring:
    degree (25%) + field (25%) + skills (20%) + interests (20%) + experience (10%)
    """

    def __init__(self, score_threshold=0.3):
        self.name = "AgentRecommendation"
        self.score_threshold = score_threshold

    def recommend_for_all_users(self):
        print(f"\n[{self.name}] Generating intelligent recommendations...")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, name, degree, field_of_study,
                   years_experience, interests, skills
            FROM Users
        """)
        users_raw = cursor.fetchall()

        if not users_raw:
            print(f"[{self.name}] No users found.")
            conn.close()
            return 0

        users = [
            {
                "user_id": r[0], "name": r[1], "degree": r[2],
                "field_of_study": r[3], "years_experience": r[4] or 0,
                "interests": r[5], "skills": r[6]
            }
            for r in users_raw
        ]

        cursor.execute("SELECT id, type, title, description, eligibility FROM Opportunities")
        opportunities = cursor.fetchall()

        cursor.execute("DELETE FROM Recommendations")
        cursor.execute("DELETE FROM Notifications")

        total_recs = 0

        for user in users:
            print(f"\n  → User: {user['name']} | {user['degree']} in {user['field_of_study']} | {user['years_experience']} yrs exp")
            scored = []

            for opp in opportunities:
                score, breakdown = compute_smart_score(user, opp)
                if score >= self.score_threshold:
                    scored.append((opp[0], score, breakdown))

            # Sort by score, keep top 8
            scored.sort(key=lambda x: x[1], reverse=True)
            top = scored[:8]

            for opp_id, score, breakdown in top:
                breakdown_json = json.dumps(breakdown)
                cursor.execute("""
                    INSERT INTO Recommendations (user_id, opportunity_id, score, score_breakdown)
                    VALUES (?, ?, ?, ?)
                """, (user["user_id"], opp_id, score, breakdown_json))

                if score >= 0.55:
                    cursor.execute("""
                        INSERT INTO Notifications (user_id, opportunity_id, status)
                        VALUES (?, ?, 'unread')
                    """, (user["user_id"], opp_id))

                print(f"       → Opp {opp_id}: score={score} | degree={breakdown['degree']:.2f} field={breakdown['field']:.2f} skills={breakdown['skills']:.2f}")
                total_recs += 1

        conn.commit()
        conn.close()
        print(f"\n[{self.name}] Done! {total_recs} recommendations generated.\n")
        return total_recs

    def recommend_for_user(self, user_id):
        """Generate recommendations for a single user (called after login)."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, name, degree, field_of_study,
                   years_experience, interests, skills
            FROM Users WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return 0

        user = {
            "user_id": row[0], "name": row[1], "degree": row[2],
            "field_of_study": row[3], "years_experience": row[4] or 0,
            "interests": row[5], "skills": row[6]
        }

        cursor.execute("SELECT id, type, title, description, eligibility FROM Opportunities")
        opportunities = cursor.fetchall()

        cursor.execute("DELETE FROM Recommendations WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM Notifications WHERE user_id = ?", (user_id,))

        scored = []
        for opp in opportunities:
            score, breakdown = compute_smart_score(user, opp)
            if score >= self.score_threshold:
                scored.append((opp[0], score, breakdown))

        scored.sort(key=lambda x: x[1], reverse=True)

        for opp_id, score, breakdown in scored[:8]:
            cursor.execute("""
                INSERT INTO Recommendations (user_id, opportunity_id, score, score_breakdown)
                VALUES (?, ?, ?, ?)
            """, (user["user_id"], opp_id, score, json.dumps(breakdown)))

            if score >= 0.55:
                cursor.execute("""
                    INSERT INTO Notifications (user_id, opportunity_id, status)
                    VALUES (?, ?, 'unread')
                """, (user["user_id"], opp_id))

        conn.commit()
        conn.close()
        return len(scored[:8])
