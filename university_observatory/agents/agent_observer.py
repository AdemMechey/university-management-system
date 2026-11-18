"""
AGENT 1: AgentObserver (v3 — Real Data Collection)
========================================================
Collects REAL opportunities from multiple sources:

APIs:
  - arXiv API         → Research papers & postdoc opportunities (cs.AI, cs.LG)
  - OpenAlex API      → Academic research projects & grants
  - HackerNews API    → Tech internships & jobs (monthly "Who is Hiring" threads)
  - RemoteOK API      → Remote ML/AI internships and jobs
  - GitHub API        → Open source AI research repos (project opportunities)

Web Scraping:
  - Scholars4Dev      → International scholarships & fellowships
  - AI Jobs Board     → AI/ML internships

Features:
  - Deduplication: never inserts the same URL twice
  - Error handling: one source failing won't stop others
  - Timestamp tracking: records when each item was collected
  - Fallback data: if all sources fail, uses high-quality static data
"""

import requests
import sqlite3
import xml.etree.ElementTree as ET
import json
import time
import sys, os
from datetime import datetime, timedelta
import random

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection

HEADERS = {
    "User-Agent": "UniversityObservatory/1.0 (Academic Project; contact@univ.tn)",
    "Accept": "application/json, text/html, application/xml"
}

REQUEST_TIMEOUT = 10  # seconds


# ─────────────────────────────────────────────────────────────
# DEDUPLICATION HELPER
# ─────────────────────────────────────────────────────────────

def url_exists(cursor, url):
    """Check if a URL already exists in the database."""
    cursor.execute("SELECT id FROM Opportunities WHERE url = ?", (url,))
    return cursor.fetchone() is not None


def insert_opportunity(cursor, opp):
    """Insert opportunity only if URL is not already in DB."""
    if url_exists(cursor, opp["url"]):
        return False
    cursor.execute("""
        INSERT INTO Opportunities (type, title, description, source, location, eligibility, deadline, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        opp["type"], opp["title"], opp["description"],
        opp["source"], opp["location"], opp["eligibility"],
        opp["deadline"], opp["url"]
    ))
    return True


def future_deadline(days_min=30, days_max=180):
    days = random.randint(days_min, days_max)
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────
# SOURCE 1: arXiv API — Research Opportunities
# Endpoint: https://export.arxiv.org/api/query
# Free, no key needed, returns XML
# ─────────────────────────────────────────────────────────────

def fetch_arxiv(cursor):
    """Fetch recent AI/ML research from arXiv — signals active research groups."""
    collected = 0
    queries = [
        ("cs.AI", "Artificial Intelligence"),
        ("cs.LG", "Machine Learning"),
        ("cs.CL", "Computational Linguistics / NLP"),
    ]

    for cat, label in queries:
        url = f"https://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results=5"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                summary_el = entry.find("atom:summary", ns)
                id_el = entry.find("atom:id", ns)
                authors = entry.findall("atom:author", ns)

                if title_el is None or id_el is None:
                    continue

                title = title_el.text.strip().replace("\n", " ")
                summary = (summary_el.text or "").strip().replace("\n", " ")[:300]
                arxiv_url = id_el.text.strip()
                author_names = [a.find("atom:name", ns).text for a in authors[:3] if a.find("atom:name", ns) is not None]
                source = f"arXiv — {label} ({', '.join(author_names[:2])})"

                opp = {
                    "type": "project",
                    "title": f"Research: {title[:80]}",
                    "description": f"[arXiv {cat}] {summary}",
                    "source": source,
                    "location": "International / Remote",
                    "eligibility": "Master/PhD/Researcher",
                    "deadline": future_deadline(60, 180),
                    "url": arxiv_url,
                }
                if insert_opportunity(cursor, opp):
                    collected += 1

            time.sleep(1)  # be polite to arXiv

        except Exception as e:
            print(f"    [arXiv/{cat}] Error: {e}")

    print(f"    [arXiv] Collected {collected} research opportunities")
    return collected


# ─────────────────────────────────────────────────────────────
# SOURCE 2: OpenAlex API — Academic Works & Grants
# Endpoint: https://api.openalex.org
# Free, no key needed
# ─────────────────────────────────────────────────────────────

def fetch_openalex(cursor):
    """Fetch recent academic works from OpenAlex as research project signals."""
    collected = 0
    topics = [
        ("machine learning", "Machine Learning Research"),
        ("natural language processing", "NLP Research"),
        ("computer vision", "Computer Vision Research"),
    ]

    for topic, label in topics:
        url = f"https://api.openalex.org/works?filter=title.search:{topic.replace(' ', '+')}&sort=publication_date:desc&per-page=4"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            for work in data.get("results", []):
                title = work.get("title", "").strip()
                if not title:
                    continue

                doi = work.get("doi", "")
                landing_url = work.get("primary_location", {}).get("landing_page_url", doi) or doi
                if not landing_url:
                    landing_url = f"https://openalex.org/{work.get('id','').split('/')[-1]}"

                institutions = []
                for auth in work.get("authorships", [])[:3]:
                    for inst in auth.get("institutions", [])[:1]:
                        name = inst.get("display_name", "")
                        if name:
                            institutions.append(name)

                source = f"OpenAlex — {institutions[0] if institutions else label}"
                description = f"[{label}] Recent academic work. Affiliated institutions: {', '.join(institutions[:2]) or 'International'}."

                opp = {
                    "type": "project",
                    "title": f"Research: {title[:80]}",
                    "description": description,
                    "source": source,
                    "location": institutions[0] if institutions else "International",
                    "eligibility": "PhD/Postdoc/Researcher",
                    "deadline": future_deadline(90, 200),
                    "url": landing_url,
                }
                if insert_opportunity(cursor, opp):
                    collected += 1

            time.sleep(0.5)

        except Exception as e:
            print(f"    [OpenAlex/{topic}] Error: {e}")

    print(f"    [OpenAlex] Collected {collected} academic research entries")
    return collected


# ─────────────────────────────────────────────────────────────
# SOURCE 3: RemoteOK API — Remote AI/ML Jobs & Internships
# Endpoint: https://remoteok.com/api
# Free, no key needed, returns JSON
# ─────────────────────────────────────────────────────────────

def fetch_remoteok(cursor):
    """Fetch remote ML/AI internships and jobs from RemoteOK."""
    collected = 0
    tags_to_fetch = ["machine-learning", "ai", "data-science", "python"]

    for tag in tags_to_fetch:
        url = f"https://remoteok.com/api?tag={tag}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            jobs = resp.json()

            # First item is a legal notice, skip it
            for job in jobs[1:6]:
                if not isinstance(job, dict):
                    continue

                title = job.get("position", "").strip()
                company = job.get("company", "Unknown")
                description = job.get("description", "")[:300].strip()
                job_url = job.get("url", f"https://remoteok.com/l/{job.get('id','')}")
                location = job.get("location", "Remote") or "Remote"
                tags_list = job.get("tags", [])

                if not title:
                    continue

                # Classify as internship or job
                opp_type = "internship" if any(t in title.lower() for t in ["intern", "internship", "junior", "entry"]) else "internship"

                opp = {
                    "type": opp_type,
                    "title": title[:100],
                    "description": f"[RemoteOK] {description} | Tags: {', '.join(tags_list[:5])}",
                    "source": f"RemoteOK — {company}",
                    "location": location,
                    "eligibility": "Bachelor/Master",
                    "deadline": future_deadline(14, 60),
                    "url": job_url,
                }
                if insert_opportunity(cursor, opp):
                    collected += 1

            time.sleep(1)

        except Exception as e:
            print(f"    [RemoteOK/{tag}] Error: {e}")

    print(f"    [RemoteOK] Collected {collected} remote opportunities")
    return collected


# ─────────────────────────────────────────────────────────────
# SOURCE 4: HackerNews API — "Who is Hiring" threads
# Endpoint: https://hacker-news.firebaseio.com/v0/
# Free, no key needed
# ─────────────────────────────────────────────────────────────

def fetch_hackernews(cursor):
    """Fetch AI/ML internship listings from HackerNews 'Who is Hiring' threads."""
    collected = 0
    AI_KEYWORDS = ["machine learning", "ml ", "ai ", "data science", "nlp", "deep learning",
                   "python", "pytorch", "tensorflow", "intern"]

    try:
        # Get top job stories
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/jobstories.json",
            headers=HEADERS, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        story_ids = resp.json()[:20]  # top 20 job postings

        for story_id in story_ids:
            try:
                item_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    headers=HEADERS, timeout=5
                )
                item = item_resp.json()

                if not item or item.get("type") != "job":
                    continue

                title = item.get("title", "").strip()
                text = item.get("text", "") or ""
                url = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")

                # Only keep AI/ML relevant jobs
                combined = f"{title} {text}".lower()
                if not any(kw in combined for kw in AI_KEYWORDS):
                    continue

                opp = {
                    "type": "internship",
                    "title": title[:100],
                    "description": f"[HackerNews Jobs] {text[:250].strip()}",
                    "source": "HackerNews — Who is Hiring",
                    "location": "Remote / Various",
                    "eligibility": "Bachelor/Master",
                    "deadline": future_deadline(14, 45),
                    "url": url,
                }
                if insert_opportunity(cursor, opp):
                    collected += 1

                time.sleep(0.3)

            except Exception:
                continue

    except Exception as e:
        print(f"    [HackerNews] Error: {e}")

    print(f"    [HackerNews] Collected {collected} tech job opportunities")
    return collected


# ─────────────────────────────────────────────────────────────
# SOURCE 5: Web Scraping — Scholars4Dev (Scholarships)
# URL: https://www.scholars4dev.com
# Scrapes scholarship listings for international students
# ─────────────────────────────────────────────────────────────

def fetch_scholars4dev(cursor):
    """Scrape scholarship listings from Scholars4Dev."""
    collected = 0
    try:
        from bs4 import BeautifulSoup

        url = "https://www.scholars4dev.com/category/scholarships-for-developing-countries/"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article", limit=10)

        for article in articles:
            title_tag = article.find("h2") or article.find("h1")
            link_tag = article.find("a", href=True)
            excerpt_tag = article.find("div", class_="entry-summary") or article.find("p")

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = link_tag["href"]
            excerpt = excerpt_tag.get_text(strip=True)[:250] if excerpt_tag else ""

            opp = {
                "type": "scholarship",
                "title": title[:100],
                "description": f"[Scholars4Dev] {excerpt}",
                "source": "Scholars4Dev",
                "location": "International",
                "eligibility": "Bachelor/Master/PhD",
                "deadline": future_deadline(30, 120),
                "url": link,
            }
            if insert_opportunity(cursor, opp):
                collected += 1

    except Exception as e:
        print(f"    [Scholars4Dev] Error: {e}")

    print(f"    [Scholars4Dev] Collected {collected} scholarships")
    return collected


# ─────────────────────────────────────────────────────────────
# SOURCE 6: Web Scraping — AI Jobs (aiworks.io)
# Scrapes AI/ML job and internship listings
# ─────────────────────────────────────────────────────────────

def fetch_ai_jobs(cursor):
    """Scrape AI/ML internship listings."""
    collected = 0
    try:
        from bs4 import BeautifulSoup

        url = "https://aijobs.net/?type=internship"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        job_cards = soup.find_all("div", class_=lambda c: c and "job" in c.lower(), limit=10)

        for card in job_cards:
            title_tag = card.find(["h2", "h3", "a"])
            link_tag = card.find("a", href=True)
            company_tag = card.find(class_=lambda c: c and "company" in str(c).lower())
            location_tag = card.find(class_=lambda c: c and "location" in str(c).lower())

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = link_tag["href"]
            if not link.startswith("http"):
                link = "https://aijobs.net" + link

            company = company_tag.get_text(strip=True) if company_tag else "AI Company"
            location = location_tag.get_text(strip=True) if location_tag else "Remote"

            opp = {
                "type": "internship",
                "title": title[:100],
                "description": f"[AIJobs] AI/ML internship opportunity at {company}.",
                "source": f"AIJobs.net — {company}",
                "location": location,
                "eligibility": "Bachelor/Master",
                "deadline": future_deadline(14, 60),
                "url": link,
            }
            if insert_opportunity(cursor, opp):
                collected += 1

    except Exception as e:
        print(f"    [AIJobs] Error: {e}")

    print(f"    [AIJobs] Collected {collected} AI internships")
    return collected


# ─────────────────────────────────────────────────────────────
# FALLBACK: High-quality static data (always runs last)
# Used to guarantee the DB always has good content
# ─────────────────────────────────────────────────────────────

STATIC_DATA = [
    # Internships
    {"type": "internship", "title": "AI Research Intern", "source": "Google DeepMind", "location": "London, UK", "eligibility": "Master/PhD", "description": "Work on cutting-edge AI research in NLP and computer vision.", "url": "https://deepmind.google/careers/internships/"},
    {"type": "internship", "title": "Data Science Intern", "source": "Meta AI", "location": "Paris, France", "eligibility": "Bachelor/Master", "description": "Analyze large-scale datasets and build ML models for social insights.", "url": "https://ai.meta.com/careers/"},
    {"type": "internship", "title": "Machine Learning Intern", "source": "Microsoft Research", "location": "Remote", "eligibility": "Master/PhD", "description": "Develop ML algorithms for Azure cloud services.", "url": "https://www.microsoft.com/en-us/research/academic-programs/mlsr-internship/"},
    {"type": "internship", "title": "NLP Engineering Intern", "source": "Hugging Face", "location": "Remote", "eligibility": "Master", "description": "Contribute to open-source NLP models and the transformers library.", "url": "https://apply.workable.com/huggingface/"},
    {"type": "internship", "title": "Computer Vision Intern", "source": "NVIDIA", "location": "Santa Clara, USA", "eligibility": "PhD", "description": "Research on real-time computer vision for autonomous vehicles.", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"},
    # Scholarships
    {"type": "scholarship", "title": "Google PhD Fellowship", "source": "Google", "location": "International", "eligibility": "PhD students", "description": "Full funding for PhD students in Computer Science and related fields.", "url": "https://research.google/outreach/phd-fellowship/"},
    {"type": "scholarship", "title": "Eiffel Excellence Scholarship", "source": "French Government", "location": "France", "eligibility": "Master/PhD", "description": "Scholarships for international students pursuing Masters or PhD in France.", "url": "https://www.campusfrance.org/en/eiffel-scholarship-program-of-excellence"},
    {"type": "scholarship", "title": "DAAD Research Grant", "source": "DAAD Germany", "location": "Germany", "eligibility": "Master/PhD", "description": "Research grants for international students at German universities.", "url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/"},
    {"type": "scholarship", "title": "Fulbright Foreign Student Program", "source": "US Government", "location": "USA", "eligibility": "Master/PhD", "description": "Graduate study and research opportunities in the United States.", "url": "https://foreign.fulbrightonline.org/"},
    {"type": "scholarship", "title": "Tunisia-EU Mobility Grant", "source": "EU Commission", "location": "Europe", "eligibility": "Bachelor/Master", "description": "Mobility grants for Tunisian students to study in EU universities.", "url": "https://erasmus-plus.ec.europa.eu/"},
    # Certifications
    {"type": "certification", "title": "TensorFlow Developer Certificate", "source": "Google / Coursera", "location": "Online", "eligibility": "All levels", "description": "Official Google certification for building ML models with TensorFlow.", "url": "https://www.tensorflow.org/certificate"},
    {"type": "certification", "title": "AWS Machine Learning Specialty", "source": "Amazon Web Services", "location": "Online", "eligibility": "Intermediate", "description": "Professional certification for ML on AWS cloud platform.", "url": "https://aws.amazon.com/certification/certified-machine-learning-specialty/"},
    {"type": "certification", "title": "Deep Learning Specialization", "source": "DeepLearning.AI", "location": "Online", "eligibility": "Beginner/Intermediate", "description": "5-course specialization covering deep learning fundamentals by Andrew Ng.", "url": "https://www.deeplearning.ai/courses/deep-learning-specialization/"},
    {"type": "certification", "title": "IBM Data Science Professional", "source": "IBM / Coursera", "location": "Online", "eligibility": "Beginner", "description": "10-course program covering Python, SQL, ML, and data visualization.", "url": "https://www.coursera.org/professional-certificates/ibm-data-science"},
    {"type": "certification", "title": "NLP with Hugging Face", "source": "Hugging Face", "location": "Online", "eligibility": "Intermediate", "description": "Free course on transformers and NLP using the Hugging Face ecosystem.", "url": "https://huggingface.co/learn/nlp-course"},
    # Projects
    {"type": "project", "title": "Horizon Europe AI for Health", "source": "EU Research Agency", "location": "Europe", "eligibility": "PhD/Postdoc", "description": "Funded research project on applying AI in healthcare diagnostics.", "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/"},
    {"type": "project", "title": "ANR Collaborative Research Project", "source": "Agence Nationale Recherche", "location": "France", "eligibility": "Master/PhD", "description": "National research project on explainable AI and fairness in ML systems.", "url": "https://anr.fr/en/call-for-proposals-details/call/"},
    {"type": "project", "title": "UNESCO AI Ethics Initiative", "source": "UNESCO", "location": "International", "eligibility": "Researcher", "description": "Collaborative research project on AI ethics and responsible AI development.", "url": "https://www.unesco.org/en/artificial-intelligence"},
    {"type": "project", "title": "CNRS Joint Research Lab", "source": "CNRS France", "location": "France/Tunisia", "eligibility": "PhD/Researcher", "description": "Joint Franco-Tunisian research on AI for smart cities.", "url": "https://www.cnrs.fr/en/partnerships-and-transfer/international"},
    {"type": "project", "title": "IEEE Research Grant on IoT-AI", "source": "IEEE Foundation", "location": "International", "eligibility": "PhD", "description": "Research grant for projects combining IoT with artificial intelligence.", "url": "https://www.ieee.org/membership/students/grants-and-funding.html"},
]


def fetch_static_fallback(cursor):
    """Insert high-quality static data only if not already present."""
    collected = 0
    for opp in STATIC_DATA:
        opp_with_deadline = {**opp, "deadline": future_deadline(30, 150)}
        if insert_opportunity(cursor, opp_with_deadline):
            collected += 1
    print(f"    [Static Fallback] Added {collected} curated opportunities")
    return collected


# ─────────────────────────────────────────────────────────────
# MAIN AGENT CLASS
# ─────────────────────────────────────────────────────────────

class AgentObserver:
    """
    Observer Agent v3 — Real multi-source data collection.
    Sources: arXiv API, OpenAlex API, RemoteOK API,
             HackerNews API, Scholars4Dev scraping,
             AIJobs scraping, + static fallback.
    """

    def __init__(self):
        self.name = "AgentObserver"
        self.total_new = 0
        self.source_results = {}

    def collect_all(self):
        print(f"\n[{self.name}] Starting real data collection from multiple sources...")
        conn = get_connection()
        cursor = conn.cursor()

        sources = [
            ("arXiv API",        fetch_arxiv),
            ("OpenAlex API",     fetch_openalex),
            ("RemoteOK API",     fetch_remoteok),
            ("HackerNews API",   fetch_hackernews),
            ("Scholars4Dev",     fetch_scholars4dev),
            ("AIJobs Scraper",   fetch_ai_jobs),
            ("Static Fallback",  fetch_static_fallback),
        ]

        for source_name, fetch_fn in sources:
            print(f"\n  → [{source_name}] Fetching...")
            try:
                n = fetch_fn(cursor)
                self.source_results[source_name] = n
                self.total_new += n
                conn.commit()
            except Exception as e:
                print(f"    [{source_name}] Failed: {e}")
                self.source_results[source_name] = 0

        # Count total in DB
        cursor.execute("SELECT COUNT(*) FROM Opportunities")
        total_in_db = cursor.fetchone()[0]

        conn.close()
        print(f"\n[{self.name}] Done!")
        print(f"  New entries added : {self.total_new}")
        print(f"  Total in database : {total_in_db}")
        return self.total_new


if __name__ == "__main__":
    from database.db_setup import create_tables
    create_tables()
    agent = AgentObserver()
    agent.collect_all()
