import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Mapping of file extensions to language names
EXTENSION_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".sql": "SQL",
    ".sh": "Shell",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
}

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".cache",
    ".idea",
    ".vscode",
    "coverage",
    ".pytest_cache",
    "target",
}


class LanguageDetector:
    def detect(self, repo_dir: Path) -> Tuple[Dict[str, Any], List[str]]:
        """
        Detects languages and frameworks in a repository directory.
        Returns:
            languages: Dict mapping language name to {files: int, lines: int, percent: float}
            frameworks: List of identified frameworks
        """
        lang_counts: Dict[str, Dict[str, int]] = {}
        total_lines = 0

        for path in repo_dir.rglob("*"):
            if path.is_file():
                # Check if path contains ignored directory
                if any(part in IGNORED_DIRS for part in path.parts):
                    continue

                ext = path.suffix.lower()
                lang = EXTENSION_MAP.get(ext)
                if not lang:
                    continue

                try:
                    # Quick line count
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = sum(1 for _ in f)
                except Exception:
                    lines = 0

                if lang not in lang_counts:
                    lang_counts[lang] = {"files": 0, "lines": 0}

                lang_counts[lang]["files"] += 1
                lang_counts[lang]["lines"] += lines
                total_lines += lines

        # Calculate percentages
        languages_result: Dict[str, Any] = {}
        for lang, data in lang_counts.items():
            pct = round((data["lines"] / total_lines * 100), 1) if total_lines > 0 else 0.0
            languages_result[lang] = {
                "files": data["files"],
                "lines": data["lines"],
                "percent": pct,
            }

        # Sort by line count descending
        languages_result = dict(
            sorted(languages_result.items(), key=lambda item: item[1]["lines"], reverse=True)
        )

        # Detect frameworks
        frameworks = self._detect_frameworks(repo_dir)

        return languages_result, frameworks

    def _detect_frameworks(self, repo_dir: Path) -> List[str]:
        frameworks: Set[str] = set()

        # Check Python dependencies
        req_file = repo_dir / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding="utf-8", errors="ignore").lower()
                if "fastapi" in content:
                    frameworks.add("FastAPI")
                if "flask" in content:
                    frameworks.add("Flask")
                if "django" in content:
                    frameworks.add("Django")
                if "sqlalchemy" in content:
                    frameworks.add("SQLAlchemy")
                if "pydantic" in content:
                    frameworks.add("Pydantic")
                if "celery" in content:
                    frameworks.add("Celery")
                if "pytest" in content:
                    frameworks.add("Pytest")
                if "torch" in content or "pytorch" in content:
                    frameworks.add("PyTorch")
                if "redis" in content:
                    frameworks.add("Redis")
            except Exception:
                pass

        pyproject = repo_dir / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
                for fw in ["FastAPI", "Flask", "Django", "SQLAlchemy", "Pydantic", "Pytest"]:
                    if fw.lower() in content:
                        frameworks.add(fw)
            except Exception:
                pass

        # Check Node / JavaScript dependencies
        pkg_json = repo_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                dep_keys = {k.lower() for k in deps.keys()}
                if "react" in dep_keys:
                    frameworks.add("React")
                if "next" in dep_keys:
                    frameworks.add("Next.js")
                if "vue" in dep_keys:
                    frameworks.add("Vue")
                if "express" in dep_keys:
                    frameworks.add("Express")
                if "tailwindcss" in dep_keys:
                    frameworks.add("Tailwind CSS")
                if "vite" in dep_keys:
                    frameworks.add("Vite")
                if "@reduxjs/toolkit" in dep_keys or "redux" in dep_keys:
                    frameworks.add("Redux")
                if "prisma" in dep_keys or "@prisma/client" in dep_keys:
                    frameworks.add("Prisma")
                if "mongoose" in dep_keys:
                    frameworks.add("Mongoose")
            except Exception:
                pass

        # Check Infrastructure / DevOps
        if (repo_dir / "Dockerfile").exists():
            frameworks.add("Docker")
        if (repo_dir / "docker-compose.yml").exists() or (repo_dir / "docker-compose.yaml").exists():
            frameworks.add("Docker Compose")
        if (repo_dir / ".github" / "workflows").exists():
            frameworks.add("GitHub Actions")

        return sorted(list(frameworks))
