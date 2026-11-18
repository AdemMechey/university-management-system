"""
AUTO SCHEDULER — University Observatory
========================================
Keeps the database automatically updated by running agents on a schedule.

Usage:
    python scheduler.py              → runs forever (auto update)
    python scheduler.py --now        → run once immediately then schedule
    python scheduler.py --interval 2 → update every 2 hours (default: 6)

Run this in a separate terminal while the dashboard is open.
The dashboard will show fresh data automatically.
"""

import schedule
import time
import argparse
import sys, os
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
from database.db_setup import create_tables, get_connection
from agents.agent_observer import AgentObserver
from agents.agent_classifier import AgentClassifier
from agents.agent_cluster import AgentCluster
from agents.agent_recommendation import AgentRecommendation


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def run_update_pipeline():
    """
    Runs the full update pipeline:
    1. Collect new opportunities (deduplication prevents duplicates)
    2. Classify any unclassified ones
    3. Re-cluster everything
    4. Refresh all recommendations
    """
    log("=" * 55)
    log("AUTO-UPDATE: Starting pipeline...")
    log("=" * 55)

    try:
        # Step 1: Collect new data
        log("STEP 1 — AgentObserver: Fetching new opportunities...")
        observer = AgentObserver()
        n_new = observer.collect_all()
        log(f"STEP 1 Done — {n_new} new opportunities added")

        # Step 2: Classify new entries
        log("STEP 2 — AgentClassifier: Classifying...")
        classifier = AgentClassifier()
        n_classified = classifier.classify_all()
        log(f"STEP 2 Done — {n_classified} entries classified")

        # Step 3: Re-cluster
        log("STEP 3 — AgentCluster: Clustering...")
        cluster = AgentCluster(n_clusters=4)
        n_clusters = cluster.cluster_all()
        log(f"STEP 3 Done — {n_clusters} clusters updated")

        # Step 4: Refresh recommendations for all users
        log("STEP 4 — AgentRecommendation: Refreshing recommendations...")
        recommender = AgentRecommendation(score_threshold=0.3)
        n_recs = recommender.recommend_for_all_users()
        log(f"STEP 4 Done — {n_recs} recommendations generated")

        # Summary
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Opportunities")
        total = cursor.fetchone()[0]
        conn.close()

        log("=" * 55)
        log(f"UPDATE COMPLETE")
        log(f"  Total opportunities in DB : {total}")
        log(f"  New this run              : {n_new}")
        log(f"  Recommendations           : {n_recs}")
        log("=" * 55)

    except Exception as e:
        log(f"ERROR during update: {e}")
        import traceback
        traceback.print_exc()


def start_scheduler(interval_hours=6, run_now=False):
    """Start the automatic scheduler."""
    log(f"University Observatory — Auto Scheduler")
    log(f"Update interval: every {interval_hours} hour(s)")
    log(f"Press Ctrl+C to stop\n")

    # Ensure DB and tables exist
    create_tables()

    if run_now:
        log("Running initial update now...")
        run_update_pipeline()

    # Schedule recurring updates
    schedule.every(interval_hours).hours.do(run_update_pipeline)

    next_run = schedule.next_run()
    log(f"Next auto-update scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    log("Scheduler is running. Dashboard will refresh automatically.\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # check every minute
    except KeyboardInterrupt:
        log("Scheduler stopped by user.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="University Observatory Auto-Scheduler")
    parser.add_argument("--now", action="store_true", help="Run update immediately on start")
    parser.add_argument("--interval", type=int, default=6, help="Update interval in hours (default: 6)")
    args = parser.parse_args()

    start_scheduler(interval_hours=args.interval, run_now=args.now)
