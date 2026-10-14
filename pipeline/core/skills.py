"""Curated technology vocabulary shared by claim extraction (M5) and evidence search (M4, M5)."""

import re

# Canonical display name -> extra surface forms. Every form, and the display name, matches case-insensitively
# as a whole word unless it is listed in CASE_SENSITIVE or AMBIGUOUS_FORMS below.
TECHNOLOGIES: dict[str, tuple[str, ...]] = {
    # Languages
    "Python": ("python3",),
    "Java": (),
    "JavaScript": ("js", "ecmascript", "es6"),
    "TypeScript": ("ts",),
    "C++": ("cpp", "c plus plus"),
    "C#": ("csharp", "c sharp"),
    "C": ("c language", "c programming", "ansi c"),
    "Go": ("golang",),
    "Rust": (),
    "Kotlin": (),
    "Swift": (),
    "Objective-C": ("objective c", "objc"),
    "Ruby": (),
    "PHP": (),
    "Scala": (),
    "Haskell": (),
    "Elixir": (),
    "Erlang": (),
    "Clojure": (),
    "OCaml": (),
    "F#": ("fsharp",),
    "Perl": (),
    "Lua": (),
    "R": ("r language", "r programming", "rstats"),
    "Julia": (),
    "MATLAB": (),
    "Dart": (),
    "Solidity": (),
    "Fortran": (),
    "COBOL": (),
    "Groovy": (),
    "Bash": ("shell scripting", "shell script"),
    "PowerShell": (),
    "SQL": (),
    "HTML": ("html5",),
    "CSS": ("css3",),
    "Sass": ("scss",),
    # Web and backend frameworks
    "React": ("react.js", "reactjs"),
    "React Native": (),
    "Angular": ("angularjs", "angular.js"),
    "Vue": ("vue.js", "vuejs"),
    "Svelte": ("sveltekit",),
    "Next.js": ("nextjs",),
    "Nuxt": ("nuxt.js", "nuxtjs"),
    "Redux": (),
    "jQuery": (),
    "Tailwind CSS": ("tailwind", "tailwindcss"),
    "Bootstrap": (),
    "Node.js": ("nodejs", "node"),
    "Express": ("express.js", "expressjs"),
    "NestJS": ("nest.js",),
    "Django": (),
    "Django REST Framework": ("drf",),
    "Flask": (),
    "FastAPI": (),
    "Spring Boot": ("springboot",),
    "Spring": ("spring framework",),
    "Hibernate": (),
    "Ruby on Rails": ("rails", "ror"),
    "Laravel": (),
    "Symfony": (),
    ".NET": ("dotnet", "asp.net", ".net core", "asp.net core"),
    "GraphQL": (),
    "gRPC": (),
    "Celery": (),
    "Flutter": (),
    "Android": (),
    "iOS": (),
    "SwiftUI": (),
    "Electron": (),
    # Databases and messaging
    "PostgreSQL": ("postgres", "psql"),
    "MySQL": (),
    "MariaDB": (),
    "SQLite": (),
    "MongoDB": ("mongo",),
    "Redis": (),
    "Elasticsearch": ("elastic search", "opensearch"),
    "Cassandra": (),
    "DynamoDB": (),
    "Oracle Database": ("oracle db", "pl/sql"),
    "Microsoft SQL Server": ("sql server", "mssql", "t-sql"),
    "Neo4j": (),
    "Firebase": (),
    "Supabase": (),
    "Snowflake": (),
    "BigQuery": (),
    "Kafka": ("apache kafka",),
    "RabbitMQ": (),
    "pgvector": (),
    # Cloud and DevOps
    "AWS": ("amazon web services",),
    "Azure": ("microsoft azure",),
    "GCP": ("google cloud", "google cloud platform"),
    "Docker": ("dockerfile", "docker compose", "docker-compose"),
    "Kubernetes": ("k8s",),
    "Helm": (),
    "Terraform": (),
    "Ansible": (),
    "Jenkins": (),
    "GitHub Actions": (),
    "GitLab CI": ("gitlab ci/cd",),
    "CircleCI": (),
    "Git": (),
    "Linux": (),
    "Nginx": (),
    "Apache Airflow": ("airflow",),
    "Prometheus": (),
    "Grafana": (),
    "Datadog": (),
    "Heroku": (),
    "Vercel": (),
    "OpenShift": (),
    "Serverless": (),
    "MinIO": (),
    # Testing and build tools
    "pytest": (),
    "JUnit": (),
    "Jest": (),
    "Cypress": (),
    "Playwright": (),
    "Selenium": (),
    "Maven": (),
    "Gradle": (),
    "CMake": (),
    "Webpack": (),
    "Vite": (),
    # Data and machine learning
    "pandas": (),
    "NumPy": (),
    "SciPy": (),
    "scikit-learn": ("sklearn", "scikit learn"),
    "TensorFlow": (),
    "Keras": (),
    "PyTorch": ("torch",),
    "JAX": (),
    "XGBoost": (),
    "LightGBM": (),
    "Hugging Face": ("huggingface", "hugging face transformers"),
    "LangChain": (),
    "OpenCV": (),
    "NLTK": (),
    "spaCy": (),
    "MLflow": (),
    "Apache Spark": ("spark", "pyspark"),
    "Hadoop": (),
    "Jupyter": ("jupyter notebook", "jupyterlab"),
    "Matplotlib": (),
    "Tableau": (),
    "Power BI": ("powerbi",),
}

# Forms that are ordinary English words: in free text they count only when written exactly like this.
CASE_SENSITIVE = {
    form.lower(): form for form in ("Swift", "Rust", "Spring", "React", "Dart", "Julia", "Rails", "Express", "Spark")
}
CASE_SENSITIVE.update({form.lower(): form for form in ("Bootstrap", "Electron", "Snowflake", "Vite")})
CASE_SENSITIVE.update({form.lower(): form for form in ("Helm", "Jest", "Flask", "Celery", "Hadoop", "JAX", "Ruby")})

# Too ambiguous in free text ("go", "C grade", "R&D", "graph node", "py"): only inside a skills section.
AMBIGUOUS_FORMS = frozenset({"go", "c", "r", "node", "ts", "torch", "ror", "drf", "psql", "serverless"})

_BEFORE = r"(?<![A-Za-z0-9_+#.&])"
_AFTER = r"(?![A-Za-z0-9_+#&])"


def forms_of(display: str) -> tuple[str, ...]:
    """All lower-case surface forms of a technology, display name first."""
    return (display.lower(), *TECHNOLOGIES.get(display, ()))


def mention_regex(forms) -> re.Pattern:
    """Whole-word, case-insensitive alternation of surface forms; longer forms win at the same position."""
    ordered = sorted(set(forms), key=lambda form: (-len(form), form))
    return re.compile(_BEFORE + "(" + "|".join(re.escape(form) for form in ordered) + ")" + _AFTER, re.I)


def allowed_in_prose(matched: str, strict_case: bool = True) -> bool:
    """False for an ambiguous form, or (with strict_case) a common-word form not written in its exact case."""
    key = matched.lower()
    if key in AMBIGUOUS_FORMS:
        return False
    return not strict_case or key not in CASE_SENSITIVE or matched == CASE_SENSITIVE[key]


def vocabulary_aliases() -> dict[str, str]:
    """Surface form -> lower-case canonical name, for the skill normaliser."""
    return {form: display.lower() for display in TECHNOLOGIES for form in forms_of(display)[1:]}
