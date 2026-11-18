"""
DATABASE SETUP - University Observatory (v2)
Upgraded with authentication and rich user profiles
"""

import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "observatory.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # --- TABLE 1: Opportunities ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            source TEXT,
            location TEXT,
            eligibility TEXT,
            deadline TEXT,
            url TEXT,
            cluster_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- TABLE 2: Users (upgraded with full profile + auth) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            degree TEXT,
            field_of_study TEXT,
            years_experience INTEGER DEFAULT 0,
            interests TEXT,
            skills TEXT,
            profile TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- TABLE 3: OpportunityClusters ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS OpportunityClusters (
            cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_name TEXT NOT NULL,
            members TEXT
        )
    """)

    # --- TABLE 4: Recommendations ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Recommendations (
            recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            opportunity_id INTEGER,
            score REAL,
            score_breakdown TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (opportunity_id) REFERENCES Opportunities(id)
        )
    """)

    # --- TABLE 5: Notifications ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            opportunity_id INTEGER,
            status TEXT DEFAULT 'unread',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (opportunity_id) REFERENCES Opportunities(id)
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] All tables created successfully.")

# ── Auth Functions ──────────────────────────────────────

def register_user(name, email, password, degree, field_of_study,
                  years_experience, interests, skills):
    """Register a new user. Returns (True, msg) or (False, error)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Users (name, email, password_hash, degree, field_of_study,
                               years_experience, interests, skills, profile)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, email, hash_password(password),
            degree, field_of_study, years_experience,
            interests, skills,
            f"{degree} in {field_of_study}"
        ))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    finally:
        conn.close()

def login_user(email, password):
    """Check credentials. Returns user dict or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, name, email, degree, field_of_study,
               years_experience, interests, skills, profile
        FROM Users WHERE email = ? AND password_hash = ?
    """, (email, hash_password(password)))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0], "name": row[1], "email": row[2],
            "degree": row[3], "field_of_study": row[4],
            "years_experience": row[5], "interests": row[6],
            "skills": row[7], "profile": row[8]
        }
    return None

if __name__ == "__main__":
    create_tables()
