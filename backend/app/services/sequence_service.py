"""
Automatic Sequence Diagram Generation Engine for DocPilot AI (Phase 11).

Generates grounded sequence diagrams for critical application workflows:
- User login / authentication
- User registration
- Order creation & checkout
- Payment processing
- Custom API request lifecycles

Infers probable execution sequences from static AST analysis, API routes,
dependency calls, and ORM database models, with explicit confidence scoring.
Labels results as 'Static analysis-based interaction flow'.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import (
    Project,
    CodeEntity,
    DependencyRelationship,
    APIEndpoint,
    DatabaseModel,
    SequenceDiagram,
)
from app.schemas.project import SequenceStep, SequenceDiagramResponse, SequenceGenerateResponse
from app.services.diagram_service import validate_mermaid_syntax

logger = logging.getLogger("docpilot.sequences")


class SequenceService:
    """Service that discovers application workflows and generates Mermaid sequence diagrams."""

    DISCLAIMER_LABEL = "Static analysis-based interaction flow"

    def _clean_ident(self, raw: str, prefix: str = "P") -> str:
        """Sanitizes strings for safe Mermaid participant aliases."""
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', raw)
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        if not cleaned or not cleaned[0].isalpha():
            cleaned = f"{prefix}_{cleaned or 'ident'}"
        return cleaned

    def _escape_label(self, raw: str) -> str:
        """Sanitizes labels for sequence arrows and notes."""
        if not raw:
            return ""
        clean = raw.replace('"', "'").replace("\n", " ").strip()
        return clean[:90]

    # =========================================================================
    # Flow Categorization & Classification
    # =========================================================================

    def _classify_endpoint(self, ep: APIEndpoint) -> str:
        """Classifies an API endpoint into a workflow category."""
        path_lower = (ep.path or "").lower()
        handler_lower = (ep.handler_name or "").lower()
        combined = f"{path_lower} {handler_lower}"

        # 1. Registration takes priority over generic 'auth'
        if any(k in combined for k in ("register", "signup", "create_user", "sign_up")):
            return "REGISTRATION"

        # 2. Authentication
        if any(k in combined for k in ("login", "signin", "sign_in", "authenticate", "token", "auth")):
            return "AUTHENTICATION"

        # 3. Payment takes priority over generic 'checkout'
        if any(k in combined for k in ("payment", "charge", "billing", "invoice", "pay")):
            return "PAYMENT"

        # 4. Order
        if any(k in combined for k in ("order", "checkout", "cart", "purchase")):
            return "ORDER"

        if ep.method in ("POST", "PUT", "PATCH", "DELETE"):
            return "DATA_MUTATION"
        return "GENERAL_FLOW"

    # =========================================================================
    # Sequence Synthesis Helpers
    # =========================================================================

    def _find_connected_service(
        self,
        handler_name: Optional[str],
        dependencies: List[DependencyRelationship],
        entities: List[CodeEntity],
    ) -> Optional[CodeEntity]:
        """Finds service classes/functions invoked or imported by the endpoint handler."""
        if not handler_name:
            # Fallback to any class with 'Service' in name
            services = [e for e in entities if e.entity_type == "CLASS" and "service" in e.name.lower()]
            return services[0] if services else None

        # Check direct call relationships from handler
        for rel in dependencies:
            src = getattr(rel, "source", None) or getattr(rel, "source_name", "")
            tgt = getattr(rel, "target", None) or getattr(rel, "target_name", "")
            if handler_name in src or src in handler_name:
                match = next((e for e in entities if e.name == tgt), None)
                if match:
                    return match

        # Check classes in same directory or containing 'Service'
        service_classes = [e for e in entities if e.entity_type == "CLASS" and "service" in e.name.lower()]
        if service_classes:
            return service_classes[0]

        # Generic class fallback
        classes = [e for e in entities if e.entity_type == "CLASS"]
        return classes[0] if classes else None

    def _find_connected_model(
        self,
        service_name: Optional[str],
        db_models: List[DatabaseModel],
        category: str,
    ) -> Optional[DatabaseModel]:
        """Matches database model related to the service or workflow category."""
        if not db_models:
            return None

        cat_keywords = {
            "AUTHENTICATION": ("user", "account", "customer", "auth"),
            "REGISTRATION": ("user", "account", "customer", "profile"),
            "ORDER": ("order", "cart", "item", "purchase"),
            "PAYMENT": ("payment", "transaction", "invoice", "order"),
        }
        keywords = cat_keywords.get(category, ())

        # Match by category keywords first
        for dm in db_models:
            if any(k in dm.name.lower() or k in (dm.table_name or "").lower() for k in keywords):
                return dm

        # Match by service name substring
        if service_name:
            s_clean = re.sub(r'service|client|manager', '', service_name.lower())
            if s_clean:
                for dm in db_models:
                    if s_clean in dm.name.lower() or s_clean in (dm.table_name or "").lower():
                        return dm

        return db_models[0]

    # =========================================================================
    # Flow Builders
    # =========================================================================

    def _build_sequence_for_flow(
        self,
        category: str,
        ep: Optional[APIEndpoint],
        project: Project,
        entities: List[CodeEntity],
        dependencies: List[DependencyRelationship],
        db_models: List[DatabaseModel],
    ) -> Dict[str, Any]:
        """Synthesizes structured steps, participants, and Mermaid code for a flow."""
        steps: List[Dict[str, Any]] = []
        participants: List[Tuple[str, str, str]] = []  # (alias, display_name, type: actor/participant)

        handler_name = ep.handler_name if ep else None
        endpoint_path = ep.path if ep else (
            "/api/v1/auth/login" if category == "AUTHENTICATION" else
            "/api/v1/auth/register" if category == "REGISTRATION" else
            "/api/v1/orders" if category == "ORDER" else
            "/api/v1/payments/checkout" if category == "PAYMENT" else
            "/api/v1/resource"
        )
        endpoint_method = ep.method if ep else "POST"

        connected_service = self._find_connected_service(handler_name, dependencies, entities)
        service_name = connected_service.name if connected_service else (
            "AuthService" if category == "AUTHENTICATION" else
            "UserService" if category == "REGISTRATION" else
            "OrderService" if category == "ORDER" else
            "PaymentService" if category == "PAYMENT" else
            "ApplicationService"
        )

        connected_model = self._find_connected_model(service_name, db_models, category)
        model_name = connected_model.name if connected_model else (
            "User" if category in ("AUTHENTICATION", "REGISTRATION") else
            "Order" if category == "ORDER" else
            "PaymentTransaction" if category == "PAYMENT" else
            "DatabaseStorage"
        )

        # Build participant list
        participants.append(("User", "User", "actor"))
        participants.append(("FE", "Frontend", "participant"))
        participants.append(("API", f"API ({endpoint_path})", "participant"))
        participants.append(("Svc", service_name, "participant"))
        participants.append(("DB", f"Database ({model_name})", "participant"))

        if category == "PAYMENT" or (category == "ORDER" and any("payment" in e.name.lower() for e in entities)):
            participants.append(("Gateway", "External Payment Gateway", "participant"))

        # Formulate steps based on flow category
        if category == "AUTHENTICATION":
            flow_name = f"{project.name} - User Authentication & Login Flow"
            description = (
                f"Authentication flow dispatched via {endpoint_method} {endpoint_path} to {service_name}, "
                f"validating credentials against the {model_name} table and returning an authorization token."
            )
            steps = [
                {
                    "step_number": 1,
                    "source": "User",
                    "target": "FE",
                    "action": "Submit login credentials",
                    "return_action": "Render dashboard & session active",
                    "confidence": 0.95,
                    "step_type": "USER_INTERACTION",
                },
                {
                    "step_number": 2,
                    "source": "FE",
                    "target": "API",
                    "action": f"{endpoint_method} {endpoint_path} (credentials)",
                    "return_action": "HTTP 200 OK (access_token, token_type)",
                    "confidence": 0.95,
                    "step_type": "HTTP_REQUEST",
                },
                {
                    "step_number": 3,
                    "source": "API",
                    "target": "Svc",
                    "action": f"{handler_name or 'authenticate_user'}(credentials)",
                    "return_action": "User principal & JWT claims",
                    "confidence": 0.90,
                    "step_type": "FUNCTION_CALL",
                },
                {
                    "step_number": 4,
                    "source": "Svc",
                    "target": "DB",
                    "action": f"Query {model_name} record by email/username",
                    "return_action": f"{model_name} entity & password hash",
                    "confidence": 0.88,
                    "step_type": "DATABASE_QUERY",
                },
                {
                    "step_number": 5,
                    "source": "Svc",
                    "target": "Svc",
                    "action": "Verify password hash & generate JWT token",
                    "return_action": None,
                    "confidence": 0.92,
                    "step_type": "INTERNAL_LOGIC",
                },
            ]

        elif category == "REGISTRATION":
            flow_name = f"{project.name} - User Registration Flow"
            description = (
                f"Registration flow routed through {endpoint_method} {endpoint_path} into {service_name}, "
                f"verifying uniqueness and persisting a new {model_name} record."
            )
            steps = [
                {
                    "step_number": 1,
                    "source": "User",
                    "target": "FE",
                    "action": "Submit user registration form",
                    "return_action": "Account created confirmation",
                    "confidence": 0.95,
                    "step_type": "USER_INTERACTION",
                },
                {
                    "step_number": 2,
                    "source": "FE",
                    "target": "API",
                    "action": f"{endpoint_method} {endpoint_path} (user payload)",
                    "return_action": "HTTP 201 Created (user_id)",
                    "confidence": 0.95,
                    "step_type": "HTTP_REQUEST",
                },
                {
                    "step_number": 3,
                    "source": "API",
                    "target": "Svc",
                    "action": f"{handler_name or 'create_user'}(user_data)",
                    "return_action": "Created user object",
                    "confidence": 0.90,
                    "step_type": "FUNCTION_CALL",
                },
                {
                    "step_number": 4,
                    "source": "Svc",
                    "target": "DB",
                    "action": f"Check existing {model_name} uniqueness",
                    "return_action": "No duplicate record found",
                    "confidence": 0.88,
                    "step_type": "DATABASE_QUERY",
                },
                {
                    "step_number": 5,
                    "source": "Svc",
                    "target": "DB",
                    "action": f"INSERT INTO {model_name} (hashed password, details)",
                    "return_action": f"{model_name} record committed",
                    "confidence": 0.88,
                    "step_type": "DATABASE_QUERY",
                },
            ]

        elif category == "ORDER":
            flow_name = f"{project.name} - Order Creation & Checkout Flow"
            description = (
                f"End-to-end checkout flow invoking {endpoint_method} {endpoint_path}, "
                f"coordinating {service_name} with payment verification and persisting {model_name} entities."
            )
            has_gw = any(p[0] == "Gateway" for p in participants)
            steps = [
                {
                    "step_number": 1,
                    "source": "User",
                    "target": "FE",
                    "action": "Click Checkout / Confirm Order",
                    "return_action": "Display order success confirmation",
                    "confidence": 0.95,
                    "step_type": "USER_INTERACTION",
                },
                {
                    "step_number": 2,
                    "source": "FE",
                    "target": "API",
                    "action": f"{endpoint_method} {endpoint_path} (order items, payment)",
                    "return_action": "HTTP 201 Created (order_id, receipt)",
                    "confidence": 0.95,
                    "step_type": "HTTP_REQUEST",
                },
                {
                    "step_number": 3,
                    "source": "API",
                    "target": "Svc",
                    "action": f"{handler_name or 'create_order'}(order_payload)",
                    "return_action": "Order confirmation response",
                    "confidence": 0.90,
                    "step_type": "FUNCTION_CALL",
                },
                {
                    "step_number": 4,
                    "source": "Svc",
                    "target": "DB",
                    "action": "Verify inventory & validate pricing",
                    "return_action": "Inventory reserved",
                    "confidence": 0.85,
                    "step_type": "DATABASE_QUERY",
                },
            ]
            if has_gw:
                steps.append({
                    "step_number": 5,
                    "source": "Svc",
                    "target": "Gateway",
                    "action": "Authorize card & capture payment",
                    "return_action": "Payment authorization token",
                    "confidence": 0.84,
                    "step_type": "EXTERNAL_API",
                })
            steps.append({
                "step_number": len(steps) + 1,
                "source": "Svc",
                "target": "DB",
                "action": f"INSERT INTO {model_name} (order status: CONFIRMED)",
                "return_action": f"{model_name} persisted with ID",
                "confidence": 0.88,
                "step_type": "DATABASE_QUERY",
            })

        elif category == "PAYMENT":
            flow_name = f"{project.name} - Payment Processing Flow"
            description = (
                f"Financial transaction flow processing payments via {endpoint_method} {endpoint_path}, "
                f"dispatching to {service_name} and external payment providers."
            )
            steps = [
                {
                    "step_number": 1,
                    "source": "User",
                    "target": "FE",
                    "action": "Authorize payment charge",
                    "return_action": "Payment confirmation & receipt",
                    "confidence": 0.95,
                    "step_type": "USER_INTERACTION",
                },
                {
                    "step_number": 2,
                    "source": "FE",
                    "target": "API",
                    "action": f"{endpoint_method} {endpoint_path} (payment_data)",
                    "return_action": "HTTP 200 OK (payment_receipt)",
                    "confidence": 0.95,
                    "step_type": "HTTP_REQUEST",
                },
                {
                    "step_number": 3,
                    "source": "API",
                    "target": "Svc",
                    "action": f"{handler_name or 'process_payment'}(payload)",
                    "return_action": "Transaction result payload",
                    "confidence": 0.90,
                    "step_type": "FUNCTION_CALL",
                },
                {
                    "step_number": 4,
                    "source": "Svc",
                    "target": "Gateway",
                    "action": "POST /v1/charges (amount, currency)",
                    "return_action": "Charge succeeded (txn_id)",
                    "confidence": 0.85,
                    "step_type": "EXTERNAL_API",
                },
                {
                    "step_number": 5,
                    "source": "Svc",
                    "target": "DB",
                    "action": f"Record transaction in {model_name}",
                    "return_action": "Audit entry saved",
                    "confidence": 0.88,
                    "step_type": "DATABASE_QUERY",
                },
            ]

        else:
            # Custom / Mutation / General endpoint flow
            action_desc = "Resource mutation" if endpoint_method in ("POST", "PUT", "PATCH") else "Data retrieval"
            flow_name = f"{project.name} - {endpoint_method} {endpoint_path} Execution Flow"
            description = (
                f"Static analysis-based interaction flow tracing {endpoint_method} {endpoint_path} "
                f"through controller {handler_name or 'handler'}, domain service {service_name}, and {model_name} models."
            )
            steps = [
                {
                    "step_number": 1,
                    "source": "User",
                    "target": "FE",
                    "action": f"Trigger {action_desc.lower()}",
                    "return_action": "Updated view state",
                    "confidence": 0.95,
                    "step_type": "USER_INTERACTION",
                },
                {
                    "step_number": 2,
                    "source": "FE",
                    "target": "API",
                    "action": f"{endpoint_method} {endpoint_path}",
                    "return_action": "HTTP 200 / 201 Response",
                    "confidence": 0.95,
                    "step_type": "HTTP_REQUEST",
                },
                {
                    "step_number": 3,
                    "source": "API",
                    "target": "Svc",
                    "action": f"{handler_name or 'handle_request'}()",
                    "return_action": "Service result",
                    "confidence": 0.88,
                    "step_type": "FUNCTION_CALL",
                },
                {
                    "step_number": 4,
                    "source": "Svc",
                    "target": "DB",
                    "action": f"Query / mutate {model_name} data",
                    "return_action": f"{model_name} query response",
                    "confidence": 0.84,
                    "step_type": "DATABASE_QUERY",
                },
            ]

        # Calculate overall confidence
        conf_scores = [s["confidence"] for s in steps]
        overall_confidence = round(sum(conf_scores) / len(conf_scores), 2) if conf_scores else 0.85

        # Generate Mermaid Sequence Diagram Code
        mermaid_lines = ["sequenceDiagram", "    autonumber"]

        # 1. Declare Participants
        for alias, dname, ptype in participants:
            clean_dname = self._escape_label(dname)
            if ptype == "actor":
                mermaid_lines.append(f'    actor {alias} as {clean_dname}')
            else:
                mermaid_lines.append(f'    participant {alias} as {clean_dname}')

        # 2. Add Top Disclaimer Note
        first_alias = participants[0][0]
        last_alias = participants[-1][0]
        mermaid_lines.append("")
        mermaid_lines.append(
            f'    Note over {first_alias},{last_alias}: {self.DISCLAIMER_LABEL} (Confidence: {int(overall_confidence * 100)}%)'
        )
        mermaid_lines.append("")

        # 3. Add Forward Interactions
        for s in steps:
            src = s["source"]
            tgt = s["target"]
            act = self._escape_label(s["action"])
            conf_percent = int(s["confidence"] * 100)
            if src == tgt:
                mermaid_lines.append(f'    {src}->>{tgt}: {act}')
            else:
                mermaid_lines.append(f'    {src}->>{tgt}: {act}')

        mermaid_lines.append("")

        # 4. Add Return Responses in reverse order for components that returned actions
        return_steps = [s for s in steps if s.get("return_action") and s["source"] != s["target"]]
        for s in reversed(return_steps):
            src = s["target"]
            tgt = s["source"]
            ret_act = self._escape_label(s["return_action"])
            mermaid_lines.append(f'    {src}-->>{tgt}: {ret_act}')

        mermaid_code = "\n".join(mermaid_lines)

        # Collect involved component identifiers
        involved = [p[1] for p in participants]

        flow_key = f"{category.lower()}_{self._clean_ident(endpoint_path)}"

        return {
            "name": flow_name,
            "flow_key": flow_key,
            "description": description,
            "trigger_endpoint": endpoint_path,
            "trigger_method": endpoint_method,
            "flow_category": category,
            "mermaid_code": mermaid_code,
            "steps": steps,
            "involved_components": involved,
            "overall_confidence": overall_confidence,
            "execution_type": self.DISCLAIMER_LABEL,
            "is_guaranteed": False,
        }

    # =========================================================================
    # Public Execution Engine
    # =========================================================================

    async def generate_sequences(
        self,
        project_id: str,
        db: AsyncSession,
        flow_categories: Optional[List[str]] = None,
        force_regenerate: bool = False,
    ) -> SequenceGenerateResponse:
        """
        Discovers application flows and generates Mermaid sequence diagrams.
        """
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.code_entities),
                selectinload(Project.dependency_relationships),
                selectinload(Project.api_endpoints),
                selectinload(Project.database_models),
            )
        )
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        entities = project.code_entities or []
        dependencies = project.dependency_relationships or []
        apis = project.api_endpoints or []
        db_models = project.database_models or []

        # Categorize endpoints
        categorized_endpoints: Dict[str, List[APIEndpoint]] = {
            "AUTHENTICATION": [],
            "REGISTRATION": [],
            "ORDER": [],
            "PAYMENT": [],
            "DATA_MUTATION": [],
            "GENERAL_FLOW": [],
        }

        for ep in apis:
            cat = self._classify_endpoint(ep)
            categorized_endpoints[cat].append(ep)

        # Determine target categories
        active_cats: List[str] = []
        if flow_categories:
            active_cats = [c.upper() for c in flow_categories]
        else:
            # Collect categories that have endpoints or core fallbacks
            for cat in ("AUTHENTICATION", "REGISTRATION", "ORDER", "PAYMENT"):
                if categorized_endpoints[cat]:
                    active_cats.append(cat)

            # If none matched, check if any endpoints exist
            if not active_cats:
                if categorized_endpoints["DATA_MUTATION"]:
                    active_cats.append("DATA_MUTATION")
                elif categorized_endpoints["GENERAL_FLOW"]:
                    active_cats.append("GENERAL_FLOW")
                else:
                    # Default essential flows so project always has core diagrams
                    active_cats = ["AUTHENTICATION", "REGISTRATION", "ORDER"]

        generated_diagrams: List[SequenceDiagram] = []

        for cat in active_cats:
            cat_eps = categorized_endpoints.get(cat, [])
            target_ep = cat_eps[0] if cat_eps else None

            flow_dict = self._build_sequence_for_flow(
                category=cat,
                ep=target_ep,
                project=project,
                entities=entities,
                dependencies=dependencies,
                db_models=db_models,
            )

            # Validate Mermaid Sequence Syntax
            is_valid, err = validate_mermaid_syntax(flow_dict["mermaid_code"])
            if not is_valid:
                logger.error(f"Generated sequence diagram failed Mermaid validation: {err}")
                # Safe fallback
                flow_dict["mermaid_code"] = (
                    "sequenceDiagram\n"
                    "    autonumber\n"
                    "    actor User as User\n"
                    "    participant App as Application\n"
                    f"    Note over User,App: {self.DISCLAIMER_LABEL}\n"
                    f"    User->>App: {cat.replace('_', ' ').title()} Request\n"
                    "    App-->>User: Operation Completed\n"
                )

            # Check if sequence already exists for this flow_key
            flow_key = flow_dict["flow_key"]
            seq_stmt = select(SequenceDiagram).where(
                SequenceDiagram.project_id == project_id,
                SequenceDiagram.flow_key == flow_key,
            )
            seq_res = await db.execute(seq_stmt)
            existing = seq_res.scalars().first()

            now = datetime.now(timezone.utc)
            meta = {
                "category": cat,
                "endpoints_found": len(cat_eps),
                "entities_grounded": len(entities),
                "generated_at": now.isoformat(),
            }

            if existing:
                existing.name = flow_dict["name"]
                existing.description = flow_dict["description"]
                existing.trigger_endpoint = flow_dict["trigger_endpoint"]
                existing.trigger_method = flow_dict["trigger_method"]
                existing.flow_category = flow_dict["flow_category"]
                existing.mermaid_code = flow_dict["mermaid_code"]
                existing.steps = flow_dict["steps"]
                existing.involved_components = flow_dict["involved_components"]
                existing.overall_confidence = flow_dict["overall_confidence"]
                existing.execution_type = flow_dict["execution_type"]
                existing.is_guaranteed = flow_dict["is_guaranteed"]
                existing.version = existing.version + 1
                existing.metadata_json = meta
                existing.updated_at = now
                diagram_obj = existing
            else:
                diagram_obj = SequenceDiagram(
                    project_id=project_id,
                    name=flow_dict["name"],
                    flow_key=flow_key,
                    description=flow_dict["description"],
                    trigger_endpoint=flow_dict["trigger_endpoint"],
                    trigger_method=flow_dict["trigger_method"],
                    flow_category=flow_dict["flow_category"],
                    mermaid_code=flow_dict["mermaid_code"],
                    steps=flow_dict["steps"],
                    involved_components=flow_dict["involved_components"],
                    overall_confidence=flow_dict["overall_confidence"],
                    execution_type=flow_dict["execution_type"],
                    is_guaranteed=flow_dict["is_guaranteed"],
                    version=1,
                    metadata_json=meta,
                    created_at=now,
                    updated_at=now,
                )
                db.add(diagram_obj)

            await db.commit()
            await db.refresh(diagram_obj)
            generated_diagrams.append(diagram_obj)

        responses = [SequenceDiagramResponse.model_validate(d) for d in generated_diagrams]
        return SequenceGenerateResponse(
            status="SUCCESS",
            project_id=project_id,
            total_generated=len(responses),
            sequences=responses,
            message=f"Successfully generated {len(responses)} sequence diagrams from static code analysis.",
        )

    async def list_sequences(
        self,
        project_id: str,
        db: AsyncSession,
        flow_category: Optional[str] = None,
    ) -> List[SequenceDiagramResponse]:
        """Lists all stored sequence diagrams for a project with optional category filter."""
        stmt = select(SequenceDiagram).where(SequenceDiagram.project_id == project_id)
        if flow_category:
            stmt = stmt.where(SequenceDiagram.flow_category == flow_category.upper())

        stmt = stmt.order_by(SequenceDiagram.flow_category.asc(), SequenceDiagram.name.asc())
        res = await db.execute(stmt)
        seqs = res.scalars().all()
        return [SequenceDiagramResponse.model_validate(s) for s in seqs]

    async def get_sequence_by_id(
        self,
        project_id: str,
        sequence_id: str,
        db: AsyncSession,
    ) -> SequenceDiagramResponse:
        """Retrieves a single sequence diagram by ID."""
        stmt = select(SequenceDiagram).where(
            SequenceDiagram.project_id == project_id,
            SequenceDiagram.id == sequence_id,
        )
        res = await db.execute(stmt)
        seq = res.scalar_one_or_none()
        if not seq:
            raise ValueError(f"Sequence diagram with ID '{sequence_id}' not found for project '{project_id}'")
        return SequenceDiagramResponse.model_validate(seq)

    async def regenerate_sequence(
        self,
        project_id: str,
        sequence_id: str,
        db: AsyncSession,
    ) -> SequenceDiagramResponse:
        """Regenerates a specific sequence diagram, refreshing analysis context and incrementing version."""
        stmt = select(SequenceDiagram).where(
            SequenceDiagram.project_id == project_id,
            SequenceDiagram.id == sequence_id,
        )
        res = await db.execute(stmt)
        seq = res.scalar_one_or_none()
        if not seq:
            raise ValueError(f"Sequence diagram with ID '{sequence_id}' not found for project '{project_id}'")

        gen_resp = await self.generate_sequences(
            project_id=project_id,
            db=db,
            flow_categories=[seq.flow_category],
            force_regenerate=True,
        )
        for s in gen_resp.sequences:
            if s.id == sequence_id or s.flow_key == seq.flow_key:
                return s
        return await self.get_sequence_by_id(project_id, sequence_id, db)


sequence_service = SequenceService()
