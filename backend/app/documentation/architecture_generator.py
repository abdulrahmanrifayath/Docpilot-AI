from typing import Any, Dict, List


class ArchitectureGenerator:
    def generate(
        self,
        repo_name: str,
        frameworks: List[str],
        dependency_analysis: Dict[str, Any],
        structure: Dict[str, Any],
        apis: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
    ) -> str:
        """Generates a comprehensive System Architecture Guide."""
        core_mods = dependency_analysis.get("core_modules", [])
        orch_mods = dependency_analysis.get("orchestrator_modules", [])

        core_list = "\n".join([f"- **`{m['file']}`** (Depended on by `{m['dependents_count']}` other modules)" for m in core_mods[:6]]) or "- Single monolith structure"
        orch_list = "\n".join([f"- **`{m['file']}`** (Imports `{m['dependencies_count']}` modules)" for m in orch_mods[:6]]) or "- Single coordinator"

        has_frontend = any(f in frameworks for f in ["React", "Vue", "Next.js", "Angular"])
        has_orm = any(f in frameworks for f in ["SQLAlchemy", "Prisma", "Django", "Mongoose"])

        return f"""# {repo_name} — System Architecture Guide

> Technical architectural design, layered topology, and module interactions.

---

## 🏛️ 1. Architectural Style & Paradigms

The project exhibits a **Layered Service-Oriented Architecture** with distinct separation of concerns:
- **Presentation / Ingress Layer**: Handles HTTP/REST requests, validates payloads, and translates input parameters.
- **Domain & Application Services**: Encapsulates core business rules, domain operations, and orchestrations.
- **Persistence & Data Layer**: Abstraction over database storage, schemas, and relational constraints.
- **Cross-Cutting Utilities**: Configuration, logging, exception handling, and security middlewares.

Detected Framework Ecosystem:
{chr(10).join([f'- **{fw}**' for fw in frameworks]) if frameworks else '- Standard library architectures'}

---

## 🏗️ 2. Architectural Layers

### Layer 1: Client & Presentation
{"This project contains a modern web client layer interacting with downstream backend APIs via HTTP and asynchronous data hooks." if has_frontend else "Clients consume services directly via HTTP REST API endpoints."}

### Layer 2: API Routing & Controller Ingress
- Routes are parsed and dispatched to corresponding controller functions.
- Request validation is enforced before delegating work to domain services.
- Total exposed REST endpoints: `{len(apis)}`.

### Layer 3: Domain Business Services
- Implements state transitions, validations, and business logic.
- Maintains decoupling from transport protocols (HTTP/WebSocket) to allow unit testability.

### Layer 4: Persistence Layer
{"- Utilizes an Object-Relational Mapper (ORM) to interface with relational/document storage." if has_orm else "- Direct database queries and persistence handlers."}
- Total defined schema models: `{len(models)}`.

---

## 🔍 3. Key Architectural Components

### Core Foundation Modules (High In-Degree)
These modules are the foundational building blocks of the codebase. Changes to these modules have a wide impact radius:
{core_list}

### Orchestration & Integration Modules (High Out-Degree)
These modules coordinate multiple subsystems to accomplish end-to-end workflows:
{orch_list}

---

## 🔄 4. Data Flow Lifecycle

1. **Request Intake**: Incoming HTTP request enters the application router.
2. **Middleware Interception**: CORS, authentication verification, and request logging executed.
3. **Validation**: Pydantic / TypeScript types validate payload structure and constraints.
4. **Service Execution**: Handler invokes domain services with validated inputs.
5. **Persistence**: ORM session writes changes or reads records from the database.
6. **Response Serialization**: Output model serialized to JSON and returned with proper HTTP status codes.

---

## 🛡️ 5. Reliability & Security Posture

- **Error Boundary**: Handlers wrap critical operations to return deterministic error codes.
- **Circular Dependencies**: {"⚠️ Circular dependencies detected in module graph — review dependency structure." if dependency_analysis.get("has_circular_dependencies") else "✅ No circular dependencies detected in the module graph."}
"""
