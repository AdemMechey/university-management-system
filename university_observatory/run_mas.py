"""
AGENT 5: AgentCoordinator
Role: Orchestrates the entire Multi-Agent System (MAS).
Calls each agent in the correct order and logs the process.
This is the entry point for running the full system.
"""

import sys, os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.db_setup import create_tables, get_connection, register_user
from agents.agent_observer import AgentObserver
from agents.agent_classifier import AgentClassifier
from agents.agent_cluster import AgentCluster
from agents.agent_recommendation import AgentRecommendation


def seed_sample_users():
    """Adds 3 sample users to the database for demo purposes."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Users")
    count = cursor.fetchone()[0]
    if count > 0:
        print("[Coordinator] Users already exist. Skipping seed.")
        conn.close()
        return
    conn.close()

    users = [
        ("Alice Ben Salah",   "alice@univ.tn",   "password123", "Master",    "artificial intelligence", 1, "machine learning, nlp, deep learning", "python, tensorflow, scikit-learn"),
        ("Mohamed Trabelsi",  "mohamed@univ.tn", "password123", "PhD",       "computer science",        3, "computer vision, research, healthcare ai", "python, pytorch, opencv"),
        ("Sara Chaabane",     "sara@univ.tn",    "password123", "Bachelor",  "data science",            0, "data science, cloud, certifications", "python, sql, aws"),
    ]

    for u in users:
        register_user(*u)

    print(f"[Coordinator] Added {len(users)} demo users.")
    print("[Coordinator] Demo credentials: alice@univ.tn / password123")


class AgentCoordinator:
    """
    Coordinator Agent — the master orchestrator.
    Initializes all agents and runs them in sequence.
    """

    def __init__(self):
        self.name = "AgentCoordinator"

    def run(self):
        """Runs the full MAS pipeline."""
        print("=" * 60)
        print("  UNIVERSITY OBSERVATORY — MULTI-AGENT SYSTEM")
        print("=" * 60)

        # STEP 1: Setup database
        print("\n[STEP 1] Setting up database...")
        create_tables()

        # STEP 2: Seed users
        print("\n[STEP 2] Loading users...")
        seed_sample_users()

        # STEP 3: Observer Agent — collect data
        print("\n[STEP 3] Running AgentObserver...")
        observer = AgentObserver()
        n_collected = observer.collect_all()

        # STEP 4: Classifier Agent — tag opportunities
        print("\n[STEP 4] Running AgentClassifier...")
        classifier = AgentClassifier()
        n_classified = classifier.classify_all()

        # STEP 5: Cluster Agent — group opportunities
        print("\n[STEP 5] Running AgentCluster...")
        cluster = AgentCluster(n_clusters=4)
        n_clusters = cluster.cluster_all()

        # STEP 6: Recommendation Agent — match users
        print("\n[STEP 6] Running AgentRecommendation...")
        recommender = AgentRecommendation(score_threshold=0.2)
        n_recs = recommender.recommend_for_all_users()

        # SUMMARY
        print("=" * 60)
        print("  SYSTEM RUN COMPLETE — SUMMARY")
        print("=" * 60)
        print(f"  Opportunities Collected : {n_collected}")
        print(f"  Opportunities Classified: {n_classified}")
        print(f"  Clusters Created        : {n_clusters}")
        print(f"  Recommendations Made    : {n_recs}")
        print("=" * 60)
        print("  Run the dashboard: streamlit run dashboard/app.py")
        print("=" * 60)


if __name__ == "__main__":
    coordinator = AgentCoordinator()
    coordinator.run()
