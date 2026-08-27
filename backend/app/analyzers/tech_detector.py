import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from backend.app.core.logging import logger
from backend.app.schemas.technology import FrameworkInfo, InfrastructureInfo, LanguageStat


class TechDetector:
    @staticmethod
    def _read_file_safe(file_path: Path, max_bytes: int = 50000) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
        except Exception as e:
            logger.debug(f"Could not read {file_path}: {e}")
            return ""

    @classmethod
    def detect_frameworks(cls, repo_dir: Path, flat_files: List[Any]) -> List[FrameworkInfo]:
        frameworks: List[FrameworkInfo] = []
        detected_names: Set[str] = set()

        file_paths_lower = {f.path.lower() for f in flat_files}
        root_files = {f.name.lower(): f.path for f in flat_files if "/" not in f.path}

        # -------------------------------------------------------------
        # 1. Parse Manifests
        # -------------------------------------------------------------
        # Python dependencies
        py_deps: Set[str] = set()
        req_txt = repo_dir / "requirements.txt"
        if req_txt.exists():
            content = cls._read_file_safe(req_txt)
            for line in content.splitlines():
                line = line.strip().split("#")[0]
                if line:
                    match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if match:
                        py_deps.add(match.group(1).lower())

        pyproject = repo_dir / "pyproject.toml"
        if pyproject.exists():
            content = cls._read_file_safe(pyproject).lower()
            for pkg in ["fastapi", "django", "flask", "sqlalchemy", "pydantic", "celery", "tornado"]:
                if pkg in content:
                    py_deps.add(pkg)

        # JavaScript/TypeScript dependencies
        js_deps: Set[str] = set()
        js_dev_deps: Set[str] = set()
        pkg_json = repo_dir / "package.json"
        if pkg_json.exists():
            try:
                pkg_data = json.loads(cls._read_file_safe(pkg_json, max_bytes=200000))
                deps = pkg_data.get("dependencies", {})
                dev_deps = pkg_data.get("devDependencies", {})
                for k in deps.keys():
                    js_deps.add(k.lower())
                for k in dev_deps.keys():
                    js_dev_deps.add(k.lower())
            except Exception as e:
                logger.debug(f"Error parsing package.json: {e}")

        # Also search subdirectories for package.json (e.g. frontend/package.json)
        for f in flat_files:
            if f.name.lower() == "package.json" and f.path != "package.json":
                try:
                    pkg_data = json.loads(cls._read_file_safe(repo_dir / f.path, max_bytes=200000))
                    for k in pkg_data.get("dependencies", {}).keys():
                        js_deps.add(k.lower())
                    for k in pkg_data.get("devDependencies", {}).keys():
                        js_dev_deps.add(k.lower())
                except Exception:
                    pass

        # -------------------------------------------------------------
        # 2. Python Framework Detection
        # -------------------------------------------------------------
        # FastAPI
        fastapi_indicators = []
        if "fastapi" in py_deps:
            fastapi_indicators.append("fastapi declared in Python dependencies")
        for f in flat_files:
            if f.path.endswith(".py") and f.size < 50000:
                code = cls._read_file_safe(repo_dir / f.path, 5000)
                if "from fastapi import" in code or "import fastapi" in code or "FastAPI(" in code:
                    fastapi_indicators.append(f"FastAPI import/instance in {f.path}")
                    break
        if fastapi_indicators and "FastAPI" not in detected_names:
            confidence = "HIGH" if "fastapi" in py_deps else "MEDIUM"
            frameworks.append(
                FrameworkInfo(
                    name="FastAPI",
                    category="Backend Web Framework",
                    confidence=confidence,
                    indicators=fastapi_indicators[:4],
                )
            )
            detected_names.add("FastAPI")

        # Django
        django_indicators = []
        if "django" in py_deps:
            django_indicators.append("django declared in Python dependencies")
        if "manage.py" in root_files or any(f.path.endswith("/manage.py") for f in flat_files):
            django_indicators.append("Django manage.py entrypoint")
        if any("settings.py" in f.path.lower() for f in flat_files):
            django_indicators.append("Django settings.py configuration")
        if django_indicators and "Django" not in detected_names:
            confidence = "HIGH" if "django" in py_deps or "manage.py" in root_files else "MEDIUM"
            frameworks.append(
                FrameworkInfo(
                    name="Django",
                    category="Fullstack / Backend Framework",
                    confidence=confidence,
                    indicators=django_indicators[:4],
                )
            )
            detected_names.add("Django")

        # Flask
        flask_indicators = []
        if "flask" in py_deps:
            flask_indicators.append("flask declared in Python dependencies")
        for f in flat_files:
            if f.path.endswith(".py") and f.size < 50000:
                code = cls._read_file_safe(repo_dir / f.path, 5000)
                if "from flask import" in code or "Flask(__name__)" in code or "@app.route(" in code:
                    flask_indicators.append(f"Flask instance/routing in {f.path}")
                    break
        if flask_indicators and "Flask" not in detected_names:
            confidence = "HIGH" if "flask" in py_deps else "MEDIUM"
            frameworks.append(
                FrameworkInfo(
                    name="Flask",
                    category="Backend Web Framework",
                    confidence=confidence,
                    indicators=flask_indicators[:4],
                )
            )
            detected_names.add("Flask")

        # -------------------------------------------------------------
        # 3. JavaScript / TypeScript Framework Detection
        # -------------------------------------------------------------
        # React
        react_indicators = []
        if "react" in js_deps or "react" in js_dev_deps:
            react_indicators.append("react in package.json")
        if any(f.path.endswith(".tsx") or f.path.endswith(".jsx") for f in flat_files):
            react_indicators.append("JSX / TSX component files present")
        for f in flat_files:
            if (f.path.endswith(".tsx") or f.path.endswith(".jsx") or f.path.endswith(".ts") or f.path.endswith(".js")) and f.size < 50000:
                code = cls._read_file_safe(repo_dir / f.path, 5000)
                if "import React" in code or "from 'react'" in code or 'from "react"' in code:
                    react_indicators.append(f"React import in {f.path}")
                    break
        if react_indicators and "React" not in detected_names:
            confidence = "HIGH" if "react" in js_deps or "react" in js_dev_deps else "MEDIUM"
            frameworks.append(
                FrameworkInfo(
                    name="React",
                    category="Frontend UI Framework",
                    confidence=confidence,
                    indicators=react_indicators[:4],
                )
            )
            detected_names.add("React")

        # Next.js
        next_indicators = []
        if "next" in js_deps:
            next_indicators.append("next declared in package.json")
        if any("next.config" in f.path.lower() for f in flat_files):
            next_indicators.append("Next.js configuration file (next.config.*)")
        if (js_deps or js_dev_deps) and any(
            (f.path.startswith("app/") or "/app/" in f.path) and f.name.lower() in ["page.tsx", "page.jsx", "page.js", "layout.tsx", "layout.jsx", "layout.js"]
            for f in flat_files
        ):
            next_indicators.append("Next.js App Router structure (page/layout)")
        if (js_deps or js_dev_deps) and any(
            (f.path.startswith("pages/") or "/pages/" in f.path) and f.name.lower() in ["_app.tsx", "_app.jsx", "_app.js", "_document.tsx", "_document.jsx"]
            for f in flat_files
        ):
            next_indicators.append("Next.js Pages Router structure (_app/_document)")

        if next_indicators and "Next.js" not in detected_names:
            confidence = "HIGH" if "next" in js_deps or any("next.config" in f.path.lower() for f in flat_files) else "MEDIUM"
            frameworks.append(
                FrameworkInfo(
                    name="Next.js",
                    category="Fullstack React Framework",
                    confidence=confidence,
                    indicators=next_indicators[:4],
                )
            )
            detected_names.add("Next.js")

        # Express
        express_indicators = []
        if "express" in js_deps:
            express_indicators.append("express in package.json dependencies")
        for f in flat_files:
            if (f.path.endswith(".js") or f.path.endswith(".ts")) and f.size < 50000:
                code = cls._read_file_safe(repo_dir / f.path, 5000)
                if "require('express')" in code or 'from "express"' in code or "from 'express'" in code:
                    express_indicators.append(f"Express server instance in {f.path}")
                    break
        if express_indicators and "Express" not in detected_names:
            confidence = "HIGH" if "express" in js_deps else "MEDIUM"
            frameworks.append(
                FrameworkInfo(
                    name="Express",
                    category="Backend Web Framework",
                    confidence=confidence,
                    indicators=express_indicators[:4],
                )
            )
            detected_names.add("Express")

        # Node.js
        if pkg_json.exists() or any(f.name.lower() == "package.json" for f in flat_files):
            if "Node.js" not in detected_names:
                frameworks.append(
                    FrameworkInfo(
                        name="Node.js",
                        category="JavaScript Runtime",
                        confidence="HIGH",
                        indicators=["package.json configuration"],
                    )
                )
                detected_names.add("Node.js")

        return frameworks

    @classmethod
    def detect_infrastructure(cls, repo_dir: Path, flat_files: List[Any]) -> List[InfrastructureInfo]:
        infra_list: List[InfrastructureInfo] = []
        file_paths = [f.path for f in flat_files]
        file_paths_lower = {f.path.lower(): f.path for f in flat_files}

        # 1. Docker
        dockerfiles = [f.path for f in flat_files if f.name.lower().startswith("dockerfile") or f.name.lower().endswith(".dockerfile")]
        if dockerfiles:
            infra_list.append(
                InfrastructureInfo(
                    name="Docker",
                    type="Containerization",
                    files=dockerfiles,
                    details=f"Found {len(dockerfiles)} Dockerfile(s)",
                )
            )

        # 2. Docker Compose
        compose_files = [f.path for f in flat_files if f.name.lower() in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]]
        if compose_files:
            infra_list.append(
                InfrastructureInfo(
                    name="Docker Compose",
                    type="Multi-Container Orchestration",
                    files=compose_files,
                    details=f"Found {len(compose_files)} Compose configuration(s)",
                )
            )

        # 3. GitHub Actions
        gh_actions = [f.path for f in flat_files if ".github/workflows" in f.path.lower() and (f.path.endswith(".yml") or f.path.endswith(".yaml"))]
        if gh_actions:
            infra_list.append(
                InfrastructureInfo(
                    name="GitHub Actions",
                    type="CI/CD Workflows",
                    files=gh_actions,
                    details=f"Found {len(gh_actions)} workflow configuration(s)",
                )
            )

        # 4. Kubernetes Manifests
        k8s_files = []
        for f in flat_files:
            if (f.path.endswith(".yml") or f.path.endswith(".yaml")) and f.size < 50000:
                if "k8s" in f.path.lower() or "kubernetes" in f.path.lower() or "helm" in f.path.lower() or f.name.lower() == "chart.yaml":
                    k8s_files.append(f.path)
                else:
                    content = cls._read_file_safe(repo_dir / f.path, 2000)
                    if "apiversion:" in content.lower() and ("kind: deployment" in content.lower() or "kind: service" in content.lower() or "kind: ingress" in content.lower() or "kind: configmap" in content.lower()):
                        k8s_files.append(f.path)
        if k8s_files:
            infra_list.append(
                InfrastructureInfo(
                    name="Kubernetes",
                    type="Container Orchestration",
                    files=k8s_files[:10],
                    details=f"Found {len(k8s_files)} Kubernetes manifest(s)",
                )
            )

        # 5. Terraform (IaC)
        tf_files = [f.path for f in flat_files if f.path.endswith(".tf") or f.path.endswith(".tfvars")]
        if tf_files:
            infra_list.append(
                InfrastructureInfo(
                    name="Terraform",
                    type="Infrastructure as Code (IaC)",
                    files=tf_files[:10],
                    details=f"Found {len(tf_files)} Terraform configuration(s)",
                )
            )

        # 6. Environment Configuration Files
        env_files = [f.path for f in flat_files if f.name.lower().startswith(".env")]
        if env_files:
            infra_list.append(
                InfrastructureInfo(
                    name="Environment Config",
                    type="Configuration Management",
                    files=env_files,
                    details=f"Found {len(env_files)} environment file(s)",
                )
            )

        # 7. Database Migrations / ORM tools
        db_tool_files = []
        if any("alembic" in f.path.lower() for f in flat_files):
            db_tool_files.append("Alembic (SQLAlchemy)")
        if any("schema.prisma" in f.path.lower() for f in flat_files):
            db_tool_files.append("Prisma ORM")
        if any("schema.sql" in f.path.lower() for f in flat_files):
            db_tool_files.append("Raw SQL Schema")

        if db_tool_files:
            infra_list.append(
                InfrastructureInfo(
                    name="Database Schema / Migrations",
                    type="Database Tooling",
                    files=[f.path for f in flat_files if "alembic" in f.path.lower() or "prisma" in f.path.lower() or "schema.sql" in f.path.lower()][:5],
                    details=", ".join(db_tool_files),
                )
            )

        return infra_list
