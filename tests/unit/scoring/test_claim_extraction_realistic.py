"""RuleBasedClaimProvider on realistic multi-section resumes: the exact expected claim set (FR-11)."""

import pytest

from pipeline.adapters.rule_claims import RuleBasedClaimProvider
from pipeline.core.scoring.claims import ClaimExtractor

BACKEND = """Ayesha Khan
Senior Backend Engineer | ayesha@example.com | github.com/ayeshak

SUMMARY
Backend engineer with 5 years of experience in Python and over 2 years of experience with Django.

TECHNICAL SKILLS
Languages: Python, Go, SQL, Bash
Frameworks: Django, FastAPI, Celery
Databases: PostgreSQL (4 years), Redis
Cloud & DevOps: Docker, Kubernetes, AWS, Terraform, GitHub Actions

EXPERIENCE
Acme Payments - Backend Engineer (2021-present)
- Built a payments API in FastAPI backed by Postgres and Kafka.
- Cut deploy time by 40% by moving CI to GitHub Actions.

Beta Corp - Software Engineer (2019-2021)
- 3+ yrs Java on a Spring Boot monolith; migrated services to gRPC.

EDUCATION
BSc Computer Science, 2019
"""

COMPETITIVE = """Bilal Ahmed - Software Engineer (New Grad)

Competitive Programming
* Codeforces Expert (max rating 1820), handle: bilal_cp
* LeetCode Knight - solved 650+ problems on LeetCode
* Solved 1,200 problems on Codeforces
* ICPC Asia Regional finalist 2023

Skills: C++, Python, Java | Data Structures, Algorithms

Experience
Software Intern, Foo Labs (Summer 2024)
- Wrote C++ services and Python tooling; 2 years of C++ through contests.
- Master's thesis on graph algorithms.
"""

ML = """Dr. Sara Malik
Machine Learning Engineer

Profile
ML engineer with 4 years experience in PyTorch and 3 years of TensorFlow. Comfortable with R and Python.

Tech Stack
- Python (6 years), R, SQL
- PyTorch, TensorFlow, scikit-learn, XGBoost, Hugging Face
- pandas / NumPy / Matplotlib
- Docker, Kubernetes, MLflow, Apache Airflow, GCP

Projects
- Fraud detection: gradient-boosted trees (XGBoost) served with FastAPI on Google Cloud.
- Built Spark pipelines for feature engineering; tuned LightGBM baselines.

Publications
- "Robust embeddings", NeurIPS workshop 2023
"""

MESSY = """JOHN DOE | Full-Stack Dev | john@doe.dev
Skills | JavaScript • TypeScript • React • Node.js • Express.js • MongoDB • HTML/CSS • Git
TOOLS: VS Code / Postman / Jira / Docker

WORK
• Freelance (2020-2024): built 12 client sites with React.js and Next.js; React - 4 years
• Led a team; ready to go live in 2 weeks; got a C in calculus but shipped on time
• Used Rust occasionally; love swift iterations and the spring release cycle
• Rated 1450 on Codeforces; LeetCode: 300+ problems solved

INTERESTS: hiking, chess
"""


def skills(*names, **years):
    return {("skill", n, None, None, None) for n in names} | {("skill", n, y, None, None) for n, y in years.items()}


EXPECTED = {
    "backend": skills(
        "Go",
        "SQL",
        "Bash",
        "FastAPI",
        "Celery",
        "Redis",
        "Docker",
        "Kubernetes",
        "AWS",
        "Terraform",
        "GitHub Actions",
        "Kafka",
        "Spring Boot",
        "gRPC",
        Python=5.0,
        Django=2.0,
        PostgreSQL=4.0,
        Java=3.0,
    ),
    "competitive": skills("Python", "Java", **{"C++": 2.0})
    | {
        ("rating", "codeforces", None, 1820, None),
        ("rating", "leetcode", None, 1850, None),
        ("solved", "leetcode", None, None, 650),
        ("solved", "codeforces", None, None, 1200),
    },
    "ml": skills(
        "R",
        "SQL",
        "scikit-learn",
        "XGBoost",
        "Hugging Face",
        "pandas",
        "NumPy",
        "Matplotlib",
        "Docker",
        "Kubernetes",
        "MLflow",
        "Apache Airflow",
        "GCP",
        "FastAPI",
        "Apache Spark",
        "LightGBM",
        PyTorch=4.0,
        TensorFlow=3.0,
        Python=6.0,
    ),
    "messy": skills(
        "JavaScript",
        "TypeScript",
        "Node.js",
        "Express",
        "MongoDB",
        "HTML",
        "CSS",
        "Git",
        "Docker",
        "Next.js",
        "Rust",
        React=4.0,
    )
    | {("rating", "codeforces", None, 1450, None), ("solved", "leetcode", None, None, 300)},
}
RESUMES = {"backend": BACKEND, "competitive": COMPETITIVE, "ml": ML, "messy": MESSY}


def extract(resume):
    return ClaimExtractor(RuleBasedClaimProvider()).extract("cand-1", resume)


def summary(claims):
    return {(c.kind, c.subject, c.years, c.rating, c.solved) for c in claims}


@pytest.mark.parametrize("name", sorted(RESUMES))
def test_exact_claim_set(name):
    assert summary(extract(RESUMES[name])) == EXPECTED[name]


@pytest.mark.parametrize("name", sorted(RESUMES))
def test_every_claim_text_is_a_verbatim_snippet(name):
    for claim in extract(RESUMES[name]):
        assert claim.text in RESUMES[name], claim


def test_snippets_cover_the_duration_phrase():
    texts = {c.subject: c.text for c in extract(BACKEND)}
    assert texts["Python"] == "5 years of experience in Python"
    assert texts["Django"] == "2 years of experience with Django"
    assert texts["PostgreSQL"] == "PostgreSQL (4 years)"
    assert texts["Java"] == "3+ yrs Java"


def test_precision_and_recall_over_all_resumes():
    found = {(name, item) for name, text in RESUMES.items() for item in summary(extract(text))}
    wanted = {(name, item) for name, items in EXPECTED.items() for item in items}
    true_positives = len(found & wanted)
    assert true_positives / len(found) == 1.0  # precision
    assert true_positives / len(wanted) == 1.0  # recall
