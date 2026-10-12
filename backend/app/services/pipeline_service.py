import asyncio
import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from git import Repo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.repository import Repository, Document, Diagram
from app.parsers.factory import get_parser
from app.parsers.base import ParsedFile
from app.analyzers.language_detector import LanguageDetector, IGNORED_DIRS
from app.analyzers.structure_analyzer import StructureAnalyzer
from app.analyzers.dependency_analyzer import DependencyAnalyzer
from app.analyzers.api_analyzer import APIAnalyzer
from app.analyzers.database_analyzer import DatabaseAnalyzer
from app.knowledge.graph import ProjectKnowledgeGraph
from app.diagrams.mermaid_generator import MermaidGenerator
from app.diagrams.react_flow_adapter import ReactFlowAdapter
from app.documentation.readme_generator import ReadmeGenerator
from app.documentation.api_doc_generator import ApiDocGenerator
from app.documentation.architecture_generator import ArchitectureGenerator
from app.documentation.onboarding_generator import OnboardingGenerator
from app.documentation.report_generator import ReportGenerator
from app.ai.embeddings import embedding_service
from app.ai.vector_store import vector_store, VectorChunk

logger = logging.getLogger("docpilot.pipeline")


class PipelineService:
    def __init__(self) -> None:
        self.lang_detector = LanguageDetector()
        self.struct_analyzer = StructureAnalyzer()
        self.dep_analyzer = DependencyAnalyzer()
        self.api_analyzer = APIAnalyzer()
        self.db_analyzer = DatabaseAnalyzer()
        self.mermaid_gen = MermaidGenerator()
        self.react_flow_adapter = ReactFlowAdapter()
        self.readme_gen = ReadmeGenerator()
        self.api_doc_gen = ApiDocGenerator()
        self.arch_gen = ArchitectureGenerator()
        self.onboarding_gen = OnboardingGenerator()
        self.report_gen = ReportGenerator()

    async def run_pipeline(
        self,
        repository_id: str,
        session_factory,
    ) -> None:
        """Executes the full 11-stage repository analysis pipeline asynchronously."""
        async with session_factory() as session:
            repo: Optional[Repository] = await session.get(Repository, repository_id)
            if not repo:
                logger.error(f"Repository {repository_id} not found")
                return

            try:
                repo_path = Path(repo.local_path)
                repo.status = "analyzing"
                repo.progress_percent = 5
                repo.current_step = "Stage 1: Extracting repository contents..."
                await session.commit()

                # Stage 1: Extraction / Clone
                if repo.source_type == "git" and repo.source_url:
                    if not repo_path.exists() or not any(repo_path.iterdir()):
                        repo_path.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Cloning {repo.source_url} to {repo_path}")
                        Repo.clone_from(repo.source_url, str(repo_path), depth=1)

                elif repo.source_type == "zip":
                    # Check if local_path is a zip file that needs extraction
                    if repo.local_path.endswith(".zip") and Path(repo.local_path).exists():
                        target_dir = repo_path.parent / repo_path.stem
                        target_dir.mkdir(parents=True, exist_ok=True)
                        with zipfile.ZipFile(repo.local_path, "r") as zip_ref:
                            zip_ref.extractall(target_dir)
                        # Check for single nested top folder
                        nested = list(target_dir.iterdir())
                        if len(nested) == 1 and nested[0].is_dir():
                            repo_path = nested[0]
                        else:
                            repo_path = target_dir
                        repo.local_path = str(repo_path)
                        await session.commit()

                # Stage 2: Language & Framework Detection
                repo.current_step = "Stage 2: Detecting languages and frameworks..."
                repo.progress_percent = 15
                await session.commit()

                languages, frameworks = self.lang_detector.detect(repo_path)
                repo.languages = languages
                repo.frameworks = frameworks
                await session.commit()

                # Stage 3: Source Code Parsing
                repo.current_step = "Stage 3: Parsing source code AST and symbols..."
                repo.progress_percent = 25
                await session.commit()

                parsed_files: List[ParsedFile] = []
                total_classes = 0
                total_functions = 0
                total_lines = 0

                for file_path in repo_path.rglob("*"):
                    if file_path.is_file():
                        if any(part in IGNORED_DIRS for part in file_path.parts) or file_path.name.startswith("."):
                            continue

                        rel_path = file_path.relative_to(repo_path).as_posix()
                        parser = get_parser(str(file_path))

                        try:
                            content = file_path.read_text(encoding="utf-8", errors="ignore")
                        except Exception:
                            content = ""

                        parsed = parser.parse(str(file_path), rel_path, content)
                        parsed_files.append(parsed)
                        total_classes += len(parsed.classes)
                        total_functions += len(parsed.functions)
                        total_lines += parsed.lines_of_code

                # Stage 4: Structure Analysis
                repo.current_step = "Stage 4: Analyzing project directory structure..."
                repo.progress_percent = 35
                await session.commit()

                structure = self.struct_analyzer.analyze(repo_path)
                repo.structure = structure
                await session.commit()

                # Stage 5: Dependency Analysis
                repo.current_step = "Stage 5: Analyzing module and package dependencies..."
                repo.progress_percent = 45
                await session.commit()

                dependency_data = self.dep_analyzer.analyze(parsed_files, repo_path)

                # Stage 6: API Analysis
                repo.current_step = "Stage 6: Discovering REST API endpoints..."
                repo.progress_percent = 55
                await session.commit()

                api_data = self.api_analyzer.analyze(parsed_files)

                # Stage 7: Database Analysis
                repo.current_step = "Stage 7: Analyzing database models and schemas..."
                repo.progress_percent = 65
                await session.commit()

                db_data = self.db_analyzer.analyze(parsed_files)

                # Save computed stats
                repo.stats = {
                    "files": len(parsed_files),
                    "lines": total_lines,
                    "classes": total_classes,
                    "functions": total_functions,
                    "apis": api_data["total_endpoints"],
                    "models": db_data["total_models"],
                }
                await session.commit()

                # Stage 8: Knowledge Graph Construction
                repo.current_step = "Stage 8: Building project knowledge graph..."
                repo.progress_percent = 75
                await session.commit()

                kg = ProjectKnowledgeGraph()
                for pf in parsed_files:
                    file_node_id = f"file:{pf.relative_path}"
                    kg.add_node(
                        node_id=file_node_id,
                        label=Path(pf.relative_path).name,
                        node_type="file",
                        file_path=pf.relative_path,
                        metadata={"lines": pf.lines_of_code, "language": pf.language},
                    )
                    for cls in pf.classes:
                        cls_id = f"class:{pf.relative_path}:{cls.name}"
                        kg.add_node(
                            node_id=cls_id,
                            label=cls.name,
                            node_type="class",
                            file_path=pf.relative_path,
                            line_number=cls.start_line,
                            docstring=cls.docstring,
                        )
                        kg.add_edge(file_node_id, cls_id, "CONTAINS")

                    for fn in pf.functions:
                        fn_id = f"func:{pf.relative_path}:{fn.name}"
                        kg.add_node(
                            node_id=fn_id,
                            label=fn.name,
                            node_type="function",
                            file_path=pf.relative_path,
                            line_number=fn.start_line,
                            docstring=fn.docstring,
                        )
                        kg.add_edge(file_node_id, fn_id, "CONTAINS")

                    for api in pf.apis:
                        api_id = f"api:{api.method}:{api.path}"
                        kg.add_node(
                            node_id=api_id,
                            label=f"{api.method} {api.path}",
                            node_type="api",
                            file_path=pf.relative_path,
                            line_number=api.start_line,
                            docstring=api.docstring,
                        )
                        kg.add_edge(file_node_id, api_id, "EXPOSES")

                    for m in pf.db_models:
                        model_id = f"model:{m.name}"
                        kg.add_node(
                            node_id=model_id,
                            label=m.name,
                            node_type="model",
                            file_path=pf.relative_path,
                            line_number=m.start_line,
                        )
                        kg.add_edge(file_node_id, model_id, "PERSISTS")

                # Stage 9: Documentation Generation
                repo.current_step = "Stage 9: Synthesizing developer documentation..."
                repo.progress_percent = 85
                await session.commit()

                # Clear old documents if re-running
                await session.execute(
                    select(Document).where(Document.repository_id == repository_id)
                )

                readme_doc = self.readme_gen.generate(
                    repo_name=repo.name,
                    languages=languages,
                    frameworks=frameworks,
                    stats=repo.stats,
                    structure=structure,
                    apis=api_data["endpoints"],
                    models=db_data["models"],
                )
                session.add(
                    Document(
                        repository_id=repository_id,
                        doc_type="readme",
                        title=f"{repo.name} — README",
                        content=readme_doc,
                    )
                )

                api_doc = self.api_doc_gen.generate(api_analysis=api_data, repo_name=repo.name)
                session.add(
                    Document(
                        repository_id=repository_id,
                        doc_type="api",
                        title="REST API Reference Specification",
                        content=api_doc,
                    )
                )

                arch_doc = self.arch_gen.generate(
                    repo_name=repo.name,
                    frameworks=frameworks,
                    dependency_analysis=dependency_data,
                    structure=structure,
                    apis=api_data["endpoints"],
                    models=db_data["models"],
                )
                session.add(
                    Document(
                        repository_id=repository_id,
                        doc_type="architecture",
                        title="System Architecture Guide",
                        content=arch_doc,
                    )
                )

                onboarding_doc = self.onboarding_gen.generate(
                    repo_name=repo.name,
                    languages=languages,
                    frameworks=frameworks,
                    structure=structure,
                    apis=api_data["endpoints"],
                    models=db_data["models"],
                )
                session.add(
                    Document(
                        repository_id=repository_id,
                        doc_type="onboarding",
                        title="Developer Onboarding Guide",
                        content=onboarding_doc,
                    )
                )

                report_doc = self.report_gen.generate(
                    repo_name=repo.name,
                    stats=repo.stats,
                    languages=languages,
                    dependency_analysis=dependency_data,
                    api_analysis=api_data,
                    database_analysis=db_data,
                )
                session.add(
                    Document(
                        repository_id=repository_id,
                        doc_type="report",
                        title="Technical Architecture & Health Report",
                        content=report_doc,
                    )
                )
                await session.commit()

                # Stage 10: Diagram Synthesis
                repo.current_step = "Stage 10: Generating architecture and sequence diagrams..."
                repo.progress_percent = 92
                await session.commit()

                arch_mermaid = self.mermaid_gen.generate_architecture_diagram(
                    repo_name=repo.name,
                    frameworks=frameworks,
                    apis=api_data["endpoints"],
                    models=db_data["models"],
                    folder_purposes=structure.get("folder_purposes", {}),
                )
                session.add(
                    Diagram(
                        repository_id=repository_id,
                        diagram_type="architecture",
                        title="System Runtime Architecture",
                        mermaid_code=arch_mermaid,
                    )
                )

                seq_mermaid = self.mermaid_gen.generate_sequence_diagram(
                    apis=api_data["endpoints"],
                    models=db_data["models"],
                )
                session.add(
                    Diagram(
                        repository_id=repository_id,
                        diagram_type="sequence",
                        title="Request Lifecycle Sequence Diagram",
                        mermaid_code=seq_mermaid,
                    )
                )

                er_mermaid = self.mermaid_gen.generate_er_diagram(db_data)
                session.add(
                    Diagram(
                        repository_id=repository_id,
                        diagram_type="er",
                        title="Database Entity-Relationship (ER) Diagram",
                        mermaid_code=er_mermaid,
                    )
                )

                dep_mermaid = self.mermaid_gen.generate_dependency_diagram(dependency_data)
                session.add(
                    Diagram(
                        repository_id=repository_id,
                        diagram_type="dependency",
                        title="Module Dependency Graph",
                        mermaid_code=dep_mermaid,
                    )
                )

                flow_data = self.react_flow_adapter.convert(
                    dependency_data=dependency_data,
                    apis=api_data["endpoints"],
                    models=db_data["models"],
                )
                session.add(
                    Diagram(
                        repository_id=repository_id,
                        diagram_type="react_flow",
                        title="Interactive React Flow Graph",
                        flow_data=flow_data,
                    )
                )
                await session.commit()

                # Stage 11: Vector Index & Embeddings
                repo.current_step = "Stage 11: Building vector index and knowledge embeddings..."
                repo.progress_percent = 96
                await session.commit()

                chunks: List[VectorChunk] = []

                # Chunk documentation chapters
                for doc_item in [
                    ("README", readme_doc, "doc"),
                    ("API Reference", api_doc, "api"),
                    ("Architecture", arch_doc, "doc"),
                    ("Onboarding", onboarding_doc, "doc"),
                ]:
                    vec = await embedding_service.get_embedding(doc_item[1][:1000])
                    chunks.append(
                        VectorChunk(
                            id=f"doc_{doc_item[0].lower()}",
                            repository_id=repository_id,
                            chunk_type=doc_item[2],
                            title=doc_item[0],
                            file_path=f"docs/{doc_item[0].lower()}.md",
                            content=doc_item[1][:1500],
                            vector=vec,
                        )
                    )

                # Chunk important source code symbols (classes, functions, endpoints)
                chunk_counter = 0
                for pf in parsed_files:
                    for cls in pf.classes:
                        cls_text = f"Class {cls.name} in {pf.relative_path}. Docstring: {cls.docstring or ''}. Decorators: {', '.join(cls.decorators)}"
                        vec = await embedding_service.get_embedding(cls_text)
                        chunks.append(
                            VectorChunk(
                                id=f"chunk_cls_{chunk_counter}",
                                repository_id=repository_id,
                                chunk_type="code",
                                title=f"Class {cls.name}",
                                file_path=pf.relative_path,
                                start_line=cls.start_line,
                                end_line=cls.end_line,
                                content=cls_text,
                                vector=vec,
                            )
                        )
                        chunk_counter += 1

                    for fn in pf.functions:
                        params_str = ", ".join([p.name for p in fn.parameters])
                        fn_text = f"Function {fn.name}({params_str}) in {pf.relative_path}. Docstring: {fn.docstring or ''}. Calls: {', '.join(fn.calls[:5])}"
                        vec = await embedding_service.get_embedding(fn_text)
                        chunks.append(
                            VectorChunk(
                                id=f"chunk_fn_{chunk_counter}",
                                repository_id=repository_id,
                                chunk_type="code",
                                title=f"Function {fn.name}",
                                file_path=pf.relative_path,
                                start_line=fn.start_line,
                                end_line=fn.end_line,
                                content=fn_text,
                                vector=vec,
                            )
                        )
                        chunk_counter += 1

                vector_store.clear(repository_id)
                vector_store.add_chunks(repository_id, chunks)

                # Completed!
                repo.status = "completed"
                repo.current_step = "Analysis Complete"
                repo.progress_percent = 100
                await session.commit()
                logger.info(f"Pipeline successfully completed for repository {repository_id}")

            except Exception as e:
                logger.exception(f"Pipeline failed for repository {repository_id}: {str(e)}")
                repo.status = "failed"
                repo.error_message = str(e)
                repo.current_step = f"Analysis Failed: {str(e)}"
                await session.commit()


pipeline_service = PipelineService()
