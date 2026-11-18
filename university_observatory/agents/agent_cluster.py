"""
AGENT 3: AgentCluster
Role: Group similar opportunities into clusters using KMeans.
Uses TF-IDF text vectorization on titles and descriptions.
"""

import sqlite3
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[Warning] scikit-learn not installed. Using fallback rule-based clustering.")


# Fallback cluster names based on opportunity type
FALLBACK_CLUSTERS = {
    "internship": "Industry Internships",
    "scholarship": "Funding & Scholarships",
    "certification": "Online Learning & Certifications",
    "project": "Research Projects",
}


class AgentCluster:
    """
    Cluster Agent — groups opportunities into meaningful clusters.
    Uses KMeans + TF-IDF if scikit-learn is available,
    otherwise uses rule-based type clustering.
    """

    def __init__(self, n_clusters=4):
        self.name = "AgentCluster"
        self.n_clusters = n_clusters

    def cluster_all(self):
        """Clusters all opportunities and saves results to DB."""
        print(f"\n[{self.name}] Starting clustering...")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, type, title, description FROM Opportunities")
        rows = cursor.fetchall()

        if not rows:
            print(f"[{self.name}] No opportunities found in DB.")
            conn.close()
            return

        ids = [r[0] for r in rows]
        types = [r[1] for r in rows]
        texts = [f"{r[2]} {r[3] or ''}" for r in rows]

        # Clear old clusters
        cursor.execute("DELETE FROM OpportunityClusters")

        if SKLEARN_AVAILABLE and len(rows) >= self.n_clusters:
            labels = self._kmeans_cluster(texts)
            cluster_names = self._generate_cluster_names(rows, labels)
        else:
            # Fallback: cluster by type
            labels = [list(FALLBACK_CLUSTERS.keys()).index(t) if t in FALLBACK_CLUSTERS else 0 for t in types]
            cluster_names = {i: name for i, name in enumerate(FALLBACK_CLUSTERS.values())}

        # Save clusters and update opportunities
        for cluster_id, cluster_name in cluster_names.items():
            members = [ids[i] for i, l in enumerate(labels) if l == cluster_id]
            cursor.execute("""
                INSERT INTO OpportunityClusters (cluster_id, cluster_name, members)
                VALUES (?, ?, ?)
            """, (cluster_id + 1, cluster_name, ",".join(map(str, members))))

            # Update each opportunity with its cluster
            for opp_id in members:
                cursor.execute("UPDATE Opportunities SET cluster_id = ? WHERE id = ?",
                               (cluster_id + 1, opp_id))

            print(f"  → Cluster {cluster_id + 1}: '{cluster_name}' — {len(members)} items")

        conn.commit()
        conn.close()
        print(f"[{self.name}] Done! Created {len(cluster_names)} clusters.\n")
        return len(cluster_names)

    def _kmeans_cluster(self, texts):
        """Uses TF-IDF + KMeans to cluster texts."""
        vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
        X = vectorizer.fit_transform(texts)
        km = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        km.fit(X)
        return km.labels_.tolist()

    def _generate_cluster_names(self, rows, labels):
        """Generates descriptive cluster names based on majority type."""
        cluster_types = {}
        for i, label in enumerate(labels):
            t = rows[i][1]
            cluster_types.setdefault(label, []).append(t)

        cluster_names = {}
        type_to_label = {
            "internship": "Industry Internships",
            "scholarship": "Scholarships & Fellowships",
            "certification": "Courses & Certifications",
            "project": "Research Projects",
        }
        for label, type_list in cluster_types.items():
            majority = max(set(type_list), key=type_list.count)
            cluster_names[label] = type_to_label.get(majority, f"Mixed Cluster {label + 1}")

        return cluster_names


if __name__ == "__main__":
    agent = AgentCluster()
    agent.cluster_all()
