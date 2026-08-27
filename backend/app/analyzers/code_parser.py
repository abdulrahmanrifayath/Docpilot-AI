from pathlib import Path
from typing import List, Optional, Set
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.entity import CodeEntityBase
from backend.app.analyzers.python_parser import PythonParser
from backend.app.analyzers.js_ts_parser import JsTsParser

PYTHON_EXTENSIONS = {".py", ".pyw"}
JS_TS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}


class CodeParser:
    @staticmethod
    def _read_source(file_path: Path) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not read source file {file_path}: {e}")
            return None

    @classmethod
    def parse_file(cls, full_path: Path, rel_path: str) -> List[CodeEntityBase]:
        ext = full_path.suffix.lower()
        content = cls._read_source(full_path)
        if content is None:
            return []

        if ext in PYTHON_EXTENSIONS:
            return PythonParser.parse_source(content, rel_path)
        elif ext in JS_TS_EXTENSIONS:
            return JsTsParser.parse_source(content, rel_path)

        return []

    @classmethod
    def parse_repository(cls, repo_dir: Path) -> List[CodeEntityBase]:
        all_entities: List[CodeEntityBase] = []
        ignored_dirs = set(settings.IGNORED_DIRECTORIES)
        ignored_files = set(settings.IGNORED_FILES)

        def walk(current_dir: Path, rel_prefix: str = ""):
            try:
                entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
            except (PermissionError, OSError) as e:
                logger.warning(f"Inaccessible directory {current_dir}: {e}")
                return

            for entry in entries:
                name = entry.name
                rel_path = f"{rel_prefix}/{name}".lstrip("/")

                if entry.is_dir():
                    if name in ignored_dirs:
                        continue
                    walk(entry, rel_path)
                else:
                    if name in ignored_files:
                        continue
                    ext = entry.suffix.lower()
                    if ext in PYTHON_EXTENSIONS or ext in JS_TS_EXTENSIONS:
                        entities = cls.parse_file(entry, rel_path)
                        all_entities.extend(entities)

        walk(repo_dir)
        return all_entities
