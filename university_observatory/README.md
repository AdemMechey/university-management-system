# 🎓 University Observatory — Multi-Agent System v3

A Multi-Agent System (MAS) for monitoring, classifying, and recommending
internships, scholarships, certifications, and research opportunities.

---

## 🚀 SETUP (first time only)

```bash
pip install streamlit pandas scikit-learn requests beautifulsoup4 schedule
```

---

## ▶️ HOW TO RUN

### Option A — Manual run
```bash
# Step 1: Run all agents (collects + classifies + clusters + recommends)
python run_mas.py

# Step 2: Launch dashboard
python -m streamlit run dashboard/app.py
```

### Option B — Auto scheduler (keeps DB always updated)
Open TWO terminals:

**Terminal 1 — Dashboard:**
```bash
python -m streamlit run dashboard/app.py
```

**Terminal 2 — Auto Scheduler:**
```bash
# Update every 6 hours (default)
python scheduler.py --now

# Or set custom interval (e.g. every 2 hours)
python scheduler.py --now --interval 2
```

---

## 🌐 Real Data Sources

| Source | Type | Data Collected |
|---|---|---|
| arXiv API | API | Research papers in cs.AI, cs.LG, cs.CL |
| OpenAlex API | API | Academic works & institutions |
| RemoteOK API | API | Remote ML/AI internships |
| HackerNews API | API | Tech job postings |
| Scholars4Dev | Scraping | International scholarships |
| AIJobs.net | Scraping | AI/ML internship listings |
| Static Curated | Built-in | 20 hand-picked high-quality opportunities |

---

## 🤖 Agent Architecture

```
AgentCoordinator
├── AgentObserver        → Real data collection (APIs + scraping)
├── AgentClassifier      → NLP domain tagging
├── AgentCluster         → KMeans grouping
└── AgentRecommendation  → Smart scoring (degree + field + skills + interests + experience)
```

## 🧠 Recommendation Scoring

| Factor | Weight |
|---|---|
| Degree Level | 25% |
| Field of Study | 25% |
| Skills Match | 20% |
| Interests Match | 20% |
| Experience | 10% |

---

## 🔐 Demo Accounts

| Email | Password | Profile |
|---|---|---|
| alice@univ.tn | password123 | Master in AI, 1yr exp |
| mohamed@univ.tn | password123 | PhD in CS, 3yr exp |
| sara@univ.tn | password123 | Bachelor in Data Science |

---

## 📁 Project Structure

```
university_observatory/
├── run_mas.py               ← Run all agents manually
├── scheduler.py             ← Auto-update scheduler
├── requirements.txt
├── database/
│   └── db_setup.py          ← Schema + auth functions
├── agents/
│   ├── agent_observer.py    ← Real scraping + APIs
│   ├── agent_classifier.py  ← NLP classification
│   ├── agent_cluster.py     ← KMeans clustering
│   └── agent_recommendation.py ← Smart recommendations
└── dashboard/
    └── app.py               ← Full Streamlit dashboard
```
