import time
from typing import List, Dict, Any, Tuple, Optional
from backend.app.core.logging import logger
from backend.app.llm.base import BaseLLMClient
from backend.app.generators.prompt_builder import PromptBuilder
from backend.app.schemas.documentation import DocumentType
from backend.app.schemas.structure import ProjectStatisticsResponse, StructureItem
from backend.app.schemas.technology import TechnologyDetectionResponse
from backend.app.schemas.entity import CodeEntityResponse
from backend.app.schemas.dependency import DependencyItem
from backend.app.schemas.api_endpoint import ApiEndpointResponse
from backend.app.schemas.database_schema import DatabaseModelResponse, DatabaseRelationshipResponse


DOC_TITLES: Dict[str, str] = {
    DocumentType.PROJECT_OVERVIEW.value: "Project Technical Overview",
    DocumentType.README.value: "README Documentation",
    DocumentType.ARCHITECTURE_OVERVIEW.value: "System Architecture Overview",
    DocumentType.API_DOCUMENTATION.value: "REST API Reference Documentation",
    DocumentType.DATABASE_DOCUMENTATION.value: "Database Schema & Entity Documentation",
    DocumentType.FOLDER_DOC.value: "Folder & Directory Architecture",
    DocumentType.FILE_DOC.value: "Source File Specifications",
    DocumentType.CLASS_DOC.value: "Class & Interface Catalog",
    DocumentType.FUNCTION_DOC.value: "Function & Routine Catalog",
}


class DocumentationGenerator:
    """Orchestrates AI prompt creation, LLM execution, and source entity extraction for project documentation."""

    def __init__(self, llm_client: BaseLLMClient):
        self.client = llm_client

    async def generate_document(
        self,
        doc_type: str,
        project_name: str,
        technologies: Optional[TechnologyDetectionResponse] = None,
        statistics: Optional[ProjectStatisticsResponse] = None,
        structure: Optional[List[StructureItem]] = None,
        entities: Optional[List[CodeEntityResponse]] = None,
        dependencies: Optional[List[DependencyItem]] = None,
        apis: Optional[List[ApiEndpointResponse]] = None,
        db_models: Optional[List[DatabaseModelResponse]] = None,
        db_relationships: Optional[List[DatabaseRelationshipResponse]] = None,
    ) -> Tuple[str, str, List[str], str, Dict[str, Any]]:
        """
        Generates a single document type.
        Returns: (title, content, source_entities, model_name, metadata)
        """
        entities = entities or []
        dependencies = dependencies or []
        apis = apis or []
        db_models = db_models or []
        db_relationships = db_relationships or []
        structure = structure or []

        start_time = time.perf_counter()

        # 1. Build Messages
        if doc_type == DocumentType.PROJECT_OVERVIEW.value:
            messages = PromptBuilder.build_project_overview_prompt(
                project_name=project_name,
                technologies=technologies,
                statistics=statistics,
                apis=apis,
                db_models=db_models,
            )
            source_entities = list(set(
                [a.file_path for a in apis] +
                [m.file_path for m in db_models]
            ))

        elif doc_type == DocumentType.README.value:
            messages = PromptBuilder.build_readme_prompt(
                project_name=project_name,
                technologies=technologies,
                statistics=statistics,
                apis=apis,
            )
            source_entities = list(set([a.file_path for a in apis]))

        elif doc_type == DocumentType.ARCHITECTURE_OVERVIEW.value:
            messages = PromptBuilder.build_architecture_prompt(
                project_name=project_name,
                technologies=technologies,
                statistics=statistics,
                dependencies=dependencies,
                apis=apis,
                db_models=db_models,
            )
            source_entities = list(set(
                [d.source_name for d in dependencies[:15]] +
                [a.path for a in apis[:10]] +
                [m.table_name for m in db_models[:10]]
            ))

        elif doc_type == DocumentType.API_DOCUMENTATION.value:
            messages = PromptBuilder.build_api_doc_prompt(
                project_name=project_name,
                apis=apis,
            )
            source_entities = [f"[{a.method}] {a.path}" for a in apis]

        elif doc_type == DocumentType.DATABASE_DOCUMENTATION.value:
            messages = PromptBuilder.build_database_doc_prompt(
                project_name=project_name,
                db_models=db_models,
                db_relationships=db_relationships,
            )
            source_entities = [f"table:{m.table_name}" for m in db_models]

        elif doc_type == DocumentType.FOLDER_DOC.value:
            messages = PromptBuilder.build_folder_doc_prompt(
                project_name=project_name,
                structure_items=structure,
            )
            source_entities = [s.path for s in structure if s.type == "directory"][:20]

        elif doc_type == DocumentType.FILE_DOC.value:
            messages = PromptBuilder.build_file_doc_prompt(
                project_name=project_name,
                entities=entities,
            )
            source_entities = list(set([e.file_path for e in entities]))[:30]

        elif doc_type == DocumentType.CLASS_DOC.value:
            messages = PromptBuilder.build_class_doc_prompt(
                project_name=project_name,
                entities=entities,
            )
            source_entities = [f"class:{e.name}" for e in entities if e.entity_type in ["CLASS", "INTERFACE", "COMPONENT"]][:30]

        elif doc_type == DocumentType.FUNCTION_DOC.value:
            messages = PromptBuilder.build_function_doc_prompt(
                project_name=project_name,
                entities=entities,
            )
            source_entities = [f"func:{e.name}" for e in entities if e.entity_type in ["FUNCTION", "METHOD"]][:30]

        else:
            messages = PromptBuilder.build_project_overview_prompt(
                project_name=project_name,
                technologies=technologies,
                statistics=statistics,
                apis=apis,
                db_models=db_models,
            )
            source_entities = []

        # 2. Invoke LLM
        response = await self.client.generate(messages)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        title = DOC_TITLES.get(doc_type, f"{doc_type.replace('_', ' ').title()} — {project_name}")
        metadata = {
            "tokens_used": response.tokens_used,
            "duration_ms": duration_ms,
            "provider": self.client.get_provider_name(),
            "finish_reason": response.finish_reason,
        }

        logger.info(f"Generated doc [{doc_type}] in {duration_ms}ms ({response.tokens_used} tokens)")

        return title, response.content, source_entities, response.model, metadata
