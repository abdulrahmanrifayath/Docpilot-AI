import re
from typing import List, Optional
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class MockLLMClient(BaseLLMClient):
    """Deterministic, context-grounded Mock LLM client for testing and keyless local previews."""

    def __init__(self, model_name: str = "mock-docpilot-v1"):
        self.model_name = model_name

    def is_configured(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "mock"

    def get_model_name(self) -> str:
        return self.model_name

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        full_prompt = "\n\n".join(m.content for m in messages)

        # Detect requested doc type from prompt
        doc_type_match = re.search(r"DOCUMENT TYPE:\s*([A-Z_]+)", full_prompt, re.IGNORECASE)
        doc_type = doc_type_match.group(1).upper() if doc_type_match else "PROJECT_OVERVIEW"

        # Extract project name / title if available
        title_match = re.search(r"PROJECT NAME:\s*([^\n]+)", full_prompt, re.IGNORECASE)
        project_name = title_match.group(1).strip() if title_match else "Software Repository"

        content = self._synthesize_doc(doc_type, project_name, full_prompt)
        tokens_used = len(content.split()) * 2

        return LLMResponse(
            content=content,
            model=self.model_name,
            tokens_used=tokens_used,
            finish_reason="stop",
            metadata={"provider": "mock", "doc_type": doc_type},
        )

    def _synthesize_doc(self, doc_type: str, project_name: str, prompt: str) -> str:
        if doc_type == "PROJECT_OVERVIEW":
            return (
                f"# {project_name} — Project Technical Overview\n\n"
                "## 1. Executive Summary\n"
                f"{project_name} is a structured software system analyzed and indexed by DocPilot AI. "
                "The repository follows a modern modular architecture with distinct presentation, service, and data access layers.\n\n"
                "## 2. Technology Stack & Frameworks\n"
                "Based on static repository analysis, the following technologies and infrastructure components were detected:\n"
                "- **Primary Language**: Multi-tier architecture\n"
                "- **Frameworks**: Backend routing and database abstraction\n"
                "- **Infrastructure**: Container and configuration manifests\n\n"
                "## 3. High-Level Architecture\n"
                "The codebase is structured around separated concerns:\n"
                "1. **Entrypoints & API Routing**: Handles inbound HTTP requests and validates payload schemas.\n"
                "2. **Service Layer**: Encapsulates business logic, data transformation, and service workflows.\n"
                "3. **Data Layer**: Manages persistent entities, schemas, and relational models.\n\n"
                "## 4. Key Capabilities\n"
                "- Automated endpoint routing and schema validation.\n"
                "- Normalized database mapping and relationship integrity.\n"
                "- Clean modular decoupling for extensible maintenance."
            )

        elif doc_type == "README":
            return (
                f"# {project_name}\n\n"
                "> Intelligent documentation generated automatically by **DocPilot AI**.\n\n"
                "## Overview\n"
                f"{project_name} is a software repository structured for scalable application workflows.\n\n"
                "## Getting Started\n\n"
                "### Prerequisites\n"
                "- Runtime environment corresponding to detected project languages.\n"
                "- Package manager and dependency toolchain.\n\n"
                "### Installation\n"
                "```bash\n"
                "# Clone repository\n"
                f"git clone <repository-url>\n"
                f"cd {project_name.lower().replace(' ', '-')}\n\n"
                "# Install dependencies\n"
                "npm install  # or pip install -r requirements.txt\n"
                "```\n\n"
                "### Running the Application\n"
                "```bash\n"
                "# Start development server\n"
                "npm run dev  # or uvicorn app.main:app --reload\n"
                "```\n\n"
                "## Repository Structure\n"
                "The codebase contains dedicated source directories for routing, services, and models."
            )

        elif doc_type == "ARCHITECTURE_OVERVIEW":
            return (
                f"# Architecture Overview — {project_name}\n\n"
                "## Architectural Topology\n"
                "The system employs a layered architectural design pattern separating interface contracts from core business computation:\n\n"
                "```\n"
                "[ Client / Frontend ]\n"
                "       |\n"
                "       v\n"
                "[ API Routers & Controllers ]\n"
                "       |\n"
                "       v\n"
                "[ Service Layer / Domain Logic ]\n"
                "       |\n"
                "       v\n"
                "[ ORM Models & Data Storage ]\n"
                "```\n\n"
                "## Key Architectural Invariants\n"
                "- **Separation of Concerns**: API routes delegate execution directly to domain services.\n"
                "- **Data Integrity**: Database models maintain foreign key and relationship constraints.\n"
                "- **Dependency Flow**: Unidirectional dependencies from outer routing layers to internal models."
            )

        elif doc_type == "API_DOCUMENTATION":
            return (
                f"# REST API Documentation — {project_name}\n\n"
                "## Overview\n"
                "This document details the HTTP REST endpoints discovered in the codebase.\n\n"
                "## Discovered Endpoints\n\n"
                "| Method | Route Path | Description / Handler | Auth Required |\n"
                "|:---|:---|:---|:---|\n"
                "| `GET` | `/api/v1/projects` | List projects | No |\n"
                "| `POST` | `/api/v1/projects` | Create project | No |\n"
                "| `GET` | `/api/v1/system/status` | System health check | No |\n\n"
                "### Request / Response Schemas\n"
                "Endpoints adhere to structured JSON request payloads and return typed responses with standardized status codes."
            )

        elif doc_type == "DATABASE_DOCUMENTATION":
            return (
                f"# Database Architecture & Schema — {project_name}\n\n"
                "## Overview\n"
                "The database schema consists of structured relational entities with primary and foreign key constraints.\n\n"
                "## Entity Tables\n\n"
                "### Models & Columns\n"
                "- **Primary Keys**: Integer or UUID unique identifiers.\n"
                "- **Foreign Keys**: Explicit column links enforcing relational referential integrity.\n\n"
                "## Entity Relationships\n"
                "Entities communicate across `ONE_TO_MANY` and `FOREIGN_KEY` connections ensuring data consistency."
            )

        elif doc_type == "FOLDER_DOC":
            return (
                f"# Folder & Directory Architecture — {project_name}\n\n"
                "## Directory Hierarchy Breakdown\n"
                "Each directory in the codebase has designated responsibilities:\n"
                "- `app/api/`: Inbound API routers, endpoints, and HTTP request handlers.\n"
                "- `app/models/`: Persistent database models and entity definitions.\n"
                "- `app/services/`: Core application services and business workflow logic.\n"
                "- `app/schemas/`: Validation and data transfer schemas."
            )

        elif doc_type == "FILE_DOC":
            return (
                f"# File Technical Documentation — {project_name}\n\n"
                "## Source File Specifications\n"
                "Documents the role, dependencies, and declared code entities for core repository files.\n\n"
                "### Key Modules\n"
                "- Declares classes, methods, and functions.\n"
                "- Encapsulates targeted functionality with typed signatures."
            )

        elif doc_type == "CLASS_DOC":
            return (
                f"# Class Catalog & Object Models — {project_name}\n\n"
                "## Object-Oriented Structures\n"
                "Documents object structures, classes, and inheritance hierarchies discovered across the repository."
            )

        elif doc_type == "FUNCTION_DOC":
            return (
                f"# Function & Routine Catalog — {project_name}\n\n"
                "## Discovered Routines\n"
                "Documents top-level functions, handler routines, signatures, parameter requirements, and return types."
            )

        return f"# {doc_type} — {project_name}\n\nTechnical documentation generated based on static code analysis."
