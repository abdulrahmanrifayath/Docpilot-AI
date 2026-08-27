from typing import List, Dict, Any, Optional
from backend.app.llm.base import LLMMessage
from backend.app.schemas.structure import ProjectStatisticsResponse, StructureItem
from backend.app.schemas.technology import TechnologyDetectionResponse
from backend.app.schemas.entity import CodeEntityResponse
from backend.app.schemas.dependency import DependencyItem
from backend.app.schemas.api_endpoint import ApiEndpointResponse
from backend.app.schemas.database_schema import DatabaseModelResponse, DatabaseRelationshipResponse


SYSTEM_PROMPT = """You are DocPilot AI, an expert technical software documentation generator.
You generate clear, precise, and production-grade developer documentation based strictly on structured repository analysis.

CRITICAL INSTRUCTIONS:
1. Ground all explanations in the supplied repository facts (languages, detected frameworks, file structures, API routes, database schemas, and AST code signatures).
2. Clearly distinguish detected facts (explicit routes, types, functions, schemas) from inferred explanations (architectural patterns).
3. Do NOT hallucinate or invent endpoints, tables, columns, or files not present in the supplied context.
4. Avoid claiming functionality not substantiated by the code analysis.
5. Use concise, authoritative, and clean technical Markdown.
6. Reference relevant source files (`path/to/file.py`) and code entity names throughout your explanations.
7. Use tables, structured bullet points, and code blocks with syntax highlighting where appropriate.
"""


class PromptBuilder:
    """Builds token-efficient, fact-grounded prompts for 9 documentation types."""

    @classmethod
    def get_system_message(cls) -> LLMMessage:
        return LLMMessage(role="system", content=SYSTEM_PROMPT)

    @classmethod
    def _format_tech_summary(cls, technologies: Optional[TechnologyDetectionResponse], statistics: Optional[ProjectStatisticsResponse]) -> str:
        lines = []
        if technologies:
            if technologies.primary_language:
                lines.append(f"- **Primary Language**: {technologies.primary_language}")
            if technologies.frameworks:
                fws = ", ".join(f"{f.name} ({f.category})" for f in technologies.frameworks)
                lines.append(f"- **Frameworks Detected**: {fws}")
            if technologies.infrastructure:
                infra = ", ".join(f"{i.name} ({i.type})" for i in technologies.infrastructure)
                lines.append(f"- **Infrastructure Detected**: {infra}")
        if statistics:
            lines.append(f"- **Total Files**: {statistics.total_files} | **Total Lines of Code**: {statistics.total_lines}")
            if statistics.languages:
                lang_breakdown = ", ".join(f"{k} ({v.files} files, {v.lines} lines)" for k, v in statistics.languages.items())
                lines.append(f"- **Languages**: {lang_breakdown}")
        return "\n".join(lines) if lines else "No technology metadata available."

    @classmethod
    def _format_apis_summary(cls, apis: List[ApiEndpointResponse], limit: int = 40) -> str:
        if not apis:
            return "No REST API endpoints detected."
        items = []
        for api in apis[:limit]:
            auth_str = " (Auth Required)" if api.authentication_required else ""
            summary_str = f" - {api.summary}" if api.summary else ""
            items.append(f"- `[{api.method}] {api.path}` in `{api.file_path}` (Handler: `{api.handler_name}`){auth_str}{summary_str}")
        if len(apis) > limit:
            items.append(f"... and {len(apis) - limit} additional endpoints.")
        return "\n".join(items)

    @classmethod
    def _format_db_summary(cls, db_models: List[DatabaseModelResponse], db_relationships: List[DatabaseRelationshipResponse], limit: int = 25) -> str:
        if not db_models:
            return "No database models or SQL schemas detected."
        items = []
        for m in db_models[:limit]:
            cols = [f"{f.name} ({f.data_type}{', PK' if f.primary_key else ''})" for f in m.fields[:8]]
            col_str = ", ".join(cols)
            items.append(f"- **Table `{m.table_name}`** (Model `{m.model_name}`, ORM: {m.orm_framework}, defined in `{m.file_path}`): columns: [{col_str}]")
        if len(db_models) > limit:
            items.append(f"... and {len(db_models) - limit} additional database tables.")

        if db_relationships:
            items.append("\n**Detected Relationships:**")
            for r in db_relationships[:20]:
                items.append(f"- `{r.source_table}` -> `{r.target_table}` ({r.relationship_type})")
        return "\n".join(items)

    @classmethod
    def _format_entities_summary(cls, entities: List[CodeEntityResponse], entity_type: Optional[str] = None, limit: int = 50) -> str:
        filtered = [e for e in entities if entity_type is None or e.entity_type == entity_type]
        if not filtered:
            return f"No {entity_type or 'code'} entities found."
        items = []
        for e in filtered[:limit]:
            sig_str = f" | Signature: `{e.signature}`" if e.signature else ""
            doc_str = f" | Doc: {e.docstring[:80]}..." if e.docstring else ""
            items.append(f"- `[{e.entity_type}] {e.name}` in `{e.file_path}:{e.start_line}`{sig_str}{doc_str}")
        if len(filtered) > limit:
            items.append(f"... and {len(filtered) - limit} additional entities.")
        return "\n".join(items)

    # 1. Project Overview Prompt
    @classmethod
    def build_project_overview_prompt(
        cls,
        project_name: str,
        technologies: Optional[TechnologyDetectionResponse],
        statistics: Optional[ProjectStatisticsResponse],
        apis: List[ApiEndpointResponse],
        db_models: List[DatabaseModelResponse],
    ) -> List[LLMMessage]:
        user_content = f"""DOCUMENT TYPE: PROJECT_OVERVIEW
PROJECT NAME: {project_name}

STRUCTURED REPOSITORY FACTS:
{cls._format_tech_summary(technologies, statistics)}

DISCOVERED API ENDPOINTS:
{cls._format_apis_summary(apis, limit=20)}

DATABASE TABLES:
{cls._format_db_summary(db_models, [], limit=15)}

TASK:
Generate an executive technical Project Overview document in GitHub-flavored Markdown.
Structure:
1. Executive Summary & Purpose
2. Technology Stack Breakdown (Languages, Frameworks, Infrastructure)
3. High-Level Architectural Flow (Client -> API -> Service -> Database)
4. Primary Capabilities & Module Organization
5. Repository Statistics & File Distribution
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 2. README Prompt
    @classmethod
    def build_readme_prompt(
        cls,
        project_name: str,
        technologies: Optional[TechnologyDetectionResponse],
        statistics: Optional[ProjectStatisticsResponse],
        apis: List[ApiEndpointResponse],
    ) -> List[LLMMessage]:
        user_content = f"""DOCUMENT TYPE: README
PROJECT NAME: {project_name}

STRUCTURED REPOSITORY FACTS:
{cls._format_tech_summary(technologies, statistics)}

KEY API ENDPOINTS:
{cls._format_apis_summary(apis, limit=15)}

TASK:
Generate a developer-friendly README.md for the repository in GitHub-flavored Markdown.
Include:
- Project Title & Badges Placeholder
- Overview & Feature Highlights
- Architecture & Tech Stack
- Prerequisites & Installation Commands (tailored to detected frameworks/package managers)
- Running Locally & Development Commands
- Key API Endpoints table
- Folder Structure summary
- Contributing & License notices
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 3. Architecture Overview Prompt
    @classmethod
    def build_architecture_prompt(
        cls,
        project_name: str,
        technologies: Optional[TechnologyDetectionResponse],
        statistics: Optional[ProjectStatisticsResponse],
        dependencies: List[DependencyItem],
        apis: List[ApiEndpointResponse],
        db_models: List[DatabaseModelResponse],
    ) -> List[LLMMessage]:
        dep_summary = "\n".join(f"- `{d.source_name}` -[{d.relationship_type}]-> `{d.target_name}`" for d in dependencies[:30])
        user_content = f"""DOCUMENT TYPE: ARCHITECTURE_OVERVIEW
PROJECT NAME: {project_name}

TECHNOLOGY STACK:
{cls._format_tech_summary(technologies, statistics)}

API INTERFACES:
{cls._format_apis_summary(apis, limit=20)}

DATABASE SCHEMA:
{cls._format_db_summary(db_models, [], limit=15)}

KEY COMPONENT RELATIONSHIPS:
{dep_summary if dep_summary else 'Standard modular layered architecture.'}

TASK:
Generate a detailed Architecture Overview document in GitHub-flavored Markdown.
Include:
1. Architectural Style & Layering Pattern (Controller/Router, Service Layer, ORM Models)
2. ASCII / Text Architectural Block Diagram
3. Data Flow from Inbound Requests to Database Persistence
4. Component Dependency Invariants & Boundaries
5. Technology & Third-Party Library Integration Points
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 4. API Documentation Prompt
    @classmethod
    def build_api_doc_prompt(
        cls,
        project_name: str,
        apis: List[ApiEndpointResponse],
    ) -> List[LLMMessage]:
        user_content = f"""DOCUMENT TYPE: API_DOCUMENTATION
PROJECT NAME: {project_name}

TOTAL DISCOVERED APIS: {len(apis)}
DISCOVERED ENDPOINTS AND METADATA:
{cls._format_apis_summary(apis, limit=50)}

TASK:
Generate comprehensive REST API Reference Documentation in GitHub-flavored Markdown.
Structure:
1. API Overview & Conventions (Base URLs, Standard Headers, JSON payloads, Status Codes)
2. Endpoint Matrix Table (Method, Path, Handler, Auth, Tags)
3. Detailed Endpoint Breakdown grouped by resource/router:
   - Method & Path
   - Purpose & Handler reference
   - Request parameters / Schema
   - Expected Response
   - Authentication & Security requirements
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 5. Database Documentation Prompt
    @classmethod
    def build_database_doc_prompt(
        cls,
        project_name: str,
        db_models: List[DatabaseModelResponse],
        db_relationships: List[DatabaseRelationshipResponse],
    ) -> List[LLMMessage]:
        user_content = f"""DOCUMENT TYPE: DATABASE_DOCUMENTATION
PROJECT NAME: {project_name}

TOTAL TABLES: {len(db_models)}
DATABASE SCHEMAS AND FIELDS:
{cls._format_db_summary(db_models, db_relationships, limit=40)}

TASK:
Generate a detailed Database & Data Model Architecture Document in GitHub-flavored Markdown.
Structure:
1. Database Architecture & ORM Framework (SQLAlchemy, Django ORM, or SQL)
2. Relational Entity Tables Breakdown (Table name, Model name, File path, Columns table with data types, PK, FK, Nullable)
3. Entity Relationships & Foreign Keys (Cardinalities, cascade behavior, foreign keys)
4. Data Integrity & Indexing Invariants
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 6. Folder Documentation Prompt
    @classmethod
    def build_folder_doc_prompt(
        cls,
        project_name: str,
        structure_items: List[StructureItem],
    ) -> List[LLMMessage]:
        folder_lines = []
        def traverse(items: List[StructureItem], depth: int = 0):
            for it in items:
                indent = "  " * depth
                if it.type == "directory":
                    folder_lines.append(f"{indent}- **`{it.path}/`** ({it.size} bytes)")
                    if it.children:
                        traverse(it.children, depth + 1)
                elif depth <= 2:
                    folder_lines.append(f"{indent}- `{it.name}` ({it.lines} lines, {it.category})")

        traverse(structure_items[:30])
        tree_str = "\n".join(folder_lines[:60])

        user_content = f"""DOCUMENT TYPE: FOLDER_DOC
PROJECT NAME: {project_name}

DIRECTORY HIERARCHY:
{tree_str if tree_str else 'Standard root directory layout.'}

TASK:
Generate a Folder & Directory Architecture Guide in GitHub-flavored Markdown.
Explain the designated responsibilities, conventions, and architectural role of each primary directory and subdirectory.
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 7. File Documentation Prompt
    @classmethod
    def build_file_doc_prompt(
        cls,
        project_name: str,
        entities: List[CodeEntityResponse],
    ) -> List[LLMMessage]:
        user_content = f"""DOCUMENT TYPE: FILE_DOC
PROJECT NAME: {project_name}

CODE ENTITIES GROUPED BY SOURCE FILE:
{cls._format_entities_summary(entities, limit=60)}

TASK:
Generate a File-by-File Technical Specification in GitHub-flavored Markdown.
Document each key source file, its primary purpose, declared modules, classes, and exported interfaces.
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 8. Class Documentation Prompt
    @classmethod
    def build_class_doc_prompt(
        cls,
        project_name: str,
        entities: List[CodeEntityResponse],
    ) -> List[LLMMessage]:
        classes = [e for e in entities if e.entity_type in ["CLASS", "INTERFACE", "COMPONENT"]]
        user_content = f"""DOCUMENT TYPE: CLASS_DOC
PROJECT NAME: {project_name}

DECLARED CLASSES & INTERFACES ({len(classes)}):
{cls._format_entities_summary(classes, limit=50)}

TASK:
Generate an Object-Oriented Class & Interface Catalog in GitHub-flavored Markdown.
Detail class hierarchies, parent entities, methods, signatures, and data contracts.
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]

    # 9. Function Documentation Prompt
    @classmethod
    def build_function_doc_prompt(
        cls,
        project_name: str,
        entities: List[CodeEntityResponse],
    ) -> List[LLMMessage]:
        functions = [e for e in entities if e.entity_type in ["FUNCTION", "METHOD"]]
        user_content = f"""DOCUMENT TYPE: FUNCTION_DOC
PROJECT NAME: {project_name}

DECLARED FUNCTIONS & METHODS ({len(functions)}):
{cls._format_entities_summary(functions, limit=60)}

TASK:
Generate a Function & Routine Catalog in GitHub-flavored Markdown.
Document routine signatures, parameters, return types, and their file locations.
"""
        return [cls.get_system_message(), LLMMessage(role="user", content=user_content)]
