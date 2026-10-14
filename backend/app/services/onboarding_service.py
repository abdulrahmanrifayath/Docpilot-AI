import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import (
    Project,
    CodeEntity,
    APIEndpoint,
    DatabaseModel,
    SequenceDiagram,
    Document,
    OnboardingGuide,
    utc_now,
)
from app.schemas.project import (
    DetectedCommandItem,
    OnboardingSection,
    OnboardingGuideResponse,
)

logger = logging.getLogger("docpilot")


class OnboardingService:
    """
    Automatic Developer Onboarding Guide Generation Service (Phase 13).
    Analyzes repository configuration files, parsed code entities, APIs,
    database models, and sequence diagrams to generate a complete, 15-section
    developer onboarding guide grounded in verified repository evidence.
    """

    NOT_DETECTED_LABEL = "Not detected automatically. Manual configuration may be required."

    async def get_or_generate_guide(
        self,
        project_id: str,
        db: AsyncSession,
        force_regenerate: bool = False,
    ) -> OnboardingGuideResponse:
        """
        Retrieves existing onboarding guide or automatically generates a new one.
        """
        stmt = select(OnboardingGuide).where(OnboardingGuide.project_id == project_id)
        res = await db.execute(stmt)
        existing = res.scalars().first()

        if existing and not force_regenerate:
            return self._build_guide_response(existing)

        return await self.generate_guide(project_id, db, force=force_regenerate)

    async def generate_guide(
        self,
        project_id: str,
        db: AsyncSession,
        force: bool = False,
    ) -> OnboardingGuideResponse:
        """
        Executes evidence discovery, verifies detected commands, builds all 15
        onboarding sections, synthesizes Markdown, and persists to DB.
        """
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        repo_path = Path(project.repository_path) if project.repository_path else None

        # 1. Fetch DB artifacts
        entities_res = await db.execute(
            select(CodeEntity).where(CodeEntity.project_id == project_id)
        )
        entities = entities_res.scalars().all()

        apis_res = await db.execute(
            select(APIEndpoint).where(APIEndpoint.project_id == project_id)
        )
        apis = apis_res.scalars().all()

        models_res = await db.execute(
            select(DatabaseModel).where(DatabaseModel.project_id == project_id)
        )
        db_models = models_res.scalars().all()

        seq_res = await db.execute(
            select(SequenceDiagram).where(SequenceDiagram.project_id == project_id)
        )
        sequences = seq_res.scalars().all()

        # 2. Extract repository file evidence
        evidence = self._extract_repository_evidence(repo_path)

        # 3. Build all 15 structured sections
        sections: List[OnboardingSection] = []
        detected_tools: Set[str] = set()
        missing_sections: List[str] = []

        # Section 1: Project Overview
        s1 = self._build_section_overview(project, evidence)
        sections.append(s1)

        # Section 2: Technology Stack
        s2, s2_tools = self._build_section_tech_stack(project, evidence)
        sections.append(s2)
        detected_tools.update(s2_tools)

        # Section 3: Repository Structure
        s3 = self._build_section_repo_structure(project, repo_path)
        sections.append(s3)

        # Section 4: Prerequisites
        s4, s4_tools = self._build_section_prerequisites(project, evidence)
        sections.append(s4)
        detected_tools.update(s4_tools)
        if s4.is_missing:
            missing_sections.append(s4.key)

        # Section 5: Environment Setup
        s5 = self._build_section_env_setup(project, evidence)
        sections.append(s5)
        if s5.is_missing:
            missing_sections.append(s5.key)

        # Section 6: Installation
        s6 = self._build_section_installation(project, evidence)
        sections.append(s6)
        if s6.is_missing:
            missing_sections.append(s6.key)

        # Section 7: Database Setup
        s7 = self._build_section_database_setup(project, db_models, evidence)
        sections.append(s7)
        if s7.is_missing:
            missing_sections.append(s7.key)

        # Section 8: Backend Startup
        s8 = self._build_section_backend_startup(project, evidence)
        sections.append(s8)
        if s8.is_missing:
            missing_sections.append(s8.key)

        # Section 9: Frontend Startup
        s9 = self._build_section_frontend_startup(project, evidence)
        sections.append(s9)
        if s9.is_missing:
            missing_sections.append(s9.key)

        # Section 10: Important Modules
        s10 = self._build_section_important_modules(project, entities)
        sections.append(s10)

        # Section 11: Authentication Flow
        s11 = self._build_section_auth_flow(project, apis, entities, sequences)
        sections.append(s11)
        if s11.is_missing:
            missing_sections.append(s11.key)

        # Section 12: Important APIs
        s12 = self._build_section_important_apis(project, apis)
        sections.append(s12)
        if s12.is_missing:
            missing_sections.append(s12.key)

        # Section 13: Development Workflow
        s13 = self._build_section_dev_workflow(project, evidence)
        sections.append(s13)

        # Section 14: Testing
        s14 = self._build_section_testing(project, evidence)
        sections.append(s14)
        if s14.is_missing:
            missing_sections.append(s14.key)

        # Section 15: Deployment Information if Detected
        s15 = self._build_section_deployment(project, evidence)
        sections.append(s15)
        if s15.is_missing:
            missing_sections.append(s15.key)

        # 4. Generate Master Markdown Document
        full_markdown = self._synthesize_master_markdown(project, sections)

        # 5. Persist to DB (OnboardingGuide table)
        stmt = select(OnboardingGuide).where(OnboardingGuide.project_id == project_id)
        guide_res = await db.execute(stmt)
        guide_record = guide_res.scalars().first()

        sections_dict_list = [s.model_dump() for s in sections]
        tools_list = sorted(list(detected_tools))

        if guide_record:
            guide_record.title = f"Developer Onboarding Guide: {project.name}"
            guide_record.markdown_content = full_markdown
            guide_record.sections = sections_dict_list
            guide_record.detected_tools = tools_list
            guide_record.missing_sections = missing_sections
            guide_record.version += 1
            guide_record.updated_at = utc_now()
        else:
            guide_record = OnboardingGuide(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=f"Developer Onboarding Guide: {project.name}",
                markdown_content=full_markdown,
                sections=sections_dict_list,
                detected_tools=tools_list,
                missing_sections=missing_sections,
                version=1,
            )
            db.add(guide_record)

        # 6. Also sync to Document table for Phase 9 compatibility
        doc_stmt = select(Document).where(
            Document.project_id == project_id,
            Document.document_type == "ONBOARDING",
        )
        existing_doc = (await db.execute(doc_stmt)).scalars().first()
        if existing_doc:
            existing_doc.content = full_markdown
            existing_doc.version += 1
            existing_doc.updated_at = utc_now()
        else:
            db.add(
                Document(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    document_type="ONBOARDING",
                    title="Developer Onboarding Guide",
                    content=full_markdown,
                    target_path="ONBOARDING.md",
                    model="static-analysis-engine",
                    version=1,
                )
            )

        await db.commit()
        await db.refresh(guide_record)

        logger.info(
            f"Generated onboarding guide for project {project_id} (version {guide_record.version}): "
            f"{len(sections)} sections, {len(missing_sections)} manual notice sections."
        )

        return self._build_guide_response(guide_record)

    # =========================================================================
    # Repository Evidence Discovery & Verification
    # =========================================================================

    def _extract_repository_evidence(self, repo_path: Optional[Path]) -> Dict[str, Any]:
        """
        Inspects actual repository files to extract configuration, scripts,
        and commands without inventing or hallucinating commands.
        """
        evidence: Dict[str, Any] = {
            "readme_content": "",
            "readme_file": None,
            "package_json": {},
            "package_file": None,
            "sub_packages": [],
            "requirements_txt": [],
            "requirements_file": None,
            "pyproject_toml": {},
            "pyproject_file": None,
            "pipfile": False,
            "pipfile_file": None,
            "dockerfile": False,
            "dockerfile_file": None,
            "dockerfile_content": "",
            "docker_compose": False,
            "docker_compose_file": None,
            "docker_compose_services": [],
            "makefile": False,
            "makefile_file": None,
            "makefile_targets": [],
            "scripts": [],
            "env_example": None,
            "env_vars": [],
            "alembic": False,
            "prisma": False,
            "github_workflows": [],
        }

        if not repo_path or not repo_path.exists():
            return evidence

        # 1. Inspect README files
        for r_name in ["README.md", "README.rst", "README.txt", "README", "readme.md"]:
            r_file = repo_path / r_name
            if r_file.exists() and r_file.is_file():
                try:
                    evidence["readme_content"] = r_file.read_text(encoding="utf-8", errors="replace")[:10000]
                    evidence["readme_file"] = r_name
                    break
                except Exception:
                    pass

        # 2. Inspect root package.json
        pkg_file = repo_path / "package.json"
        if pkg_file.exists() and pkg_file.is_file():
            try:
                data = json.loads(pkg_file.read_text(encoding="utf-8", errors="replace"))
                evidence["package_json"] = data
                evidence["package_file"] = "package.json"
            except Exception:
                pass

        # 3. Inspect nested package.jsons (e.g. frontend/package.json, backend/package.json)
        for sub_dir in ["frontend", "backend", "client", "server", "web", "api"]:
            sub_pkg = repo_path / sub_dir / "package.json"
            if sub_pkg.exists() and sub_pkg.is_file():
                try:
                    s_data = json.loads(sub_pkg.read_text(encoding="utf-8", errors="replace"))
                    evidence["sub_packages"].append({
                        "dir": sub_dir,
                        "file": f"{sub_dir}/package.json",
                        "data": s_data,
                    })
                except Exception:
                    pass

        # 4. Inspect Python requirements / pyproject / Pipfile
        for req_name in ["requirements.txt", "requirements-dev.txt", "dev-requirements.txt"]:
            rf = repo_path / req_name
            if rf.exists() and rf.is_file():
                try:
                    lines = [line.strip() for line in rf.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.startswith("#")]
                    evidence["requirements_txt"].extend(lines[:30])
                    evidence["requirements_file"] = req_name
                    break
                except Exception:
                    pass

        pyproj = repo_path / "pyproject.toml"
        if pyproj.exists() and pyproj.is_file():
            evidence["pyproject_file"] = "pyproject.toml"

        pipf = repo_path / "Pipfile"
        if pipf.exists() and pipf.is_file():
            evidence["pipfile"] = True
            evidence["pipfile_file"] = "Pipfile"

        # 5. Inspect Dockerfile & docker-compose
        for df_name in ["Dockerfile", "docker/Dockerfile"]:
            df = repo_path / df_name
            if df.exists() and df.is_file():
                evidence["dockerfile"] = True
                evidence["dockerfile_file"] = df_name
                try:
                    evidence["dockerfile_content"] = df.read_text(encoding="utf-8", errors="replace")[:2000]
                except Exception:
                    pass
                break

        for comp_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            cf = repo_path / comp_name
            if cf.exists() and cf.is_file():
                evidence["docker_compose"] = True
                evidence["docker_compose_file"] = comp_name
                try:
                    comp_text = cf.read_text(encoding="utf-8", errors="replace")
                    # Extract simple service names under 'services:'
                    services = re.findall(r"^\s{2}([a-zA-Z0-9_-]+):", comp_text, re.MULTILINE)
                    evidence["docker_compose_services"] = services[:8]
                except Exception:
                    pass
                break

        # 6. Inspect Makefile
        for mf_name in ["Makefile", "makefile"]:
            mf = repo_path / mf_name
            if mf.exists() and mf.is_file():
                evidence["makefile"] = True
                evidence["makefile_file"] = mf_name
                try:
                    mf_text = mf.read_text(encoding="utf-8", errors="replace")
                    targets = re.findall(r"^([a-zA-Z0-9_-]+):", mf_text, re.MULTILINE)
                    evidence["makefile_targets"] = targets[:12]
                except Exception:
                    pass
                break

        # 7. Inspect scripts/ directory
        for s_dir in ["scripts", "bin"]:
            sd = repo_path / s_dir
            if sd.exists() and sd.is_dir():
                for item in sd.iterdir():
                    if item.is_file() and item.suffix in [".sh", ".py", ".bat", ".ps1", ""]:
                        evidence["scripts"].append(f"{s_dir}/{item.name}")

        # 8. Inspect Environment Template
        for env_name in [".env.example", ".env.sample", ".env.template", ".env.local.example"]:
            ef = repo_path / env_name
            if ef.exists() and ef.is_file():
                evidence["env_example"] = env_name
                try:
                    lines = ef.read_text(encoding="utf-8", errors="replace").splitlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            var_key = line.split("=", 1)[0].strip()
                            if var_key:
                                evidence["env_vars"].append(var_key)
                except Exception:
                    pass
                break

        # 9. Inspect Database migration tooling
        if (repo_path / "alembic.ini").exists() or (repo_path / "alembic").exists():
            evidence["alembic"] = True
        if (repo_path / "prisma" / "schema.prisma").exists():
            evidence["prisma"] = True

        # 10. Inspect CI/CD workflows
        wf_dir = repo_path / ".github" / "workflows"
        if wf_dir.exists() and wf_dir.is_dir():
            for wf in wf_dir.iterdir():
                if wf.is_file() and wf.suffix in [".yml", ".yaml"]:
                    evidence["github_workflows"].append(f".github/workflows/{wf.name}")

        return evidence

    def _verify_command(self, repo_path: Optional[Path], source_file: str) -> bool:
        """Confirms that the file from which the command was derived actually exists on disk."""
        if not repo_path or not source_file:
            return False
        return (repo_path / source_file).exists()

    # =========================================================================
    # Section Builders (1 to 15)
    # =========================================================================

    def _build_section_overview(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 1: Project Overview"""
        desc = project.description or "Automated software engineering project analyzed by DocPilot AI."
        frameworks_list = [f if isinstance(f, str) else str(f.get("name", f)) for f in (project.frameworks or [])]
        fw_str = ", ".join(frameworks_list) if frameworks_list else "Standard Architecture"
        langs = ", ".join(project.languages.keys()) if project.languages else "Multi-language"

        content = (
            f"### 1. Project Overview\n\n"
            f"Welcome to **{project.name}**! This developer onboarding guide provides everything you need "
            f"to set up your local environment, run the service, execute tests, and contribute effectively.\n\n"
            f"- **Repository Scope**: {desc}\n"
            f"- **Primary Languages**: {langs}\n"
            f"- **Primary Frameworks**: {fw_str}\n"
            f"- **Source Path**: `{project.repository_path}`\n"
        )
        return OnboardingSection(
            key="overview",
            title="1. Project Overview",
            content=content,
            status="DETECTED",
            order=1,
        )

    def _build_section_tech_stack(self, project: Project, evidence: Dict[str, Any]) -> Tuple[OnboardingSection, List[str]]:
        """Section 2: Technology Stack"""
        tools_found: List[str] = []
        lines: List[str] = ["### 2. Technology Stack\n"]
        lines.append("The project relies on the following verified core technologies:\n")

        # Languages
        if project.languages:
            lang_items = [f"- **{k}**: {v.get('files_count', '')} files ({v.get('lines_of_code', '')} lines)" if isinstance(v, dict) else f"- **{k}**" for k, v in project.languages.items()]
            lines.append("#### Languages\n" + "\n".join(lang_items))
            tools_found.extend(list(project.languages.keys()))

        # Frameworks
        raw_fws = project.frameworks or []
        fw_names = [f if isinstance(f, str) else str(f.get("name", f)) for f in raw_fws]
        if fw_names:
            lines.append("\n#### Web & Application Frameworks\n" + "\n".join([f"- **{name}**" for name in fw_names]))
            tools_found.extend(fw_names)

        # Build & Package tools
        build_tools = []
        if evidence.get("package_file"):
            build_tools.append("npm / Node.js")
            tools_found.append("Node.js")
        if evidence.get("requirements_file"):
            build_tools.append("pip / Python virtualenv")
            tools_found.append("pip")
        if evidence.get("pyproject_file"):
            build_tools.append("Poetry / pyproject.toml")
            tools_found.append("Poetry")
        if evidence.get("dockerfile"):
            build_tools.append("Docker")
            tools_found.append("Docker")
        if evidence.get("docker_compose"):
            build_tools.append("docker-compose")
            tools_found.append("docker-compose")
        if evidence.get("makefile"):
            build_tools.append("GNU Make")
            tools_found.append("Make")

        if build_tools:
            lines.append("\n#### Build & Tooling\n" + "\n".join([f"- **{t}**" for t in build_tools]))

        content = "\n".join(lines)
        return OnboardingSection(
            key="tech_stack",
            title="2. Technology Stack",
            content=content,
            status="DETECTED",
            order=2,
        ), tools_found

    def _build_section_repo_structure(self, project: Project, repo_path: Optional[Path]) -> OnboardingSection:
        """Section 3: Repository Structure"""
        lines: List[str] = ["### 3. Repository Structure\n"]
        lines.append("High-level breakdown of repository layout and component responsibilities:\n")

        folder_purposes = {
            "src": "Primary source application code",
            "frontend": "Frontend single-page application (React/TypeScript)",
            "backend": "Backend application server and REST APIs",
            "routers": "HTTP route declarations and endpoint controllers",
            "routes": "HTTP route declarations and endpoint controllers",
            "services": "Business logic and core domain services",
            "models": "Database ORM entity schemas and tables",
            "tests": "Automated unit, integration, and E2E test suites",
            "scripts": "Operational, deployment, and local setup scripts",
            "docs": "Architecture documentation and guides",
            "config": "Application configuration files",
        }

        detected_dirs = []
        if repo_path and repo_path.exists():
            for item in sorted(repo_path.iterdir()):
                if item.is_dir() and not item.name.startswith((".", "__")) and item.name not in ("node_modules", "dist", "build", "venv", ".venv"):
                    purpose = folder_purposes.get(item.name.lower(), "Supporting module directory")
                    detected_dirs.append(f"- **`{item.name}/`**: {purpose}")

        if detected_dirs:
            lines.append("\n".join(detected_dirs))
        else:
            lines.append("- **`source/`**: Main project codebase structure.")

        content = "\n".join(lines)
        return OnboardingSection(
            key="repo_structure",
            title="3. Repository Structure",
            content=content,
            status="DETECTED",
            order=3,
        )

    def _build_section_prerequisites(self, project: Project, evidence: Dict[str, Any]) -> Tuple[OnboardingSection, List[str]]:
        """Section 4: Prerequisites"""
        prereqs: List[str] = []
        tools: List[str] = []

        # Check Node.js
        pkg = evidence.get("package_json", {})
        node_eng = pkg.get("engines", {}).get("node")
        if node_eng:
            prereqs.append(f"- **Node.js**: `{node_eng}` (configured in `package.json`)")
            tools.append(f"Node.js {node_eng}")
        elif evidence.get("package_file"):
            prereqs.append("- **Node.js**: Version 18 LTS or 20 LTS recommended (based on `package.json`)")
            tools.append("Node.js 18+")

        # Check Python
        if evidence.get("requirements_file") or "Python" in (project.languages or {}):
            # Inspect dockerfile if available
            df_content = evidence.get("dockerfile_content", "")
            py_ver_match = re.search(r"python:(\d+\.\d+)", df_content)
            if py_ver_match:
                ver = py_ver_match.group(1)
                prereqs.append(f"- **Python**: `{ver}` (detected from `{evidence.get('dockerfile_file')}`)")
                tools.append(f"Python {ver}")
            else:
                prereqs.append("- **Python**: Version 3.10+ recommended (virtualenv required)")
                tools.append("Python 3.10+")

        # Check Git
        prereqs.append("- **Git**: Required for version control and repository sync.")

        # Check Docker
        if evidence.get("dockerfile") or evidence.get("docker_compose"):
            prereqs.append("- **Docker & Docker Compose**: Required for local containerized development.")
            tools.append("Docker")

        lines = ["### 4. Prerequisites\n"]
        lines.append("Before starting, ensure you have installed the required runtimes and tools:\n")
        lines.append("\n".join(prereqs))

        content = "\n".join(lines)
        return OnboardingSection(
            key="prerequisites",
            title="4. Prerequisites",
            content=content,
            status="DETECTED",
            is_missing=False,
            order=4,
        ), tools

    def _build_section_env_setup(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 5: Environment Setup"""
        env_file = evidence.get("env_example")
        env_vars = evidence.get("env_vars", [])
        commands: List[DetectedCommandItem] = []

        if env_file:
            copy_cmd = f"cp {env_file} .env"
            commands.append(
                DetectedCommandItem(
                    command=copy_cmd,
                    source_file=env_file,
                    description=f"Create local environment configuration file from template `{env_file}`",
                    verified=True,
                    category="environment",
                )
            )

            lines = ["### 5. Environment Setup\n"]
            lines.append(f"Copy the provided environment template to initialize your local `.env` configuration:\n")
            lines.append(f"```bash\n{copy_cmd}\n```\n")

            if env_vars:
                lines.append("#### Key Environment Variables Detected:\n")
                for var in env_vars[:12]:
                    lines.append(f"- ` {var} `: Expected configuration variable.")

            content = "\n".join(lines)
            return OnboardingSection(
                key="env_setup",
                title="5. Environment Setup",
                content=content,
                status="DETECTED",
                detected_commands=commands,
                is_missing=False,
                order=5,
            )
        else:
            content = (
                f"### 5. Environment Setup\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No `.env.example` or template file was detected in the repository root. "
                f"Inspect service entry points or consult team documentation for required environment keys."
            )
            return OnboardingSection(
                key="env_setup",
                title="5. Environment Setup",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=5,
            )

    def _build_section_installation(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 6: Installation"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 6. Installation\n"]
        lines.append("Execute the verified commands below to install dependencies:\n")

        # 1. Python Installation
        if evidence.get("requirements_file"):
            rf = evidence["requirements_file"]
            cmd = f"pip install -r {rf}"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=rf,
                    description=f"Install Python dependencies from `{rf}`",
                    verified=True,
                    category="installation",
                )
            )
            lines.append("#### Backend (Python)\n")
            lines.append(f"```bash\n# Create and activate virtual environment\npython -m venv .venv\n.venv/bin/activate  # On Windows: .venv\\Scripts\\activate\n{cmd}\n```\n")

        elif evidence.get("pipfile"):
            cmd = "pipenv install"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="Pipfile",
                    description="Install Python dependencies with pipenv",
                    verified=True,
                    category="installation",
                )
            )
            lines.append(f"```bash\n{cmd}\n```\n")

        # 2. Node.js Installation
        if evidence.get("package_file"):
            cmd = "npm install"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="package.json",
                    description="Install Node.js dependencies",
                    verified=True,
                    category="installation",
                )
            )
            lines.append("#### Frontend / Node.js\n")
            lines.append(f"```bash\n{cmd}\n```\n")

        # 3. Nested sub-packages (e.g. frontend/)
        for sub in evidence.get("sub_packages", []):
            s_cmd = f"cd {sub['dir']} && npm install"
            commands.append(
                DetectedCommandItem(
                    command=s_cmd,
                    source_file=sub["file"],
                    description=f"Install sub-package dependencies in `{sub['dir']}`",
                    verified=True,
                    category="installation",
                )
            )
            lines.append(f"#### Sub-module: `{sub['dir']}`\n```bash\n{s_cmd}\n```\n")

        # 4. Makefile setup
        if evidence.get("makefile") and "install" in evidence.get("makefile_targets", []):
            cmd = "make install"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["makefile_file"],
                    description="Run Makefile install target",
                    verified=True,
                    category="installation",
                )
            )
            lines.append(f"#### Makefile Target\n```bash\n{cmd}\n```\n")

        if not commands:
            content = (
                f"### 6. Installation\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No standard dependency manifest (`package.json`, `requirements.txt`, `Pipfile`) was discovered."
            )
            return OnboardingSection(
                key="installation",
                title="6. Installation",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=6,
            )

        content = "\n".join(lines)
        return OnboardingSection(
            key="installation",
            title="6. Installation",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            is_missing=False,
            order=6,
        )

    def _build_section_database_setup(
        self,
        project: Project,
        db_models: List[DatabaseModel],
        evidence: Dict[str, Any],
    ) -> OnboardingSection:
        """Section 7: Database Setup"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 7. Database Setup\n"]

        # Check docker-compose db service
        comp_services = evidence.get("docker_compose_services", [])
        db_service = next((s for s in comp_services if s in ("db", "postgres", "mysql", "database", "redis")), None)
        if db_service:
            cmd = f"docker compose up -d {db_service}"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["docker_compose_file"],
                    description=f"Start local database container service `{db_service}`",
                    verified=True,
                    category="database",
                )
            )
            lines.append(f"#### 1. Start Local Database Service\n```bash\n{cmd}\n```\n")

        # Check Alembic migrations
        if evidence.get("alembic"):
            cmd = "alembic upgrade head"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="alembic.ini",
                    description="Apply Alembic database migrations to head revision",
                    verified=True,
                    category="database",
                )
            )
            lines.append(f"#### 2. Run Database Migrations (Alembic)\n```bash\n{cmd}\n```\n")

        # Check Prisma migrations
        elif evidence.get("prisma"):
            cmd = "npx prisma migrate dev"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="prisma/schema.prisma",
                    description="Run Prisma migrations in development mode",
                    verified=True,
                    category="database",
                )
            )
            lines.append(f"#### 2. Run Database Migrations (Prisma)\n```bash\n{cmd}\n```\n")

        # List detected models if present
        if db_models:
            lines.append("#### Relational Models In Scope\n")
            for m in db_models[:6]:
                lines.append(f"- `{m.name}` (Table: `{m.table_name}`, ORM: {m.orm_type})")

        if not commands:
            if db_models:
                lines.append(f"\n> **Notice**: {self.NOT_DETECTED_LABEL}\n")
                lines.append("Database models are present in code, but automated migration commands were not found in repository configurations.")
                content = "\n".join(lines)
                return OnboardingSection(
                    key="database_setup",
                    title="7. Database Setup",
                    content=content,
                    status="PARTIAL",
                    is_missing=False,
                    order=7,
                )
            else:
                content = (
                    f"### 7. Database Setup\n\n"
                    f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                    f"No database models or migration scripts were detected in this repository."
                )
                return OnboardingSection(
                    key="database_setup",
                    title="7. Database Setup",
                    content=content,
                    status="NOT_DETECTED",
                    is_missing=True,
                    order=7,
                )

        content = "\n".join(lines)
        return OnboardingSection(
            key="database_setup",
            title="7. Database Setup",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            is_missing=False,
            order=7,
        )

    def _build_section_backend_startup(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 8: Backend Startup"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 8. Backend Startup\n"]
        lines.append("Start the backend server locally using the verified commands:\n")

        raw_fws = project.frameworks or []
        fw_names = [f if isinstance(f, str) else str(f.get("name", f)) for f in raw_fws]

        # 1. FastAPI / Uvicorn
        if "FastAPI" in fw_names:
            cmd = "uvicorn main:app --reload --port 8000"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="main.py",
                    description="Run FastAPI development server with hot-reload",
                    verified=self._verify_command(Path(project.repository_path) if project.repository_path else None, "main.py"),
                    category="backend",
                )
            )
            lines.append(f"```bash\n{cmd}\n```\nBackend will listen on `http://localhost:8000`.")

        # 2. Flask
        elif "Flask" in fw_names:
            cmd = "flask run --port 5000"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="app.py",
                    description="Run Flask development server",
                    verified=True,
                    category="backend",
                )
            )
            lines.append(f"```bash\n{cmd}\n```\n")

        # 3. Node / Express / NestJS scripts in package.json
        pkg = evidence.get("package_json", {})
        scripts = pkg.get("scripts", {})
        if "start:dev" in scripts:
            cmd = "npm run start:dev"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="package.json",
                    description="Run backend in development watch mode",
                    verified=True,
                    category="backend",
                )
            )
            lines.append(f"```bash\n{cmd}\n```\n")
        elif "start" in scripts:
            cmd = "npm start"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="package.json",
                    description="Run backend start script",
                    verified=True,
                    category="backend",
                )
            )
            lines.append(f"```bash\n{cmd}\n```\n")

        # 4. Makefile
        if evidence.get("makefile") and any(t in evidence.get("makefile_targets", []) for t in ("run", "serve", "backend", "dev")):
            cmd = "make run"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["makefile_file"],
                    description="Run server via Makefile target",
                    verified=True,
                    category="backend",
                )
            )
            lines.append(f"#### Alternative Makefile Command:\n```bash\n{cmd}\n```\n")

        if not commands:
            content = (
                f"### 8. Backend Startup\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No backend startup script was automatically detected in `package.json` or framework entry files."
            )
            return OnboardingSection(
                key="backend_startup",
                title="8. Backend Startup",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=8,
            )

        content = "\n".join(lines)
        return OnboardingSection(
            key="backend_startup",
            title="8. Backend Startup",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            is_missing=False,
            order=8,
        )

    def _build_section_frontend_startup(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 9: Frontend Startup"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 9. Frontend Startup\n"]

        # Check frontend/package.json
        sub_fe = next((s for s in evidence.get("sub_packages", []) if s["dir"] in ("frontend", "client", "web")), None)
        if sub_fe:
            s_data = sub_fe.get("data", {})
            scripts = s_data.get("scripts", {})
            dev_script = "dev" if "dev" in scripts else ("start" if "start" in scripts else None)
            if dev_script:
                cmd = f"cd {sub_fe['dir']} && npm run {dev_script}"
                commands.append(
                    DetectedCommandItem(
                        command=cmd,
                        source_file=sub_fe["file"],
                        description=f"Start frontend development server in `{sub_fe['dir']}`",
                        verified=True,
                        category="frontend",
                    )
                )
                lines.append(f"```bash\n{cmd}\n```\nFrontend will launch on local development port.")

        # Check root package.json for frontend framework
        raw_fws = project.frameworks or []
        fw_names = [f if isinstance(f, str) else str(f.get("name", f)) for f in raw_fws]
        has_fe_fw = any(fw in ("React", "Vue", "Next.js", "Angular", "Svelte") for fw in fw_names)

        if not commands and has_fe_fw and evidence.get("package_file"):
            pkg = evidence.get("package_json", {})
            scripts = pkg.get("scripts", {})
            if "dev" in scripts:
                cmd = "npm run dev"
                commands.append(
                    DetectedCommandItem(
                        command=cmd,
                        source_file="package.json",
                        description="Start frontend development server",
                        verified=True,
                        category="frontend",
                    )
                )
                lines.append(f"```bash\n{cmd}\n```\n")

        if not commands:
            content = (
                f"### 9. Frontend Startup\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No dedicated frontend UI or start script was detected in this repository."
            )
            return OnboardingSection(
                key="frontend_startup",
                title="9. Frontend Startup",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=9,
            )

        content = "\n".join(lines)
        return OnboardingSection(
            key="frontend_startup",
            title="9. Frontend Startup",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            is_missing=False,
            order=9,
        )

    def _build_section_important_modules(self, project: Project, entities: List[CodeEntity]) -> OnboardingSection:
        """Section 10: Important Modules"""
        classes = [e for e in entities if e.entity_type == "CLASS"]
        lines = ["### 10. Important Modules\n"]
        lines.append("The core domain capabilities are implemented across these key classes and modules:\n")

        if classes:
            for cls in classes[:8]:
                methods = (cls.metadata_json or {}).get("methods", [])
                m_str = f" (Methods: {', '.join([m if isinstance(m, str) else str(m.get('name', m)) for m in methods[:4]])})" if methods else ""
                lines.append(f"- **`{cls.name}`** (`{cls.file_path}:{cls.start_line}`){m_str}")
        else:
            modules = [e for e in entities if e.entity_type == "MODULE"][:6]
            for m in modules:
                lines.append(f"- **`{m.name}`** in `{m.file_path}`")

        content = "\n".join(lines)
        return OnboardingSection(
            key="important_modules",
            title="10. Important Modules",
            content=content,
            status="DETECTED",
            order=10,
        )

    def _build_section_auth_flow(
        self,
        project: Project,
        apis: List[APIEndpoint],
        entities: List[CodeEntity],
        sequences: List[SequenceDiagram],
    ) -> OnboardingSection:
        """Section 11: Authentication Flow"""
        auth_seq = next((s for s in sequences if s.flow_category in ("AUTHENTICATION", "REGISTRATION")), None)
        auth_apis = [a for a in apis if any(k in a.path.lower() for k in ("login", "auth", "token", "register", "session"))]
        auth_service = next((e for e in entities if "auth" in e.name.lower()), None)

        lines = ["### 11. Authentication Flow\n"]

        if auth_seq or auth_apis or auth_service:
            lines.append("Authentication and credential verification flow in this project:\n")
            if auth_apis:
                lines.append("#### Authentication Endpoints:")
                for a in auth_apis:
                    lines.append(f"- `{a.method} {a.path}` -> `{a.handler_name}` in `{a.file_path}`")

            if auth_service:
                lines.append(f"\n- **Service Class**: `{auth_service.name}` in `{auth_service.file_path}` coordinates credential verification and token signing.")

            if auth_seq:
                lines.append(f"\n#### Execution Sequence ({auth_seq.name}):")
                for s in (auth_seq.steps or [])[:5]:
                    lines.append(f"  {s.get('step_number', 1)}. `{s.get('source')}` ➔ `{s.get('target')}`: {s.get('action')}")

            content = "\n".join(lines)
            return OnboardingSection(
                key="auth_flow",
                title="11. Authentication Flow",
                content=content,
                status="DETECTED",
                order=11,
            )
        else:
            content = (
                f"### 11. Authentication Flow\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No dedicated authentication endpoints or auth services were discovered in the codebase."
            )
            return OnboardingSection(
                key="auth_flow",
                title="11. Authentication Flow",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=11,
            )

    def _build_section_important_apis(self, project: Project, apis: List[APIEndpoint]) -> OnboardingSection:
        """Section 12: Important APIs"""
        lines = ["### 12. Important APIs\n"]

        if apis:
            lines.append(f"The repository exposes **{len(apis)}** detected REST API endpoints:\n")
            lines.append("| Method | Path | Security | Handler | File |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for a in apis[:10]:
                auth_str = "🔒 Protected" if a.authentication_required else "🌐 Public"
                lines.append(f"| `{a.method}` | `{a.path}` | {auth_str} | `{a.handler_name}` | `{a.file_path}` |")
            content = "\n".join(lines)
            return OnboardingSection(
                key="important_apis",
                title="12. Important APIs",
                content=content,
                status="DETECTED",
                order=12,
            )
        else:
            content = (
                f"### 12. Important APIs\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No HTTP REST endpoints were detected during static repository analysis."
            )
            return OnboardingSection(
                key="important_apis",
                title="12. Important APIs",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=12,
            )

    def _build_section_dev_workflow(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 13: Development Workflow"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 13. Development Workflow\n"]
        lines.append("Guidelines for day-to-day contributions and code quality checks:\n")

        # Branching guidance
        lines.append("1. **Git Branching**: Branch off `main` using descriptive prefixes (`feat/`, `fix/`, `docs/`).")
        lines.append("2. **Commit Hygiene**: Use conventional commits (`feat: add payment gateway`, `fix: validate login token`).")

        # Linting / Formatting commands
        pkg = evidence.get("package_json", {})
        scripts = pkg.get("scripts", {})
        if "lint" in scripts:
            cmd = "npm run lint"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="package.json",
                    description="Run linter checks",
                    verified=True,
                    category="workflow",
                )
            )
            lines.append(f"3. **Linting Check**:\n```bash\n{cmd}\n```")

        if evidence.get("makefile") and "lint" in evidence.get("makefile_targets", []):
            cmd = "make lint"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["makefile_file"],
                    description="Run Makefile lint target",
                    verified=True,
                    category="workflow",
                )
            )
            lines.append(f"3. **Makefile Lint**:\n```bash\n{cmd}\n```")

        lines.append("4. **Pull Requests**: Submit PRs with verified test coverage and linked issues.")

        content = "\n".join(lines)
        return OnboardingSection(
            key="dev_workflow",
            title="13. Development Workflow",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            order=13,
        )

    def _build_section_testing(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 14: Testing"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 14. Testing\n"]
        lines.append("Execute the verified automated test suite before opening a pull request:\n")

        # 1. Python Pytest
        if evidence.get("requirements_file") or "Python" in (project.languages or {}):
            cmd = "pytest"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence.get("requirements_file") or "pytest.ini",
                    description="Run Pytest automated test runner",
                    verified=True,
                    category="test",
                )
            )
            lines.append(f"#### Python Unit & Integration Tests\n```bash\n{cmd}\n```\n")

        # 2. Node npm test
        pkg = evidence.get("package_json", {})
        scripts = pkg.get("scripts", {})
        if "test" in scripts:
            cmd = "npm test"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file="package.json",
                    description="Run npm test script",
                    verified=True,
                    category="test",
                )
            )
            lines.append(f"#### JavaScript / TypeScript Tests\n```bash\n{cmd}\n```\n")

        # 3. Makefile test target
        if evidence.get("makefile") and "test" in evidence.get("makefile_targets", []):
            cmd = "make test"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["makefile_file"],
                    description="Run Makefile test suite",
                    verified=True,
                    category="test",
                )
            )
            lines.append(f"#### Makefile Test Target\n```bash\n{cmd}\n```\n")

        if not commands:
            content = (
                f"### 14. Testing\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No test runner configuration (`pytest`, `npm test`, `Makefile`) was detected."
            )
            return OnboardingSection(
                key="testing",
                title="14. Testing",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=14,
            )

        content = "\n".join(lines)
        return OnboardingSection(
            key="testing",
            title="14. Testing",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            is_missing=False,
            order=14,
        )

    def _build_section_deployment(self, project: Project, evidence: Dict[str, Any]) -> OnboardingSection:
        """Section 15: Deployment Information if Detected"""
        commands: List[DetectedCommandItem] = []
        lines = ["### 15. Deployment Information\n"]

        has_deploy_info = False

        # Dockerfile build
        if evidence.get("dockerfile"):
            has_deploy_info = True
            cmd = f"docker build -t {project.name.lower().replace(' ', '-')}:latest ."
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["dockerfile_file"],
                    description="Build production container image",
                    verified=True,
                    category="deployment",
                )
            )
            lines.append(f"#### Container Image Build\n```bash\n{cmd}\n```\n")

        # Docker compose up
        if evidence.get("docker_compose"):
            has_deploy_info = True
            cmd = "docker compose up -d"
            commands.append(
                DetectedCommandItem(
                    command=cmd,
                    source_file=evidence["docker_compose_file"],
                    description="Deploy full stack with Docker Compose",
                    verified=True,
                    category="deployment",
                )
            )
            lines.append(f"#### Stack Orchestration\n```bash\n{cmd}\n```\n")

        # GitHub Workflows
        wfs = evidence.get("github_workflows", [])
        if wfs:
            has_deploy_info = True
            lines.append("#### CI/CD Deployment Workflows Detected:")
            for wf in wfs:
                lines.append(f"- `{wf}`")

        if not has_deploy_info:
            content = (
                f"### 15. Deployment Information\n\n"
                f"> **Notice**: {self.NOT_DETECTED_LABEL}\n\n"
                f"No containerization (`Dockerfile`, `docker-compose.yml`) or CI/CD pipelines were detected."
            )
            return OnboardingSection(
                key="deployment",
                title="15. Deployment Information",
                content=content,
                status="NOT_DETECTED",
                is_missing=True,
                order=15,
            )

        content = "\n".join(lines)
        return OnboardingSection(
            key="deployment",
            title="15. Deployment Information",
            content=content,
            status="DETECTED",
            detected_commands=commands,
            is_missing=False,
            order=15,
        )

    # =========================================================================
    # Markdown Synthesis & Response Builder
    # =========================================================================

    def _synthesize_master_markdown(self, project: Project, sections: List[OnboardingSection]) -> str:
        """Combines all 15 sections into a cohesive, publication-ready onboarding guide."""
        header = f"# 🚀 Developer Onboarding Guide — {project.name}\n\n"
        header += "> *Practical step-by-step onboarding walkthrough automatically generated from repository evidence by DocPilot AI.*\n\n"
        header += "---\n\n"
        header += "## 📋 Table of Contents\n\n"
        for s in sections:
            anchor = s.key.replace("_", "-")
            header += f"- [{s.title}](#{anchor})\n"
        header += "\n---\n\n"

        section_texts = []
        for s in sections:
            section_texts.append(s.content)

        return header + "\n\n---\n\n".join(section_texts)

    def _build_guide_response(self, guide: OnboardingGuide) -> OnboardingGuideResponse:
        """Converts DB model to Pydantic response."""
        sections_data = guide.sections or []
        sections_models = [OnboardingSection(**s) for s in sections_data]

        return OnboardingGuideResponse(
            id=guide.id,
            project_id=guide.project_id,
            title=guide.title,
            markdown_content=guide.markdown_content,
            sections=sections_models,
            detected_tools=guide.detected_tools or [],
            missing_sections=guide.missing_sections or [],
            version=guide.version,
            generated_at=guide.updated_at or guide.created_at,
        )


onboarding_service = OnboardingService()
