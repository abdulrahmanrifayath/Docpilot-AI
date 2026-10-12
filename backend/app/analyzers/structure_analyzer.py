from pathlib import Path
from typing import Any, Dict, List

from app.analyzers.language_detector import IGNORED_DIRS

PURPOSE_PATTERNS = {
    "api": "API and HTTP routing endpoints",
    "routes": "Route declarations and request handlers",
    "controllers": "Controller logic and request mediation",
    "services": "Business logic and domain service operations",
    "models": "Data models, schemas, and ORM entities",
    "entities": "Core business entities and data structures",
    "schemas": "Data validation schemas and DTOs",
    "database": "Database connections, sessions, and migrations",
    "db": "Database persistence layer and queries",
    "migrations": "Database schema evolution and migration scripts",
    "components": "Reusable UI components and views",
    "pages": "Application route pages and views",
    "views": "Presentation layer and user interface templates",
    "utils": "Helper functions and shared utility routines",
    "helpers": "Auxiliary utility functions",
    "core": "Core application configuration, settings, and constants",
    "config": "Environment and runtime settings",
    "middleware": "Request/response interceptors and middlewares",
    "middlewares": "Request/response interceptors and middlewares",
    "auth": "Authentication, authorization, and token handling",
    "security": "Security rules, encryption, and access control",
    "hooks": "Custom state and lifecycle hooks",
    "store": "Global state management and actions",
    "tests": "Automated unit and integration test suite",
    "test": "Automated tests and fixtures",
    "docs": "Project documentation and guides",
    "scripts": "Automation and maintenance build scripts",
    "integrations": "Third-party APIs and external service adapters",
    "analyzers": "Code and repository static analysis modules",
    "parsers": "Source code AST and grammar parsers",
    "diagrams": "Diagram generation and visualization components",
}


class StructureAnalyzer:
    def analyze(self, repo_dir: Path) -> Dict[str, Any]:
        """Analyzes directory tree structure and annotates folder purposes."""
        folder_purposes: Dict[str, str] = {}
        all_files: List[str] = []

        tree = self._build_tree(repo_dir, repo_dir, folder_purposes, all_files)

        return {
            "root_name": repo_dir.name,
            "tree": tree,
            "folder_purposes": folder_purposes,
            "total_files": len(all_files),
        }

    def _build_tree(
        self,
        current_path: Path,
        repo_root: Path,
        folder_purposes: Dict[str, str],
        all_files: List[str],
    ) -> Dict[str, Any]:
        rel_path = current_path.relative_to(repo_root).as_posix() if current_path != repo_root else "."
        folder_name = current_path.name.lower()

        # Determine purpose
        purpose = PURPOSE_PATTERNS.get(folder_name)
        if not purpose:
            for key, val in PURPOSE_PATTERNS.items():
                if key in folder_name:
                    purpose = val
                    break
        if not purpose:
            purpose = "General project files and modules"

        if rel_path != ".":
            folder_purposes[rel_path] = purpose

        children: List[Dict[str, Any]] = []

        try:
            for item in sorted(current_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if item.name in IGNORED_DIRS or item.name.startswith("."):
                    continue

                if item.is_dir():
                    sub_tree = self._build_tree(item, repo_root, folder_purposes, all_files)
                    if sub_tree["children"]:  # Only include non-empty directories
                        children.append(sub_tree)
                elif item.is_file():
                    rel_file = item.relative_to(repo_root).as_posix()
                    all_files.append(rel_file)
                    children.append(
                        {
                            "name": item.name,
                            "type": "file",
                            "path": rel_file,
                            "size": item.stat().st_size,
                        }
                    )
        except PermissionError:
            pass

        return {
            "name": current_path.name or "root",
            "type": "directory",
            "path": rel_path,
            "purpose": purpose,
            "children": children,
        }
