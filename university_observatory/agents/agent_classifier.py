"""
AGENT 2: AgentClassifier
Role: Classify and tag opportunities using NLP keyword extraction.
Assigns domain tags (AI, NLP, Data Science, etc.) to each opportunity.
"""

import sqlite3
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

# ─────────────────────────────────────────────
# KEYWORD-BASED CLASSIFICATION RULES
# Each domain has a list of keywords. If an opportunity's title or
# description contains any keyword, it gets that domain tag.
# ─────────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "NLP": ["nlp", "natural language", "text", "transformer", "language model", "bert", "gpt", "hugging face"],
    "Computer Vision": ["vision", "image", "video", "object detection", "cnn", "segmentation", "autonomous"],
    "Machine Learning": ["machine learning", "ml", "neural network", "deep learning", "tensorflow", "pytorch", "scikit"],
    "Data Science": ["data science", "data analysis", "pandas", "statistics", "visualization", "dashboard", "sql"],
    "Cloud & MLOps": ["aws", "azure", "cloud", "mlops", "deployment", "docker", "kubernetes"],
    "AI Ethics": ["ethics", "fairness", "explainable", "bias", "responsible", "transparency"],
    "Research": ["research", "phd", "postdoc", "fellowship", "grant", "publication", "lab"],
    "IoT": ["iot", "internet of things", "sensor", "embedded", "smart city"],
    "Healthcare AI": ["health", "medical", "clinical", "diagnosis", "patient", "biomedical"],
}

LEVEL_KEYWORDS = {
    "Beginner": ["beginner", "bachelor", "undergraduate", "all levels", "introductory"],
    "Intermediate": ["intermediate", "master", "graduate"],
    "Advanced": ["phd", "doctoral", "postdoc", "researcher", "advanced"],
}


def classify_opportunity(title, description, eligibility):
    """
    Classifies a single opportunity and returns domain + level tags.
    """
    combined_text = f"{title} {description} {eligibility}".lower()

    # Domain classification
    matched_domains = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in combined_text:
                matched_domains.append(domain)
                break  # one match per domain is enough

    if not matched_domains:
        matched_domains = ["General AI"]

    # Level classification
    matched_level = "All Levels"
    for level, keywords in LEVEL_KEYWORDS.items():
        for kw in keywords:
            if kw in combined_text:
                matched_level = level
                break

    return ", ".join(matched_domains), matched_level


class AgentClassifier:
    """
    Classifier Agent — reads opportunities from DB and adds domain/level tags.
    Updates the description field with classification metadata.
    """

    def __init__(self):
        self.name = "AgentClassifier"
        self.classified_count = 0

    def classify_all(self):
        """Reads all opportunities and classifies each one."""
        print(f"\n[{self.name}] Starting classification...")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, title, description, eligibility FROM Opportunities")
        opportunities = cursor.fetchall()

        for opp_id, title, description, eligibility in opportunities:
            domains, level = classify_opportunity(title, description or "", eligibility or "")

            # Store classification back into the description as a tag prefix
            tagged_description = f"[Domains: {domains}] [Level: {level}] {description}"

            cursor.execute("""
                UPDATE Opportunities SET description = ? WHERE id = ?
            """, (tagged_description, opp_id))

            print(f"  → ID {opp_id}: {title[:40]}")
            print(f"       Domains: {domains} | Level: {level}")
            self.classified_count += 1

        conn.commit()
        conn.close()
        print(f"[{self.name}] Done! Classified {self.classified_count} opportunities.\n")
        return self.classified_count


if __name__ == "__main__":
    agent = AgentClassifier()
    agent.classify_all()
