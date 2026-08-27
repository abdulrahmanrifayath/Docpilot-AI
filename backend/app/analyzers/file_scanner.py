import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.structure import StructureItem, FileSummaryInfo
from backend.app.schemas.technology import LanguageStat

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".tiff",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".flac", ".ogg",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".class", ".pyc", ".pyo", ".pyd", ".o", ".a", ".lib",
    ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

LANGUAGE_CONFIG = {
    ".py": {"language": "Python", "category": "source_code"},
    ".pyw": {"language": "Python", "category": "source_code"},
    ".js": {"language": "JavaScript", "category": "source_code"},
    ".mjs": {"language": "JavaScript", "category": "source_code"},
    ".cjs": {"language": "JavaScript", "category": "source_code"},
    ".jsx": {"language": "JavaScript", "category": "source_code"},
    ".ts": {"language": "TypeScript", "category": "source_code"},
    ".tsx": {"language": "TypeScript", "category": "source_code"},
    ".html": {"language": "HTML", "category": "source_code"},
    ".htm": {"language": "HTML", "category": "source_code"},
    ".css": {"language": "CSS", "category": "style"},
    ".scss": {"language": "SCSS", "category": "style"},
    ".sass": {"language": "SASS", "category": "style"},
    ".less": {"language": "LESS", "category": "style"},
    ".json": {"language": "JSON", "category": "configuration"},
    ".json5": {"language": "JSON", "category": "configuration"},
    ".yml": {"language": "YAML", "category": "configuration"},
    ".yaml": {"language": "YAML", "category": "configuration"},
    ".sql": {"language": "SQL", "category": "data"},
    ".md": {"language": "Markdown", "category": "documentation"},
    ".markdown": {"language": "Markdown", "category": "documentation"},
    ".rst": {"language": "reStructuredText", "category": "documentation"},
    ".txt": {"language": "Text", "category": "documentation"},
    ".toml": {"language": "TOML", "category": "configuration"},
    ".ini": {"language": "INI", "category": "configuration"},
    ".cfg": {"language": "Config", "category": "configuration"},
    ".conf": {"language": "Config", "category": "configuration"},
    ".env": {"language": "Environment", "category": "configuration"},
    ".tf": {"language": "HCL / Terraform", "category": "infrastructure"},
    ".tfvars": {"language": "HCL / Terraform", "category": "infrastructure"},
    ".sh": {"language": "Shell", "category": "configuration"},
    ".bash": {"language": "Shell", "category": "configuration"},
    ".zsh": {"language": "Shell", "category": "configuration"},
    ".ps1": {"language": "PowerShell", "category": "configuration"},
    ".bat": {"language": "Batch", "category": "configuration"},
    ".cmd": {"language": "Batch", "category": "configuration"},
    ".rs": {"language": "Rust", "category": "source_code"},
    ".go": {"language": "Go", "category": "source_code"},
    ".java": {"language": "Java", "category": "source_code"},
    ".c": {"language": "C", "category": "source_code"},
    ".h": {"language": "C Header", "category": "source_code"},
    ".cpp": {"language": "C++", "category": "source_code"},
    ".hpp": {"language": "C++ Header", "category": "source_code"},
    ".cs": {"language": "C#", "category": "source_code"},
    ".php": {"language": "PHP", "category": "source_code"},
    ".graphql": {"language": "GraphQL", "category": "source_code"},
    ".gql": {"language": "GraphQL", "category": "source_code"},
    ".proto": {"language": "Protobuf", "category": "source_code"},
}

SPECIAL_FILENAMES = {
    "dockerfile": {"language": "Dockerfile", "category": "infrastructure"},
    "dockerfile.dev": {"language": "Dockerfile", "category": "infrastructure"},
    "dockerfile.prod": {"language": "Dockerfile", "category": "infrastructure"},
    "docker-compose.yml": {"language": "YAML", "category": "infrastructure"},
    "docker-compose.yaml": {"language": "YAML", "category": "infrastructure"},
    "compose.yml": {"language": "YAML", "category": "infrastructure"},
    "compose.yaml": {"language": "YAML", "category": "infrastructure"},
    "makefile": {"language": "Makefile", "category": "configuration"},
    "jenkinsfile": {"language": "Groovy", "category": "infrastructure"},
    ".gitignore": {"language": "GitIgnore", "category": "configuration"},
    ".dockerignore": {"language": "DockerIgnore", "category": "configuration"},
    ".env": {"language": "Environment", "category": "configuration"},
    ".env.example": {"language": "Environment", "category": "configuration"},
    ".env.local": {"language": "Environment", "category": "configuration"},
}


class FileScanner:
    @staticmethod
    def is_binary_file(file_path: Path, ext: str) -> bool:
        if ext in BINARY_EXTENSIONS:
            return True
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\x00" in chunk:
                    return True
        except Exception:
            return True
        return False

    @staticmethod
    def count_lines(file_path: Path, is_binary: bool, file_size: int) -> int:
        if is_binary or file_size == 0:
            return 0
        try:
            # For files <= 5MB, fast byte read
            if file_size <= 5 * 1024 * 1024:
                with open(file_path, "rb") as f:
                    content = f.read()
                    # Count newline characters
                    return content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)
            else:
                # Streaming buffer count for larger files
                line_count = 0
                last_char = b""
                with open(file_path, "rb") as f:
                    while chunk := f.read(64 * 1024):
                        line_count += chunk.count(b"\n")
                        last_char = chunk[-1:] if chunk else b""
                if last_char and last_char != b"\n":
                    line_count += 1
                return line_count
        except Exception as e:
            logger.warning(f"Error counting lines in {file_path}: {e}")
            return 0

    @classmethod
    def classify_file(cls, file_name: str, ext: str) -> Tuple[Optional[str], str]:
        lower_name = file_name.lower()
        if lower_name in SPECIAL_FILENAMES:
            info = SPECIAL_FILENAMES[lower_name]
            return info["language"], info["category"]

        if lower_name.startswith(".env"):
            return "Environment", "configuration"

        if lower_name.endswith(".dockerfile"):
            return "Dockerfile", "infrastructure"

        if ext in LANGUAGE_CONFIG:
            info = LANGUAGE_CONFIG[ext]
            return info["language"], info["category"]

        if ext in BINARY_EXTENSIONS:
            return None, "asset"

        return None, "other"

    @classmethod
    def scan_repository(cls, repo_dir: Path) -> Dict[str, Any]:
        ignored_dirs = set(settings.IGNORED_DIRECTORIES)
        ignored_files = set(settings.IGNORED_FILES)

        total_files = 0
        total_dirs = 0
        total_lines = 0
        total_size = 0

        lang_counters: Dict[str, Dict[str, int]] = {}  # { "Python": { "files": X, "lines": Y } }
        category_counters: Dict[str, Dict[str, int]] = {}  # { "source_code": { "files": X, "lines": Y } }
        flat_file_list: List[FileSummaryInfo] = []

        def traverse(current_dir: Path, rel_prefix: str = "") -> List[StructureItem]:
            nonlocal total_files, total_dirs, total_lines, total_size
            items: List[StructureItem] = []

            try:
                entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
            except (PermissionError, OSError) as e:
                logger.warning(f"Inaccessible directory {current_dir}: {e}")
                return items

            for entry in entries:
                name = entry.name
                rel_path = f"{rel_prefix}/{name}".lstrip("/")

                if entry.is_dir():
                    if name in ignored_dirs:
                        continue
                    total_dirs += 1
                    children = traverse(entry, rel_path)
                    dir_size = sum(c.size for c in children)
                    dir_lines = sum(c.lines for c in children)
                    items.append(
                        StructureItem(
                            name=name,
                            path=rel_path,
                            type="directory",
                            size=dir_size,
                            lines=dir_lines,
                            category="directory",
                            children=children,
                        )
                    )
                else:
                    if name in ignored_files:
                        continue

                    try:
                        file_stat = entry.stat()
                        f_size = file_stat.st_size
                    except OSError:
                        f_size = 0

                    ext = entry.suffix.lower()
                    is_binary = cls.is_binary_file(entry, ext)
                    lines = cls.count_lines(entry, is_binary, f_size)
                    language, category = cls.classify_file(name, ext)

                    total_files += 1
                    total_size += f_size
                    total_lines += lines

                    # Update language counters
                    if language:
                        if language not in lang_counters:
                            lang_counters[language] = {"files": 0, "lines": 0}
                        lang_counters[language]["files"] += 1
                        lang_counters[language]["lines"] += lines

                    # Update category counters
                    if category not in category_counters:
                        category_counters[category] = {"files": 0, "lines": 0}
                    category_counters[category]["files"] += 1
                    category_counters[category]["lines"] += lines

                    summary_info = FileSummaryInfo(
                        path=rel_path,
                        name=name,
                        lines=lines,
                        size=f_size,
                        language=language,
                        category=category,
                    )
                    flat_file_list.append(summary_info)

                    items.append(
                        StructureItem(
                            name=name,
                            path=rel_path,
                            type="file",
                            size=f_size,
                            lines=lines,
                            category=category,
                            language=language,
                            extension=ext or None,
                        )
                    )

            return items

        structure = traverse(repo_dir)

        # Calculate language percentage
        languages_dict: Dict[str, LanguageStat] = {}
        for lang, counts in sorted(lang_counters.items(), key=lambda item: item[1]["lines"], reverse=True):
            pct = round((counts["lines"] / total_lines * 100), 2) if total_lines > 0 else 0.0
            languages_dict[lang] = LanguageStat(
                files=counts["files"],
                lines=counts["lines"],
                percentage=pct,
            )

        # Largest files by size / lines
        largest_files = sorted(flat_file_list, key=lambda f: f.lines, reverse=True)[:10]

        return {
            "structure": structure,
            "total_files": total_files,
            "total_directories": total_dirs,
            "total_lines": total_lines,
            "total_size_bytes": total_size,
            "languages": languages_dict,
            "categories": category_counters,
            "largest_files": largest_files,
            "flat_files": flat_file_list,
        }
