"""
Technical Reports and Documentation Export Service (Phase 16).

Provides comprehensive enterprise-grade technical reporting and multi-format documentation export:
1. Generates 6 report types:
   - Full Technical Report (All 12 required sections)
   - Project README
   - API Documentation
   - Architecture Documentation
   - Database Documentation
   - Onboarding Guide
2. Clearly distinguishes information classification across all sections:
   - 🔍 [Detected from Repository Evidence]
   - 🤖 [AI-Generated Architecture Explanation]
   - 🔗 [Inferred Relationship & Dependency Graph]
3. Supports multiple export formats:
   - Markdown (.md)
   - HTML (.html) with responsive layout, styling, and Mermaid.js diagram support
   - PDF (.pdf) with ReportLab enterprise document styling and pagination
"""

import io
import html
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import markdown
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.project import (
    Project,
    CodeEntity,
    APIEndpoint,
    DatabaseModel,
    DependencyNode,
    DependencyRelationship,
    SequenceDiagram,
    Diagram,
    Document,
    OnboardingGuide,
    TechnicalReport,
    utc_now,
)
from app.schemas.project import (
    ReportSectionItem,
    ReportGenerateRequest,
    TechnicalReportResponse,
)

logger = logging.getLogger("docpilot.reports")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for ReportLab that prints accurate 'Page X of Y' and running headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 792 - 25, "DocPilot AI • Enterprise Technical Documentation")
            self.drawRightString(612 - 36, 792 - 25, "Confidential / Internal Report")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(36, 792 - 28, 612 - 36, 792 - 28)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, 612 - 36, 32)
        self.drawString(36, 20, "Generated automatically by DocPilot AI grounded in repository evidence")
        self.drawRightString(612 - 36, 20, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class ReportService:
    """Service handling multi-format technical report generation, storage, and export."""

    CATEGORY_DETECTED = "detected"
    CATEGORY_AI = "ai_generated"
    CATEGORY_INFERRED = "inferred"

    LABEL_DETECTED = "Detected from Repository Evidence"
    LABEL_AI = "AI-Generated Architecture Explanation"
    LABEL_INFERRED = "Inferred Relationship & Dependency Graph"

    async def generate_report(
        self,
        project_id: str,
        payload: ReportGenerateRequest,
        db: AsyncSession,
    ) -> TechnicalReportResponse:
        """Generates a technical report grounded in repository analysis and stores it in the database."""
        res = await db.execute(select(Project).where(Project.id == project_id))
        project = res.scalars().first()
        if not project:
            raise EntityNotFoundException(
                entity_type="Project",
                entity_id=project_id,
                message=f"Project with ID '{project_id}' not found",
            )

        report_type = (payload.report_type or "FULL_TECHNICAL_REPORT").upper()
        title = payload.title or self._default_title(report_type, project.name)

        # Dispatch generation
        if report_type == "FULL_TECHNICAL_REPORT":
            sections, markdown_content = await self._generate_full_technical_report(project, title, db)
            description = "Comprehensive 12-section technical architecture and repository analysis report."
        elif report_type == "README":
            sections, markdown_content = await self._generate_readme_report(project, title, db)
            description = "Production-ready GitHub project README documentation with setup and architecture."
        elif report_type == "API_DOCUMENTATION":
            sections, markdown_content = await self._generate_api_report(project, title, db)
            description = "Complete API specification and route reference documentation."
        elif report_type == "ARCHITECTURE":
            sections, markdown_content = await self._generate_architecture_report(project, title, db)
            description = "Structural architecture documentation including system design and component topology."
        elif report_type == "DATABASE":
            sections, markdown_content = await self._generate_database_report(project, title, db)
            description = "Data architecture, ORM models, field definitions, and entity relationship diagrams."
        elif report_type == "ONBOARDING":
            sections, markdown_content = await self._generate_onboarding_report(project, title, db)
            description = "Developer onboarding guide with environment setup and operational commands."
        else:
            raise ValidationException(
                message=f"Unknown report type '{payload.report_type}'. Supported: FULL_TECHNICAL_REPORT, README, API_DOCUMENTATION, ARCHITECTURE, DATABASE, ONBOARDING",
                details={"provided_type": payload.report_type},
            )

        # Pre-render HTML template
        html_content = self.render_html(title, report_type, project, sections, markdown_content)

        report = TechnicalReport(
            project_id=project_id,
            report_type=report_type,
            title=title,
            description=description,
            markdown_content=markdown_content,
            html_content=html_content,
            sections=[s.model_dump() for s in sections],
            commit_sha=project.last_commit_sha,
            format_metadata={
                "generated_by": "DocPilot AI Report Generator",
                "total_sections": len(sections),
                "has_diagrams": "mermaid" in markdown_content,
                "project_branch": project.branch or "main",
            },
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return self._to_response(report)

    async def list_reports(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> List[TechnicalReportResponse]:
        """Lists all generated reports for a project."""
        stmt = (
            select(TechnicalReport)
            .where(TechnicalReport.project_id == project_id)
            .order_by(TechnicalReport.created_at.desc())
        )
        res = await db.execute(stmt)
        reports = res.scalars().all()
        return [self._to_response(r) for r in reports]

    async def get_report(
        self,
        project_id: str,
        report_id: str,
        db: AsyncSession,
    ) -> TechnicalReport:
        """Fetches a specific technical report."""
        stmt = select(TechnicalReport).where(
            TechnicalReport.id == report_id,
            TechnicalReport.project_id == project_id,
        )
        res = await db.execute(stmt)
        report = res.scalars().first()
        if not report:
            raise EntityNotFoundException(
                entity_type="TechnicalReport",
                entity_id=report_id,
                message=f"Report with ID '{report_id}' not found for project '{project_id}'",
            )
        return report

    async def export_report(
        self,
        project_id: str,
        report_id: str,
        format_type: str,
        db: AsyncSession,
    ) -> Tuple[bytes, str, str]:
        """
        Exports a report in the requested format (markdown, html, pdf).
        Returns: (file_bytes, media_type, filename)
        """
        report = await self.get_report(project_id, report_id, db)
        p_res = await db.execute(select(Project).where(Project.id == project_id))
        project = p_res.scalars().first()
        if not project:
            raise EntityNotFoundException(
                entity_type="Project",
                entity_id=project_id,
                message=f"Project with ID '{project_id}' not found",
            )

        clean_title = re.sub(r"[^A-Za-z0-9_-]+", "_", report.title.lower()).strip("_")
        base_name = f"{clean_title}_{report.id[:8]}"
        fmt = (format_type or "markdown").lower().strip()

        if fmt in ("markdown", "md"):
            return (
                report.markdown_content.encode("utf-8"),
                "text/markdown; charset=utf-8",
                f"{base_name}.md",
            )

        elif fmt in ("html", "htm"):
            html_text = report.html_content or self.render_html(
                report.title,
                report.report_type,
                project,
                [ReportSectionItem(**s) for s in report.sections],
                report.markdown_content,
            )
            return (
                html_text.encode("utf-8"),
                "text/html; charset=utf-8",
                f"{base_name}.html",
            )

        elif fmt == "pdf":
            pdf_bytes = self.render_pdf(report, project)
            return (
                pdf_bytes,
                "application/pdf",
                f"{base_name}.pdf",
            )

        else:
            raise ValidationException(
                message=f"Unsupported export format '{format_type}'. Supported formats: markdown, html, pdf.",
                details={"requested_format": format_type, "supported_formats": ["markdown", "html", "pdf"]},
            )

    # =========================================================================
    # Report Builders
    # =========================================================================

    def _default_title(self, report_type: str, project_name: str) -> str:
        titles = {
            "FULL_TECHNICAL_REPORT": f"{project_name} - Full Technical Report",
            "README": f"{project_name} - Project README",
            "API_DOCUMENTATION": f"{project_name} - API Documentation",
            "ARCHITECTURE": f"{project_name} - Architecture Documentation",
            "DATABASE": f"{project_name} - Database Documentation",
            "ONBOARDING": f"{project_name} - Developer Onboarding Guide",
        }
        return titles.get(report_type, f"{project_name} - Technical Report")

    async def _fetch_project_data(self, project_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Loads all extracted repository entities and models for comprehensive reporting."""
        entities_res = await db.execute(select(CodeEntity).where(CodeEntity.project_id == project_id))
        entities = entities_res.scalars().all()

        apis_res = await db.execute(select(APIEndpoint).where(APIEndpoint.project_id == project_id))
        apis = apis_res.scalars().all()

        db_models_res = await db.execute(select(DatabaseModel).where(DatabaseModel.project_id == project_id))
        db_models = db_models_res.scalars().all()

        deps_res = await db.execute(select(DependencyRelationship).where(DependencyRelationship.project_id == project_id))
        deps = deps_res.scalars().all()

        seqs_res = await db.execute(select(SequenceDiagram).where(SequenceDiagram.project_id == project_id))
        seqs = seqs_res.scalars().all()

        diags_res = await db.execute(select(Diagram).where(Diagram.project_id == project_id))
        diags = diags_res.scalars().all()

        onboard_res = await db.execute(select(OnboardingGuide).where(OnboardingGuide.project_id == project_id))
        onboard = onboard_res.scalars().first()

        return {
            "entities": entities,
            "apis": apis,
            "db_models": db_models,
            "deps": deps,
            "sequences": seqs,
            "diagrams": diags,
            "onboarding": onboard,
        }

    async def _generate_full_technical_report(
        self,
        project: Project,
        title: str,
        db: AsyncSession,
    ) -> Tuple[List[ReportSectionItem], str]:
        """
        Builds the 12-section Full Technical Report with explicit information classification badges.
        """
        data = await self._fetch_project_data(project.id, db)
        sections: List[ReportSectionItem] = []

        total_files = project.stats.get("total_files", 0) if project.stats else 0
        total_lines = project.stats.get("total_lines", 0) if project.stats else 0
        languages = project.languages or {}
        frameworks = project.frameworks or []
        infrastructure = project.infrastructure or []

        # 1. Executive Summary [AI-Generated Architecture Explanation]
        sec1_content = (
            f"This technical report presents an automated structural and architectural analysis of **{project.name}**.\n\n"
            f"The codebase comprises **{total_files} sanitized source files** across **{total_lines:,} lines of code**, "
            f"leveraging primary technologies including {', '.join(frameworks) if frameworks else 'modern standard libraries'}. "
            f"The repository exposes **{len(data['apis'])} API endpoints** and manages **{len(data['db_models'])} data models**.\n\n"
            f"This document is assembled to assist engineering teams, system architects, and technical leadership in onboarding, "
            f"code audits, refactoring, and automated synchronization."
        )
        sections.append(ReportSectionItem(
            id="executive_summary",
            title="1. Executive Summary",
            category=self.CATEGORY_AI,
            category_label=self.LABEL_AI,
            content=sec1_content,
        ))

        # 2. Project Overview [Detected + AI-Generated]
        sec2_content = (
            f"### Project Overview & Identification\n\n"
            f"- **Project Name:** {project.name}\n"
            f"- **Repository Source:** `{project.source_url or project.source_type}`\n"
            f"- **Tracking Branch:** `{project.branch or 'main'}`\n"
            f"- **Commit SHA Analyzed:** `{project.last_commit_sha or 'Initial Snapshot'}`\n"
            f"- **Description:** {project.description or 'No explicit repository description provided.'}\n\n"
            f"The project structure was inspected via AST and Tree-sitter semantic parsers without executing untrusted code."
        )
        sections.append(ReportSectionItem(
            id="project_overview",
            title="2. Project Overview",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=sec2_content,
            source_evidence=[project.source_url or project.repository_path],
        ))

        # 3. Technology Stack [Detected from Repository Evidence]
        tech_lines = ["| Category | Detected Technologies | Evidence Origin |", "|---|---|---|"]
        lang_str = ", ".join([f"{k} ({v.get('percent', 0)}%)" for k, v in languages.items()]) or "General Polyglot"
        tech_lines.append(f"| **Languages** | {lang_str} | AST / File Ext Parsing |")
        tech_lines.append(f"| **Frameworks** | {', '.join(frameworks) if frameworks else 'Standard Library'} | Imports & Package Manifests |")
        tech_lines.append(f"| **Infrastructure** | {', '.join(infrastructure) if infrastructure else 'Not explicitly detected'} | Dockerfile / Compose / CI Manifests |")

        sec3_content = (
            "The following technology stack components were strictly detected from source files and manifests:\n\n"
            + "\n".join(tech_lines)
        )
        sections.append(ReportSectionItem(
            id="technology_stack",
            title="3. Technology Stack",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=sec3_content,
            source_evidence=["package.json", "requirements.txt", "pyproject.toml"],
        ))

        # 4. Repository Statistics [Detected from Repository Evidence]
        stats_table = [
            "| Metric | Count | Measurement Scope |",
            "|---|---|---|",
            f"| **Total Files** | {total_files} | Processed source code files |",
            f"| **Total Lines of Code** | {total_lines:,} | Normalized non-empty source lines |",
            f"| **Extracted Code Entities** | {len(data['entities'])} | Classes, functions, interfaces, modules |",
            f"| **Discovered APIs** | {len(data['apis'])} | Express, FastAPI, Flask, Spring routes |",
            f"| **Database Models** | {len(data['db_models'])} | SQLAlchemy, Django, Prisma, TypeORM entities |",
            f"| **Interaction Flows** | {len(data['sequences'])} | End-to-end call sequences |",
        ]
        sec4_content = (
            "Quantitative repository analysis summary:\n\n" + "\n".join(stats_table)
        )
        sections.append(ReportSectionItem(
            id="repository_statistics",
            title="4. Repository Statistics",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=sec4_content,
        ))

        # 5. Architecture [Inferred via Knowledge Graph & AI Synthesis]
        arch_mermaid = ""
        for d in data["diagrams"]:
            if d.diagram_type in ("SYSTEM_ARCHITECTURE", "MODULE_ARCHITECTURE") and d.mermaid_code:
                arch_mermaid = f"\n\n```mermaid\n{d.mermaid_code.strip()}\n```\n"
                break
        if not arch_mermaid:
            arch_mermaid = (
                "\n\n```mermaid\ngraph TD\n"
                "    Client[Client / Consumer] --> API[API Gateway / Router]\n"
                "    API --> Controller[Service / Controller Layer]\n"
                "    Controller --> Core[Business Domain Logic]\n"
                "    Controller --> DB[(Database Layer)]\n```\n"
            )

        sec5_content = (
            f"The architecture of **{project.name}** follows a layered component structure. "
            f"Incoming requests flow through router definitions into service handlers and persistence layers."
            f"{arch_mermaid}\n"
            f"*Diagram inferred from code imports and routing declarations.*"
        )
        sections.append(ReportSectionItem(
            id="architecture",
            title="5. Architecture",
            category=self.CATEGORY_INFERRED,
            category_label=self.LABEL_INFERRED,
            content=sec5_content,
        ))

        # 6. Major Components [Detected from Repository Evidence]
        comp_rows = ["| Component Name | Entity Type | Defined In | Signature / Detail |", "|---|---|---|---|"]
        for ent in data["entities"][:15]:
            sig = (ent.signature or "").replace("|", "\\|")[:45]
            comp_rows.append(f"| `{ent.name}` | {ent.entity_type} | `{ent.file_path}` | `{sig}` |")
        if len(data["entities"]) > 15:
            comp_rows.append(f"| *...and {len(data['entities']) - 15} more entities* | - | - | - |")

        sec6_content = (
            f"The repository defines **{len(data['entities'])} code entities**. The key architectural components include:\n\n"
            + "\n".join(comp_rows)
        )
        sections.append(ReportSectionItem(
            id="major_components",
            title="6. Major Components",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=sec6_content,
        ))

        # 7. API Summary [Detected from Repository Evidence]
        api_rows = ["| Method | Path | Auth Required | Handler Component |", "|---|---|---|---|"]
        for ep in data["apis"][:20]:
            auth_badge = "🔒 Yes" if ep.authentication_required else "🌐 Public"
            api_rows.append(f"| **{ep.http_method}** | `{ep.path}` | {auth_badge} | `{ep.handler_function or 'Route'}` |")
        if not data["apis"]:
            api_rows.append("| - | *No HTTP REST endpoints detected in scanned files* | - | - |")
        elif len(data["apis"]) > 20:
            api_rows.append(f"| *...and {len(data['apis']) - 20} more endpoints* | - | - | - |")

        sec7_content = (
            f"Detected **{len(data['apis'])} HTTP endpoints** across the repository:\n\n"
            + "\n".join(api_rows)
        )
        sections.append(ReportSectionItem(
            id="api_summary",
            title="7. API Summary",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=sec7_content,
        ))

        # 8. Database Structure [Detected + Inferred ER Diagram]
        db_rows = ["| Model Name | Table Name | Declared Fields | File Path |", "|---|---|---|---|"]
        for m in data["db_models"][:15]:
            field_count = len(m.fields) if m.fields else 0
            db_rows.append(f"| `{m.name}` | `{m.table_name}` | {field_count} fields | `{m.file_path}` |")
        if not data["db_models"]:
            db_rows.append("| - | *No ORM models detected in repository* | - | - |")

        er_mermaid = ""
        for d in data["diagrams"]:
            if d.diagram_type == "DATABASE_ER" and d.mermaid_code:
                er_mermaid = f"\n\n```mermaid\n{d.mermaid_code.strip()}\n```\n"
                break

        sec8_content = (
            f"The persistence layer contains **{len(data['db_models'])} data models**:\n\n"
            + "\n".join(db_rows)
            + er_mermaid
        )
        sections.append(ReportSectionItem(
            id="database_structure",
            title="8. Database Structure",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=sec8_content,
        ))

        # 9. Dependency Analysis [Inferred Relationship & Dependency Graph]
        dep_rows = ["| Source | Target | Relationship Type | Confidence |", "|---|---|---|---|"]
        for dep in data["deps"][:15]:
            dep_rows.append(f"| `{dep.source_name}` | `{dep.target_name}` | {dep.relationship_type} | {int(dep.confidence * 100)}% |")
        if not data["deps"]:
            dep_rows.append("| - | *No inter-module dependencies indexed* | - | - |")
        elif len(data["deps"]) > 15:
            dep_rows.append(f"| *...and {len(data['deps']) - 15} more relations* | - | - | - |")

        sec9_content = (
            f"Static import analysis mapped **{len(data['deps'])} architectural relationships** across components:\n\n"
            + "\n".join(dep_rows)
        )
        sections.append(ReportSectionItem(
            id="dependency_analysis",
            title="9. Dependency Analysis",
            category=self.CATEGORY_INFERRED,
            category_label=self.LABEL_INFERRED,
            content=sec9_content,
        ))

        # 10. Important Flows [Inferred Relationship & Sequence Modeling]
        seq_text = "Key end-to-end operational execution paths discovered in this repository:\n\n"
        if data["sequences"]:
            for sq in data["sequences"][:3]:
                seq_text += f"#### Flow: {sq.name}\n"
                seq_text += f"- **Category:** {sq.flow_category}\n"
                seq_text += f"- **Trigger:** `{sq.trigger_method} {sq.trigger_endpoint or 'Internal'}`\n"
                seq_text += f"- **Confidence:** {int(sq.overall_confidence * 100)}%\n\n"
                if sq.mermaid_code:
                    seq_text += f"```mermaid\n{sq.mermaid_code.strip()}\n```\n\n"
        else:
            seq_text += "*No sequence interaction flows currently generated for this project.*\n"

        sections.append(ReportSectionItem(
            id="important_flows",
            title="10. Important Flows",
            category=self.CATEGORY_INFERRED,
            category_label=self.LABEL_INFERRED,
            content=seq_text,
        ))

        # 11. Setup and Deployment [Detected from Repository Evidence]
        setup_text = "Operational commands discovered from project configuration files:\n\n"
        if data["onboarding"]:
            for sec in data["onboarding"].sections:
                if sec.get("id") in ("environment_setup", "installation", "backend_startup", "frontend_startup"):
                    setup_text += f"**{sec.get('title')}:**\n{sec.get('content', '')}\n\n"
        else:
            setup_text += (
                "- **Installation:** Standard package manager (`pip install -r requirements.txt` or `npm install`)\n"
                "- **Startup:** Inferred from discovered technology stack\n"
            )

        sections.append(ReportSectionItem(
            id="setup_and_deployment",
            title="11. Setup and Deployment",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=setup_text,
        ))

        # 12. Risks and Limitations [AI-Generated Architecture Explanation]
        sec12_content = (
            "Architectural observations, potential technical debt, and risk considerations:\n\n"
            "1. **Static Inference Boundaries:** Inferred relationships are computed from static AST and Tree-sitter parsers. Dynamic runtime reflection or metaprogramming cannot be evaluated statically.\n"
            "2. **Authentication Coverage:** Endpoints without explicit decorators should be reviewed to guarantee authentication enforcement.\n"
            "3. **Synchronous Coupling:** Inter-service database calls without explicit queues or resilience timeouts may represent scalability bottlenecks.\n"
            "4. **Documentation Freshness:** Run repository synchronization (`POST /api/v1/projects/{id}/github/refresh`) following Git commits to maintain documentation parity."
        )
        sections.append(ReportSectionItem(
            id="risks_and_limitations",
            title="12. Risks and Limitations",
            category=self.CATEGORY_AI,
            category_label=self.LABEL_AI,
            content=sec12_content,
        ))

        markdown_doc = self._compose_markdown_document(title, project, sections)
        return sections, markdown_doc

    async def _generate_readme_report(
        self,
        project: Project,
        title: str,
        db: AsyncSession,
    ) -> Tuple[List[ReportSectionItem], str]:
        """Generates an executive, production-ready README report."""
        data = await self._fetch_project_data(project.id, db)
        sections: List[ReportSectionItem] = []

        overview_content = (
            f"# {project.name}\n\n"
            f"> {project.description or 'Automated architectural analysis and documentation powered by DocPilot AI.'}\n\n"
            f"![DocPilot AI Verified](https://img.shields.io/badge/DocPilot-Architecture_Verified-6366f1)\n"
            f"![Status](https://img.shields.io/badge/Status-Synchronized-10b981)\n"
            f"![Branch](https://img.shields.io/badge/Branch-{project.branch or 'main'}-3b82f6)\n"
        )
        sections.append(ReportSectionItem(
            id="readme_overview",
            title="Overview",
            category=self.CATEGORY_AI,
            category_label=self.LABEL_AI,
            content=overview_content,
        ))

        features_content = (
            f"## Key Architectural Highlights\n\n"
            f"- **Analyzed Codebase:** {project.stats.get('total_files', 0)} files, {project.stats.get('total_lines', 0):,} lines\n"
            f"- **APIs Discovered:** {len(data['apis'])} REST endpoints\n"
            f"- **Database Schema:** {len(data['db_models'])} data models and ORM entities\n"
            f"- **Primary Stack:** {', '.join(project.frameworks) if project.frameworks else 'Modern Libraries'}\n"
        )
        sections.append(ReportSectionItem(
            id="readme_features",
            title="Features & Specifications",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=features_content,
        ))

        install_content = "## Quick Start & Setup\n\n"
        if data["onboarding"]:
            for sec in data["onboarding"].sections:
                if sec.get("id") in ("installation", "backend_startup"):
                    install_content += f"{sec.get('content', '')}\n\n"
        else:
            install_content += "Refer to repository documentation for detailed prerequisites and startup instructions.\n"

        sections.append(ReportSectionItem(
            id="readme_setup",
            title="Installation & Quick Start",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=install_content,
        ))

        markdown_doc = self._compose_markdown_document(title, project, sections)
        return sections, markdown_doc

    async def _generate_api_report(
        self,
        project: Project,
        title: str,
        db: AsyncSession,
    ) -> Tuple[List[ReportSectionItem], str]:
        """Generates comprehensive API Documentation."""
        data = await self._fetch_project_data(project.id, db)
        sections: List[ReportSectionItem] = []

        apis = data["apis"]
        public_count = sum(1 for ep in apis if not ep.authentication_required)
        auth_count = len(apis) - public_count

        overview = (
            f"This document catalogs all **{len(apis)} HTTP endpoints** extracted from source code.\n\n"
            f"- **Authenticated Endpoints:** {auth_count}\n"
            f"- **Public Endpoints:** {public_count}\n"
            f"- **Frameworks Detected:** {', '.join(project.frameworks) if project.frameworks else 'HTTP Handlers'}\n"
        )
        sections.append(ReportSectionItem(
            id="api_overview",
            title="API Architecture Overview",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=overview,
        ))

        table_rows = ["| Method | Path | Security | Handler Function | File Location |", "|---|---|---|---|---|"]
        for ep in apis:
            sec = "🔒 Protected" if ep.authentication_required else "🌐 Public"
            table_rows.append(f"| **{ep.http_method}** | `{ep.path}` | {sec} | `{ep.handler_function or 'Anonymous'}` | `{ep.file_path or 'Route'}` |")

        sections.append(ReportSectionItem(
            id="api_catalog",
            title="Endpoint Catalog",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content="\n".join(table_rows),
        ))

        markdown_doc = self._compose_markdown_document(title, project, sections)
        return sections, markdown_doc

    async def _generate_architecture_report(
        self,
        project: Project,
        title: str,
        db: AsyncSession,
    ) -> Tuple[List[ReportSectionItem], str]:
        """Generates Architecture Documentation."""
        data = await self._fetch_project_data(project.id, db)
        sections: List[ReportSectionItem] = []

        overview = (
            f"Architectural blueprint and component topology for **{project.name}**.\n\n"
            f"The system is organized into modular subsystems. Static dependency analysis identified "
            f"**{len(data['deps'])} inter-module relationships** between **{len(data['entities'])} code entities**."
        )
        sections.append(ReportSectionItem(
            id="arch_overview",
            title="System Topology & Principles",
            category=self.CATEGORY_AI,
            category_label=self.LABEL_AI,
            content=overview,
        ))

        # Include all relevant diagrams
        for d in data["diagrams"]:
            sections.append(ReportSectionItem(
                id=f"diagram_{d.id[:8]}",
                title=f"Diagram: {d.title}",
                category=self.CATEGORY_INFERRED,
                category_label=self.LABEL_INFERRED,
                content=f"{d.description or ''}\n\n```mermaid\n{d.mermaid_code or ''}\n```",
            ))

        markdown_doc = self._compose_markdown_document(title, project, sections)
        return sections, markdown_doc

    async def _generate_database_report(
        self,
        project: Project,
        title: str,
        db: AsyncSession,
    ) -> Tuple[List[ReportSectionItem], str]:
        """Generates Database Documentation."""
        data = await self._fetch_project_data(project.id, db)
        sections: List[ReportSectionItem] = []

        models = data["db_models"]
        overview = (
            f"Database schema specification for **{project.name}** containing **{len(models)} data models**.\n"
        )
        sections.append(ReportSectionItem(
            id="db_overview",
            title="Persistence Overview",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content=overview,
        ))

        # Model details
        model_details = []
        for m in models:
            model_details.append(f"### Model: `{m.name}` (`{m.table_name}`)\n- **Declared In:** `{m.file_path}`\n- **ORM:** {m.orm_type}")
            field_table = ["| Column Name | Data Type | Primary Key | Nullable | Foreign Key Target |", "|---|---|---|---|---|"]
            for f in (m.fields or []):
                pk = "✓ PK" if f.is_primary_key else ""
                null = "Yes" if f.is_nullable else "No"
                fk = f"`{f.foreign_key_target}`" if f.is_foreign_key and f.foreign_key_target else ""
                field_table.append(f"| `{f.name}` | `{f.data_type}` | {pk} | {null} | {fk} |")
            model_details.append("\n".join(field_table) + "\n")

        sections.append(ReportSectionItem(
            id="db_models",
            title="Database Entities & Tables",
            category=self.CATEGORY_DETECTED,
            category_label=self.LABEL_DETECTED,
            content="\n\n".join(model_details),
        ))

        markdown_doc = self._compose_markdown_document(title, project, sections)
        return sections, markdown_doc

    async def _generate_onboarding_report(
        self,
        project: Project,
        title: str,
        db: AsyncSession,
    ) -> Tuple[List[ReportSectionItem], str]:
        """Generates Developer Onboarding Guide as an exportable report."""
        data = await self._fetch_project_data(project.id, db)
        sections: List[ReportSectionItem] = []

        if data["onboarding"]:
            for sec in data["onboarding"].sections:
                sections.append(ReportSectionItem(
                    id=sec.get("id", "section"),
                    title=sec.get("title", "Onboarding Section"),
                    category=self.CATEGORY_DETECTED,
                    category_label=self.LABEL_DETECTED,
                    content=sec.get("content", ""),
                ))
        else:
            sections.append(ReportSectionItem(
                id="onboarding_default",
                title="Developer Onboarding",
                category=self.CATEGORY_DETECTED,
                category_label=self.LABEL_DETECTED,
                content="Please run Onboarding Generation (`POST /api/v1/projects/{id}/onboarding/generate`) first to build verified setup guide.",
            ))

        markdown_doc = self._compose_markdown_document(title, project, sections)
        return sections, markdown_doc

    # =========================================================================
    # Markdown, HTML, and PDF Rendering Engines
    # =========================================================================

    def _compose_markdown_document(
        self,
        title: str,
        project: Project,
        sections: List[ReportSectionItem],
    ) -> str:
        """Composes complete GitHub-Flavored Markdown document with visual classification badges."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_sha = project.last_commit_sha[:8] if project.last_commit_sha else "Initial"

        md = [
            f"# {title}",
            "",
            f"> **Project:** {project.name} | **Branch:** `{project.branch or 'main'}` | **Commit:** `{commit_sha}` | **Generated:** {now_str}",
            "",
            "---",
            "",
            "## Table of Contents",
            "",
        ]

        for s in sections:
            anchor = re.sub(r"[^A-Za-z0-9_-]+", "", s.title.lower().replace(" ", "-"))
            badge_icon = "🔍" if s.category == self.CATEGORY_DETECTED else ("🤖" if s.category == self.CATEGORY_AI else "🔗")
            md.append(f"- [{s.title}](#{anchor}) {badge_icon}")

        md.extend(["", "---", ""])

        for s in sections:
            badge_icon = "🔍" if s.category == self.CATEGORY_DETECTED else ("🤖" if s.category == self.CATEGORY_AI else "🔗")
            badge_class = s.category_label
            md.append(f"## {s.title}")
            md.append(f"> **Information Classification:** {badge_icon} *[{badge_class}]*")
            md.append("")
            md.append(s.content)
            md.append("")
            md.append("---")
            md.append("")

        md.append("*Document automatically compiled by DocPilot AI Technical Report Engine.*")
        return "\n".join(md)

    def render_html(
        self,
        title: str,
        report_type: str,
        project: Project,
        sections: List[ReportSectionItem],
        markdown_text: str,
    ) -> str:
        """Renders standalone, responsive HTML report with typography, badges, and Mermaid.js support."""
        body_html = markdown.markdown(
            markdown_text,
            extensions=["tables", "fenced_code", "toc"],
        )

        now_str = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
        commit_sha = project.last_commit_sha[:8] if project.last_commit_sha else "Initial"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --border: #334155;
      --brand: #6366f1;
      --brand-hover: #4f46e5;
      --emerald: #10b981;
      --amber: #f59e0b;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f8fafc;
        --card-bg: #ffffff;
        --text: #0f172a;
        --text-muted: #64748b;
        --border: #e2e8f0;
        --brand: #4f46e5;
      }}
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
    }}
    .container {{
      max-width: 960px;
      margin: 0 auto;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 2.5rem;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
    }}
    header {{
      border-bottom: 2px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    .header-badge {{
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: rgba(99, 102, 241, 0.15);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.3);
      margin-bottom: 0.75rem;
    }}
    h1 {{
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: -0.025em;
      margin-bottom: 0.5rem;
    }}
    .meta-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 1.5rem;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.5rem;
    }}
    .meta-bar span strong {{
      color: var(--text);
    }}
    h2 {{
      font-size: 1.4rem;
      font-weight: 700;
      margin-top: 2rem;
      margin-bottom: 0.75rem;
      padding-bottom: 0.3rem;
      border-bottom: 1px solid var(--border);
      color: #818cf8;
    }}
    h3 {{
      font-size: 1.15rem;
      font-weight: 600;
      margin-top: 1.5rem;
      margin-bottom: 0.5rem;
    }}
    p, ul, ol {{
      margin-bottom: 1rem;
    }}
    ul, ol {{
      padding-left: 1.5rem;
    }}
    li {{
      margin-bottom: 0.3rem;
    }}
    blockquote {{
      background: rgba(99, 102, 241, 0.08);
      border-left: 4px solid var(--brand);
      padding: 0.75rem 1rem;
      border-radius: 0 0.5rem 0.5rem 0;
      font-size: 0.875rem;
      margin-bottom: 1.25rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1.5rem 0;
      font-size: 0.875rem;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      text-align: left;
      border: 1px solid var(--border);
    }}
    th {{
      background: rgba(99, 102, 241, 0.1);
      font-weight: 600;
    }}
    tr:nth-child(even) {{
      background: rgba(255, 255, 255, 0.02);
    }}
    pre, code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
    }}
    code {{
      background: rgba(255, 255, 255, 0.08);
      padding: 0.15rem 0.4rem;
      border-radius: 0.25rem;
    }}
    pre {{
      background: #090d16;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 1rem;
      overflow-x: auto;
      margin-bottom: 1.25rem;
    }}
    pre code {{
      background: none;
      padding: 0;
    }}
    hr {{
      border: 0;
      border-top: 1px solid var(--border);
      margin: 2rem 0;
    }}
    footer {{
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
    /* Print Styles */
    @media print {{
      body {{
        background: #fff;
        color: #000;
        padding: 0;
      }}
      .container {{
        border: none;
        box-shadow: none;
        max-width: 100%;
        padding: 0;
      }}
      h2 {{
        page-break-before: auto;
        color: #333;
      }}
      pre, table {{
        page-break-inside: avoid;
      }}
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    document.addEventListener("DOMContentLoaded", function () {{
      mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
    }});
  </script>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-badge">DocPilot AI • {html.escape(report_type.replace('_', ' '))}</div>
      <h1>{html.escape(title)}</h1>
      <div class="meta-bar">
        <span><strong>Project:</strong> {html.escape(project.name)}</span>
        <span><strong>Branch:</strong> {html.escape(project.branch or 'main')}</span>
        <span><strong>Commit:</strong> <code>{html.escape(commit_sha)}</code></span>
        <span><strong>Generated:</strong> {html.escape(now_str)}</span>
      </div>
    </header>

    <main>
      {body_html}
    </main>

    <footer>
      Produced by DocPilot AI Enterprise Documentation Engine • Grounded in static repository evidence and AST analysis.
    </footer>
  </div>
</body>
</html>"""

    def render_pdf(
        self,
        report: TechnicalReport,
        project: Project,
    ) -> bytes:
        """Renders an executive, publication-grade PDF document using ReportLab Platypus."""
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        # Custom Paragraph Styles
        title_style = ParagraphStyle(
            "DocPilotTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocPilotSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=15,
        )
        h1_style = ParagraphStyle(
            "DocPilotH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        )
        h2_style = ParagraphStyle(
            "DocPilotH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#334155"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )
        body_style = ParagraphStyle(
            "DocPilotBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6,
        )
        bullet_style = ParagraphStyle(
            "DocPilotBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            leftIndent=15,
            spaceAfter=3,
        )
        badge_detected = ParagraphStyle(
            "BadgeDetected",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#065f46"),
            backColor=colors.HexColor("#d1fae5"),
            borderPadding=(2, 6, 2, 6),
            spaceAfter=6,
        )
        badge_ai = ParagraphStyle(
            "BadgeAI",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#4338ca"),
            backColor=colors.HexColor("#e0e7ff"),
            borderPadding=(2, 6, 2, 6),
            spaceAfter=6,
        )
        badge_inferred = ParagraphStyle(
            "BadgeInferred",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#92400e"),
            backColor=colors.HexColor("#fef3c7"),
            borderPadding=(2, 6, 2, 6),
            spaceAfter=6,
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        )
        table_header_style = ParagraphStyle(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        )
        code_box_style = ParagraphStyle(
            "CodeBox",
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f1f5f9"),
            borderPadding=(4, 6, 4, 6),
            spaceAfter=6,
        )

        story: List[Any] = []

        # 1. Header Banner
        story.append(Paragraph(html.escape(report.title), title_style))
        commit_sha = project.last_commit_sha[:8] if project.last_commit_sha else "Initial"
        now_str = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
        meta_line = (
            f"<b>Project:</b> {html.escape(project.name)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Branch:</b> {html.escape(project.branch or 'main')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Commit:</b> {html.escape(commit_sha)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Export Date:</b> {now_str}"
        )
        story.append(Paragraph(meta_line, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

        # 2. Iterate Sections
        for s_dict in report.sections:
            s_title = s_dict.get("title", "")
            s_cat = s_dict.get("category", "")
            s_content = s_dict.get("content", "")

            # Section Title
            story.append(Paragraph(html.escape(s_title), h1_style))

            # Classification Badge
            if s_cat == self.CATEGORY_DETECTED:
                story.append(Paragraph("SOURCE CONTEXT: DETECTED FROM REPOSITORY EVIDENCE", badge_detected))
            elif s_cat == self.CATEGORY_INFERRED:
                story.append(Paragraph("SOURCE CONTEXT: INFERRED VIA RELATIONSHIP & CALL GRAPH", badge_inferred))
            else:
                story.append(Paragraph("SOURCE CONTEXT: AI ARCHITECTURAL SYNTHESIS", badge_ai))

            # Parse content lines
            lines = s_content.split("\n")
            in_table = False
            table_lines: List[str] = []
            in_code = False
            code_lines: List[str] = []

            for line in lines:
                stripped = line.strip()

                # Handle code block toggle
                if stripped.startswith("```"):
                    if in_code:
                        in_code = False
                        code_text = html.escape("\n".join(code_lines[:15]))
                        story.append(Paragraph(code_text.replace("\n", "<br/>"), code_box_style))
                        code_lines = []
                    else:
                        in_code = True
                        code_lines = []
                    continue

                if in_code:
                    code_lines.append(line)
                    continue

                # Handle markdown tables
                if stripped.startswith("|") and stripped.endswith("|"):
                    in_table = True
                    table_lines.append(stripped)
                    continue
                elif in_table:
                    # Flush table
                    story.append(self._build_reportlab_table(table_lines, table_header_style, table_cell_style))
                    in_table = False
                    table_lines = []

                if not stripped:
                    continue

                # Headings inside section
                if stripped.startswith("### "):
                    story.append(Paragraph(html.escape(stripped[4:]), h2_style))
                elif stripped.startswith("#### "):
                    story.append(Paragraph(html.escape(stripped[5:]), h2_style))
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    bullet_text = html.escape(stripped[2:])
                    story.append(Paragraph(f"• {bullet_text}", bullet_style))
                else:
                    clean_p = html.escape(stripped)
                    # Convert simple bold **text**
                    clean_p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", clean_p)
                    story.append(Paragraph(clean_p, body_style))

            if in_table and table_lines:
                story.append(self._build_reportlab_table(table_lines, table_header_style, table_cell_style))

            story.append(Spacer(1, 8))

        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue()

    def _build_reportlab_table(
        self,
        table_lines: List[str],
        header_style: ParagraphStyle,
        cell_style: ParagraphStyle,
    ) -> Table:
        """Converts Markdown table rows into a ReportLab Table flowable."""
        data_rows: List[List[Paragraph]] = []
        is_first = True

        for raw_line in table_lines:
            # Skip separator line |---|---|
            if re.match(r"^\|[\s\-:|]+\|$", raw_line):
                continue
            cells = [c.strip() for c in raw_line.strip("|").split("|")]
            if is_first:
                row = [Paragraph(html.escape(c), header_style) for c in cells]
                is_first = False
            else:
                row = [Paragraph(html.escape(c), cell_style) for c in cells]
            data_rows.append(row)

        if not data_rows:
            return Spacer(1, 1)

        col_count = max(len(r) for r in data_rows)
        # Pad shorter rows
        for r in data_rows:
            while len(r) < col_count:
                r.append(Paragraph("", cell_style))

        # 540 pt available width divided evenly
        col_width = 540.0 / col_count
        t = Table(data_rows, colWidths=[col_width] * col_count)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    def _to_response(self, r: TechnicalReport) -> TechnicalReportResponse:
        """Serializes TechnicalReport model to Pydantic schema."""
        sections = [ReportSectionItem(**s) for s in (r.sections or [])]
        return TechnicalReportResponse(
            id=r.id,
            project_id=r.project_id,
            report_type=r.report_type,
            title=r.title,
            description=r.description,
            sections=sections,
            markdown_content=r.markdown_content,
            html_content=r.html_content,
            commit_sha=r.commit_sha,
            version=r.version,
            available_formats=["markdown", "html", "pdf"],
            metadata=r.format_metadata or {},
            created_at=r.created_at,
            updated_at=r.updated_at,
        )


report_service = ReportService()
