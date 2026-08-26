"""Project stack detector.

Scans a directory and identifies the tech stack, frameworks, and services needed.
"""

from pathlib import Path

STACK_SIGNATURES = {
    "python": {
        "files": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
        "services": ["python"],
        "label": "Python",
    },
    "node": {
        "files": ["package.json"],
        "exclude": ["requirements.txt"],
        "services": ["node"],
        "label": "Node.js",
    },
    "go": {
        "files": ["go.mod"],
        "services": ["go"],
        "label": "Go",
    },
    "rust": {
        "files": ["Cargo.toml"],
        "services": ["rust"],
        "label": "Rust",
    },
    "java": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "services": ["java"],
        "label": "Java",
    },
    "ruby": {
        "files": ["Gemfile"],
        "services": ["ruby"],
        "label": "Ruby",
    },
    "deno": {
        "files": ["deno.json", "deno.jsonc"],
        "services": ["deno"],
        "label": "Deno",
    },
    "bun": {
        "files": ["bun.lockb", "bunfig.toml"],
        "exclude": ["package.json"],
        "services": ["bun"],
        "label": "Bun",
    },
    "elixir": {
        "files": ["mix.exs"],
        "services": ["elixir"],
        "label": "Elixir",
    },
    "php": {
        "files": ["composer.json"],
        "services": ["php"],
        "label": "PHP",
    },
}

FRAMEWORK_SIGNATURES = {
    "django": {"files": ["manage.py"], "port": 8000},
    "flask": {"imports": ["flask"], "port": 5000},
    "fastapi": {"imports": ["fastapi"], "port": 8000},
    "express": {"imports": ["express"], "port": 3000},
    "nextjs": {"files": ["next.config.js", "next.config.mjs", "next.config.ts"], "port": 3000},
    "gin": {"imports": ["github.com/gin-gonic/gin"], "port": 8080},
    "actix": {"imports": ["actix-web"], "port": 8080},
    "rails": {"files": ["config/routes.rb"], "port": 3000},
    "spring": {"files": ["src/main/java"], "port": 8080},
    "laravel": {"files": ["artisan"], "port": 8000},
    "phoenix": {"imports": ["phoenix"], "port": 4000},
    "hugo": {"files": ["config.toml", "config.yaml", "hugo.toml", "hugo.yaml"], "port": 1313},
    "jekyll": {"files": ["_config.yml", "Gemfile"], "port": 4000},
    "astro": {"files": ["astro.config.mjs", "astro.config.ts"], "port": 4321},
    "gatsby": {"files": ["gatsby-config.js", "gatsby-config.ts"], "port": 8000},
}

SERVICE_SIGNATURES = {
    "postgres": {
        "files": ["docker-compose.yml", "docker-compose.yaml"],
        "pattern": r"postgres",
        "port": 5432,
    },
    "redis": {"pattern": r"redis", "port": 6379},
    "mysql": {"pattern": r"mysql", "port": 3306},
    "mongo": {"pattern": r"mongo", "port": 27017},
    "elasticsearch": {"pattern": r"elastic", "port": 9200},
    "kafka": {"pattern": r"kafka", "port": 9092},
    "minio": {"pattern": r"minio", "port": 9000},
    "rabbitmq": {"pattern": r"rabbitmq|amqp", "port": 5672},
    "nats": {"pattern": r"nats", "port": 4222},
}

GRAPHQL_FILES = ["schema.graphql", "schema.gql"]
STATIC_SITE_INDICATORS = ["public/", "static/", "_site/", "dist/"]

DOCKER_FILES = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"]
TERRAFORM_FILES = ["main.tf", "variables.tf", "outputs.tf", "terraform.tfstate"]


class StackInfo:
    """Detected stack information."""

    def __init__(self, path: Path):
        self.path = path
        self.languages: list[str] = []
        self.frameworks: list[str] = []
        self.services: list[str] = []
        self.has_docker = False
        self.has_terraform = False
        self.has_ci = False
        self.has_graphql = False
        self.is_static_site = False
        self.port: int | None = None

    @property
    def primary_language(self) -> str | None:
        return self.languages[0] if self.languages else None

    @property
    def primary_framework(self) -> str | None:
        return self.frameworks[0] if self.frameworks else None

    @property
    def stack_label(self) -> str:
        parts = []
        if self.primary_framework:
            parts.append(self.primary_framework.title())
        elif self.primary_language:
            parts.append(self.primary_language.title())
        if self.services:
            parts.append(f"+ {', '.join(self.services)}")
        return " ".join(parts) if parts else "Unknown stack"

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "languages": self.languages,
            "frameworks": self.frameworks,
            "services": self.services,
            "docker": self.has_docker,
            "terraform": self.has_terraform,
            "graphql": self.has_graphql,
            "static_site": self.is_static_site,
            "port": self.port,
        }


def _check_files(path: Path, file_list: list[str]) -> bool:
    return any((path / f).exists() for f in file_list)


def _scan_requirements(path: Path) -> list[str]:
    """Scan Python requirements for framework imports."""
    req_file = path / "requirements.txt"
    if not req_file.exists():
        return []
    try:
        content = req_file.read_text(encoding="utf-8").lower()
        return content
    except Exception:
        return ""


def _scan_package_json(path: Path) -> str:
    """Scan package.json for framework dependencies."""
    pkg = path / "package.json"
    if not pkg.exists():
        return ""
    try:
        import json

        data = json.loads(pkg.read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        return " ".join(deps.keys()).lower()
    except Exception:
        return ""


def detect_stack(path: str | None = None) -> StackInfo:
    """Detect the project stack at the given path."""
    project_path = Path(path) if path else Path.cwd()
    info = StackInfo(project_path)

    for lang, sig in STACK_SIGNATURES.items():
        if _check_files(project_path, sig["files"]):
            info.languages.append(lang)

    req_content = _scan_requirements(project_path)
    pkg_content = _scan_package_json(path)
    all_content = f"{req_content} {pkg_content}"

    for fw, sig in FRAMEWORK_SIGNATURES.items():
        if "files" in sig and _check_files(project_path, sig["files"]):
            info.frameworks.append(fw)
            if not info.port:
                info.port = sig["port"]
        elif "imports" in sig:
            for imp in sig["imports"]:
                if imp in all_content:
                    info.frameworks.append(fw)
                    if not info.port:
                        info.port = sig["port"]
                    break

    docker_content = ""
    for dc in ["docker-compose.yml", "docker-compose.yaml"]:
        dc_path = project_path / dc
        if dc_path.exists():
            try:
                docker_content = dc_path.read_text(encoding="utf-8").lower()
            except Exception:
                pass
            break

    combined = f"{all_content} {docker_content}"
    for svc, sig in SERVICE_SIGNATURES.items():
        pattern = sig.get("pattern", "")
        if pattern and pattern in combined:
            info.services.append(svc)

    info.has_docker = _check_files(project_path, DOCKER_FILES)
    info.has_terraform = _check_files(project_path, TERRAFORM_FILES)
    info.has_ci = (
        _check_files(
            project_path,
            [
                ".github/workflows",
                ".gitlab-ci.yml",
                "Jenkinsfile",
                ".circleci",
            ],
        )
        or (project_path / ".github" / "workflows").is_dir()
    )

    info.has_graphql = _check_files(project_path, GRAPHQL_FILES)
    graphql_dirs = list(project_path.rglob("*.graphql"))[:5] if not info.has_graphql else []
    if not info.has_graphql and graphql_dirs:
        info.has_graphql = True

    if any(fw in ("hugo", "jekyll", "astro", "gatsby") for fw in info.frameworks):
        info.is_static_site = True
    if _check_files(project_path, STATIC_SITE_INDICATORS):
        info.is_static_site = True

    return info
