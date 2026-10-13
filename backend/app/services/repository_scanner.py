import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.core.logging import logger

# Supported language extensions
LANGUAGE_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".pyw": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sql": "SQL",
    ".md": "Markdown",
    ".markdown": "Markdown",
}

# Known binary extensions
BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".tiff", ".svgz",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".dmg",
    ".pyc", ".pyo", ".pyd", ".class", ".jar", ".war", ".ear",
    ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".flv", ".webm",
    ".lockb", ".wasm"
}

# Configured ignored directory names
DEFAULT_IGNORED_DIRS: Set[str] = {
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    ".next",
    ".nuxt",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".idea",
    ".vscode",
    "coverage",
    ".turbo",
    "target",
    ".svn",
    ".hg",
}

MAX_FILE_SIZE_FOR_EXACT_COUNT = 5 * 1024 * 1024  # 5 MB


class RepositoryScanner:
    """
    Deterministic static repository scanner without AI/LLM dependency.
    Performs file discovery, safe line counting, and heuristic technology detection.
    """

    def __init__(self, ignored_dirs: Optional[Set[str]] = None):
        self.ignored_dirs = set(ignored_dirs or DEFAULT_IGNORED_DIRS)
        if hasattr(settings, "IGNORED_DIRECTORIES"):
            self.ignored_dirs.update(settings.IGNORED_DIRECTORIES)

    def scan_repository(self, repo_dir: Path) -> Dict[str, Any]:
        """
        Recursively scans repository directory.
        Returns:
            {
                "total_files": int,
                "total_directories": int,
                "total_lines": int,
                "languages": Dict[str, Dict[str, int]],
                "categories": Dict[str, int],
                "frameworks": List[str],
                "infrastructure": List[str],
                "tree": Dict[str, Any]
            }
        """
        if not repo_dir.exists() or not repo_dir.is_dir():
            return {
                "total_files": 0,
                "total_directories": 0,
                "total_lines": 0,
                "languages": {},
                "categories": {},
                "frameworks": [],
                "infrastructure": [],
                "tree": {
                    "name": repo_dir.name or "root",
                    "path": ".",
                    "type": "directory",
                    "children": [],
                },
            }

        total_files = 0
        total_directories = 0
        total_lines = 0
        categories: Dict[str, int] = {}
        languages: Dict[str, Dict[str, int]] = {}
        all_file_paths: List[str] = []

        # 1. Recursive Tree Discovery
        def scan_dir(current_path: Path) -> Dict[str, Any]:
            nonlocal total_files, total_directories, total_lines
            rel_path = current_path.relative_to(repo_dir).as_posix() if current_path != repo_dir else "."
            children: List[Dict[str, Any]] = []

            try:
                entries = sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                entries = []

            for entry in entries:
                # Check ignored directory or hidden internal folder
                if entry.name in self.ignored_dirs or entry.name in {".git", "__pycache__"}:
                    continue

                if entry.is_dir():
                    total_directories += 1
                    child_dir = scan_dir(entry)
                    children.append(child_dir)
                elif entry.is_file():
                    total_files += 1
                    file_info = self._analyze_file(entry, repo_dir)
                    all_file_paths.append(file_info["path"])

                    # Aggregate category
                    cat = file_info["file_category"]
                    categories[cat] = categories.get(cat, 0) + 1

                    # Aggregate language & line count
                    lines = file_info["estimated_line_count"]
                    total_lines += lines
                    lang = file_info.get("language")
                    if lang:
                        if lang not in languages:
                            languages[lang] = {"files": 0, "lines": 0}
                        languages[lang]["files"] += 1
                        languages[lang]["lines"] += lines

                    children.append(file_info)

            return {
                "name": current_path.name or "root",
                "path": rel_path,
                "type": "directory",
                "children": children,
            }

        tree = scan_dir(repo_dir)

        # 2. Sort Languages by lines descending
        sorted_languages = dict(
            sorted(languages.items(), key=lambda item: item[1]["lines"], reverse=True)
        )

        # 3. Detect Frameworks & Infrastructure
        frameworks = self._detect_frameworks(repo_dir, all_file_paths)
        infrastructure = self._detect_infrastructure(repo_dir, all_file_paths)

        logger.info(
            f"Scanned repo '{repo_dir.name}': {total_files} files, {total_directories} dirs, "
            f"{total_lines} lines. Frameworks: {frameworks}. Infra: {infrastructure}"
        )

        return {
            "total_files": total_files,
            "total_directories": total_directories,
            "total_lines": total_lines,
            "languages": sorted_languages,
            "categories": categories,
            "frameworks": frameworks,
            "infrastructure": infrastructure,
            "tree": tree,
        }

    def _analyze_file(self, file_path: Path, repo_root: Path) -> Dict[str, Any]:
        """Extracts metadata, category, language, and safe line counts for a single file."""
        rel_path = file_path.relative_to(repo_root).as_posix()
        ext = file_path.suffix.lower()
        file_name = file_path.name
        file_size = 0
        try:
            file_size = file_path.stat().st_size
        except Exception:
            pass

        # Identify language
        language = LANGUAGE_EXTENSIONS.get(ext)

        # Identify category
        category = self._classify_category(file_name, ext, language)

        # Safe line counting
        is_binary = self._is_binary_file(file_path, ext, file_size)
        if is_binary:
            category = "asset" if ext in {".png", ".jpg", ".jpeg", ".ico", ".svg", ".webp", ".gif"} else "binary"
            line_count = 0
        else:
            line_count = self._count_lines_safe(file_path, file_size)

        return {
            "name": file_name,
            "path": rel_path,
            "type": "file",
            "extension": ext,
            "file_size": file_size,
            "estimated_line_count": line_count,
            "file_category": category,
            "language": language,
        }

    def _classify_category(self, file_name: str, ext: str, language: Optional[str]) -> str:
        name_lower = file_name.lower()
        if (
            name_lower == "dockerfile"
            or name_lower.startswith("dockerfile.")
            or name_lower.startswith("docker-compose")
            or ext == ".tf"
            or ext == ".tfvars"
            or name_lower.startswith(".env")
        ):
            return "infrastructure"

        if ext in BINARY_EXTENSIONS:
            if ext in {".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".gif", ".woff", ".woff2", ".ttf"}:
                return "asset"
            return "binary"

        if language in {"Python", "JavaScript", "TypeScript", "HTML", "CSS", "SQL"}:
            return "code"

        if language == "Markdown" or ext in {".txt", ".rst", ".adoc", ".doc"}:
            return "documentation"

        if language in {"JSON", "YAML"} or ext in {".toml", ".ini", ".cfg", ".xml", ".editorconfig"}:
            return "config"

        if ext in {".csv", ".tsv", ".parquet"}:
            return "data"

        return "code" if language else "other"

    def _is_binary_file(self, file_path: Path, ext: str, file_size: int) -> bool:
        if ext in BINARY_EXTENSIONS:
            return True
        if file_size == 0:
            return False

        # Read first 1024 bytes to inspect for null byte indicator
        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
                if b"\x00" in header:
                    return True
        except Exception:
            return True
        return False

    def _count_lines_safe(self, file_path: Path, file_size: int) -> int:
        if file_size == 0:
            return 0

        # Handling very large files safely (estimate via sampling first 64KB)
        if file_size > MAX_FILE_SIZE_FOR_EXACT_COUNT:
            try:
                with open(file_path, "rb") as f:
                    sample = f.read(65536)
                    sample_lines = sample.count(b"\n")
                    if sample_lines > 0 and len(sample) > 0:
                        estimated = int((sample_lines / len(sample)) * file_size)
                        return max(1, estimated)
            except Exception:
                return 0

        # Fast and safe chunked newline byte count
        line_count = 0
        has_bytes = False
        last_char = b""
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    has_bytes = True
                    line_count += chunk.count(b"\n")
                    last_char = chunk[-1:]
            if has_bytes and last_char != b"\n":
                line_count += 1
            return line_count
        except Exception:
            return 0

    def _detect_frameworks(self, repo_dir: Path, all_file_paths: List[str]) -> List[str]:
        """Heuristic framework detection for Python and JS/TS."""
        frameworks: Set[str] = set()
        file_set = set(all_file_paths)

        # 1. Python Frameworks (FastAPI, Django, Flask)
        req_content = ""
        for rel_file in all_file_paths:
            fname = Path(rel_file).name.lower()
            if fname in {"requirements.txt", "pipfile", "pyproject.toml", "setup.py", "setup.cfg"}:
                p = repo_dir / rel_file
                if p.is_file():
                    try:
                        req_content += " " + p.read_text(encoding="utf-8", errors="ignore").lower()
                    except Exception:
                        pass

        if "fastapi" in req_content:
            frameworks.add("FastAPI")
        if "django" in req_content:
            frameworks.add("Django")
        if "flask" in req_content:
            frameworks.add("Flask")

        # Check Django structural presence
        if any(f.endswith("manage.py") or f.endswith("wsgi.py") for f in file_set):
            frameworks.add("Django")

        # Check imports in Python files if not already detected
        py_files = [f for f in file_set if f.endswith(".py")][:40]  # sample first 40 py files
        for py_rel in py_files:
            py_path = repo_dir / py_rel
            try:
                with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
                    for _ in range(35):  # check top 35 import lines
                        line = f.readline()
                        if not line:
                            break
                        line_lower = line.strip().lower()
                        if "import fastapi" in line_lower or "from fastapi" in line_lower:
                            frameworks.add("FastAPI")
                        elif "import django" in line_lower or "from django" in line_lower:
                            frameworks.add("Django")
                        elif "import flask" in line_lower or "from flask" in line_lower:
                            frameworks.add("Flask")
            except Exception:
                pass

        # 2. JavaScript / TypeScript Frameworks (React, Next.js, Express, Node.js)
        # Search all package.json files across the repository (root, frontend, client, backend)
        for rel_file in all_file_paths:
            if Path(rel_file).name.lower() == "package.json":
                frameworks.add("Node.js")
                p = repo_dir / rel_file
                if p.is_file():
                    try:
                        pkg_data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                        deps = {
                            **pkg_data.get("dependencies", {}),
                            **pkg_data.get("devDependencies", {}),
                        }
                        dep_keys = {k.lower() for k in deps.keys()}

                        if "react" in dep_keys or "react-dom" in dep_keys:
                            frameworks.add("React")
                        if "next" in dep_keys:
                            frameworks.add("Next.js")
                            frameworks.add("React")
                        if "express" in dep_keys:
                            frameworks.add("Express")
                    except Exception:
                        pass


        # Check Node.js lockfiles
        if any(
            f in file_set
            for f in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", ".nvmrc"]
        ):
            frameworks.add("Node.js")

        # Check Next.js configurations
        if any(
            f.startswith("next.config.") or "next.config.js" in f or "next.config.mjs" in f or "next.config.ts" in f
            for f in file_set
        ):
            frameworks.add("Next.js")
            frameworks.add("React")

        # Check React via JSX/TSX extensions or imports
        if any(f.endswith(".jsx") or f.endswith(".tsx") for f in file_set):
            frameworks.add("React")

        js_ts_files = [f for f in file_set if f.endswith((".js", ".jsx", ".ts", ".tsx"))][:40]
        for js_rel in js_ts_files:
            js_path = repo_dir / js_rel
            try:
                with open(js_path, "r", encoding="utf-8", errors="ignore") as f:
                    for _ in range(35):
                        line = f.readline()
                        if not line:
                            break
                        line_lower = line.strip().lower()
                        if "from 'react'" in line_lower or 'from "react"' in line_lower or "import react" in line_lower:
                            frameworks.add("React")
                        if "from 'next" in line_lower or 'from "next' in line_lower:
                            frameworks.add("Next.js")
                        if "from 'express'" in line_lower or 'from "express"' in line_lower or "require('express')" in line_lower or 'require("express")' in line_lower:
                            frameworks.add("Express")
            except Exception:
                pass

        return sorted(list(frameworks))

    def _detect_infrastructure(self, repo_dir: Path, all_file_paths: List[str]) -> List[str]:
        """Detects infrastructure components like Docker, GitHub Actions, Kubernetes, Terraform, and env files."""
        infra: Set[str] = set()
        file_set = set(all_file_paths)

        # 1. Dockerfile
        for f in file_set:
            fname = Path(f).name.lower()
            if fname == "dockerfile" or fname.startswith("dockerfile.") or fname.endswith(".dockerfile"):
                infra.add("Dockerfile")
                break

        # 2. docker-compose.yml
        for f in file_set:
            fname = Path(f).name.lower()
            if fname in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
                infra.add("docker-compose.yml")
                break

        # 3. GitHub Actions
        for f in file_set:
            if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml")):
                infra.add("GitHub Actions")
                break

        # 4. Kubernetes manifests
        for f in file_set:
            f_lower = f.lower()
            if f_lower.startswith(("k8s/", "kubernetes/", "deploy/")) or f_lower.endswith(("-k8s.yaml", "-k8s.yml", "deployment.yaml", "service.yaml")):
                infra.add("Kubernetes manifests")
                break
            elif f_lower.endswith((".yaml", ".yml")):
                # Check for apiVersion and kind
                p = repo_dir / f
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")[:1000]
                    if "apiversion:" in content.lower() and "kind:" in content.lower():
                        infra.add("Kubernetes manifests")
                        break
                except Exception:
                    pass

        # 5. Terraform
        for f in file_set:
            if f.endswith((".tf", ".tfvars")) or f.startswith(".terraform/"):
                infra.add("Terraform")
                break

        # 6. Environment files
        for f in file_set:
            fname = Path(f).name.lower()
            if fname == ".env" or fname.startswith(".env."):
                infra.add("environment files")
                break

        return sorted(list(infra))


repository_scanner = RepositoryScanner()
