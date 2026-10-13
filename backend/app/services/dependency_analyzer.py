import ast
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.models.project import CodeEntity, DependencyNode, DependencyRelationship, generate_uuid


class StaticDependencyAnalyzer:
    """Extracts internal and external dependencies and relationship graph via static analysis."""

    def __init__(self):
        # Known Python standard library top-level modules
        self.python_stdlib = {
            "os", "sys", "re", "json", "math", "time", "datetime", "typing", "collections",
            "pathlib", "shutil", "io", "subprocess", "logging", "uuid", "hashlib", "random",
            "functools", "itertools", "contextlib", "abc", "copy", "asyncio", "socket",
            "http", "urllib", "email", "unittest", "sqlite3", "csv", "zipfile", "tarfile",
            "tempfile", "glob", "traceback", "inspect", "ast", "dataclasses", "enum",
        }

    def analyze_project(
        self,
        project_id: str,
        repository_path: Path,
        code_entities: List[CodeEntity],
    ) -> Tuple[List[DependencyNode], List[DependencyRelationship]]:
        """Analyzes repository source files and code entities to generate a complete dependency graph."""
        nodes_map: Dict[str, DependencyNode] = {}
        relationships: List[DependencyRelationship] = []
        seen_edges: Set[Tuple[str, str, str]] = set()  # (source_id, target_id, rel_type)

        # Index known entities by name and by file
        entity_by_name: Dict[str, CodeEntity] = {}
        entities_by_file: Dict[str, List[CodeEntity]] = {}
        class_names: Set[str] = set()
        function_names: Set[str] = set()

        for ent in code_entities:
            entity_by_name[ent.name] = ent
            entities_by_file.setdefault(ent.file_path, []).append(ent)
            if ent.entity_type == "CLASS":
                class_names.add(ent.name)
            elif ent.entity_type in {"FUNCTION", "METHOD"}:
                function_names.add(ent.name)

        # 1. Create nodes for all CodeEntities
        for ent in code_entities:
            node_type = self._determine_node_type(ent)
            node_id = f"{project_id}_{ent.name}_{ent.entity_type}".replace(" ", "_")
            node = DependencyNode(
                id=node_id,
                project_id=project_id,
                name=ent.name,
                node_type=node_type,
                file_path=ent.file_path,
                entity_id=ent.id,
                is_external=False,
                metadata_json={
                    "entity_type": ent.entity_type,
                    "signature": ent.signature,
                    "parent_entity": ent.parent_entity,
                    "start_line": ent.start_line,
                    "end_line": ent.end_line,
                    "description": f"static analysis detected {ent.entity_type.lower()} in {ent.file_path}",
                },
            )
            nodes_map[node_id] = node

        # 2. Inspect each file in repository for imports, calls, inheritance, dependencies
        for root, dirs, files in os_walk_filtered(repository_path):
            for file_name in sorted(files):
                file_path = Path(root) / file_name
                rel_path = file_path.relative_to(repository_path).as_posix()
                ext = file_path.suffix.lower()

                if ext in {".py", ".pyw"}:
                    self._analyze_python_file(
                        project_id=project_id,
                        rel_path=rel_path,
                        file_path=file_path,
                        nodes_map=nodes_map,
                        relationships=relationships,
                        seen_edges=seen_edges,
                        entity_by_name=entity_by_name,
                        file_entities=entities_by_file.get(rel_path, []),
                    )
                elif ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                    self._analyze_jsts_file(
                        project_id=project_id,
                        rel_path=rel_path,
                        file_path=file_path,
                        nodes_map=nodes_map,
                        relationships=relationships,
                        seen_edges=seen_edges,
                        entity_by_name=entity_by_name,
                        file_entities=entities_by_file.get(rel_path, []),
                    )

        # 3. Add EXTENDS and class relationships from CodeEntity metadata
        for ent in code_entities:
            if ent.entity_type == "CLASS":
                bases = ent.metadata_json.get("bases") or ent.metadata_json.get("inheritance") or []
                source_node_id = f"{project_id}_{ent.name}_CLASS".replace(" ", "_")
                for base in bases:
                    if base in {"object", "BaseModel", "Base"}:
                        # Check if Base is a known entity
                        target_ent = entity_by_name.get(base)
                    else:
                        target_ent = entity_by_name.get(base)

                    target_name = target_ent.name if target_ent else base
                    target_node_id = (
                        f"{project_id}_{target_name}_CLASS".replace(" ", "_")
                        if target_ent
                        else f"{project_id}_{target_name}_external".replace(" ", "_")
                    )

                    if target_node_id not in nodes_map:
                        nodes_map[target_node_id] = DependencyNode(
                            id=target_node_id,
                            project_id=project_id,
                            name=target_name,
                            node_type="class" if target_ent else "external",
                            file_path=target_ent.file_path if target_ent else None,
                            entity_id=target_ent.id if target_ent else None,
                            is_external=not bool(target_ent),
                            metadata_json={"description": "static analysis detected base class"},
                        )

                    edge_key = (source_node_id, target_node_id, "EXTENDS")
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        relationships.append(
                            DependencyRelationship(
                                id=str(uuid.uuid4()),
                                project_id=project_id,
                                source=ent.name,
                                target=target_name,
                                source_type="class",
                                target_type="class" if target_ent else "external",
                                relationship_type="EXTENDS",
                                confidence=1.0,
                                is_external=not bool(target_ent),
                                metadata_json={
                                    "file_path": ent.file_path,
                                    "line_number": ent.start_line,
                                    "description": f"static analysis detected class inheritance: {ent.name} extends {target_name}",
                                },
                            )
                        )

        return list(nodes_map.values()), relationships

    def _determine_node_type(self, entity: CodeEntity) -> str:
        name_lower = entity.name.lower()
        if entity.entity_type == "CLASS":
            service_keywords = ("service", "repository", "repo", "controller", "handler", "manager", "client", "api", "router")
            if any(name_lower.endswith(kw) or kw in name_lower for kw in service_keywords):
                return "service"
            return "class"
        elif entity.entity_type == "MODULE":
            return "module"
        elif entity.entity_type in {"FUNCTION", "METHOD"}:
            return "function"
        elif entity.entity_type == "COMPONENT":
            return "component"
        elif entity.entity_type == "INTERFACE":
            return "interface"
        return "class"

    def _analyze_python_file(
        self,
        project_id: str,
        rel_path: str,
        file_path: Path,
        nodes_map: Dict[str, DependencyNode],
        relationships: List[DependencyRelationship],
        seen_edges: Set[Tuple[str, str, str]],
        entity_by_name: Dict[str, CodeEntity],
        file_entities: List[CodeEntity],
    ) -> None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except Exception as e:
            logger.debug(f"Could not parse AST for {rel_path}: {e}")
            return

        file_node_id = f"{project_id}_{Path(rel_path).stem}_file".replace(" ", "_")
        if file_node_id not in nodes_map:
            nodes_map[file_node_id] = DependencyNode(
                id=file_node_id,
                project_id=project_id,
                name=Path(rel_path).name,
                node_type="file",
                file_path=rel_path,
                is_external=False,
                metadata_json={"description": f"static analysis detected file {rel_path}"},
            )

        # 1. Imports Analysis
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
                    is_std = top_pkg in self.python_stdlib
                    is_ext = is_std or top_pkg not in {"app", "src", Path(rel_path).parts[0]}

                    target_name = alias.name
                    target_id = f"{project_id}_{top_pkg}_external".replace(" ", "_")
                    if is_ext:
                        if target_id not in nodes_map:
                            nodes_map[target_id] = DependencyNode(
                                id=target_id,
                                project_id=project_id,
                                name=top_pkg,
                                node_type="external",
                                is_external=True,
                                metadata_json={"description": f"static analysis detected external package: {top_pkg}"},
                            )
                        edge_key = (file_node_id, target_id, "IMPORTS")
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            relationships.append(
                                DependencyRelationship(
                                    id=str(uuid.uuid4()),
                                    project_id=project_id,
                                    source=Path(rel_path).stem,
                                    target=top_pkg,
                                    source_type="file",
                                    target_type="external",
                                    relationship_type="IMPORTS",
                                    confidence=1.0,
                                    is_external=True,
                                    metadata_json={
                                        "file_path": rel_path,
                                        "line_number": getattr(node, "lineno", 1),
                                        "description": f"static analysis detected import of {alias.name}",
                                    },
                                )
                            )

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                top_pkg = module.split(".")[0] if module else ""
                is_ext = top_pkg in self.python_stdlib or (not node.level and top_pkg not in {"app", "src", "backend", Path(rel_path).parts[0]})

                for alias in node.names:
                    target_name = alias.name
                    target_ent = entity_by_name.get(target_name)

                    if target_ent:
                        # Internal import of a known entity
                        source_id = file_node_id
                        target_id = f"{project_id}_{target_ent.name}_{target_ent.entity_type}".replace(" ", "_")
                        edge_key = (source_id, target_id, "IMPORTS")
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            relationships.append(
                                DependencyRelationship(
                                    id=str(uuid.uuid4()),
                                    project_id=project_id,
                                    source=Path(rel_path).stem,
                                    target=target_ent.name,
                                    source_type="file",
                                    target_type=self._determine_node_type(target_ent),
                                    relationship_type="IMPORTS",
                                    confidence=1.0,
                                    is_external=False,
                                    metadata_json={
                                        "file_path": rel_path,
                                        "line_number": getattr(node, "lineno", 1),
                                        "description": f"static analysis detected import of {target_name} from {module}",
                                    },
                                )
                            )
                    elif is_ext and top_pkg:
                        ext_id = f"{project_id}_{top_pkg}_external".replace(" ", "_")
                        if ext_id not in nodes_map:
                            nodes_map[ext_id] = DependencyNode(
                                id=ext_id,
                                project_id=project_id,
                                name=top_pkg,
                                node_type="external",
                                is_external=True,
                                metadata_json={"description": f"static analysis detected external module: {top_pkg}"},
                            )
                        edge_key = (file_node_id, ext_id, "IMPORTS")
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            relationships.append(
                                DependencyRelationship(
                                    id=str(uuid.uuid4()),
                                    project_id=project_id,
                                    source=Path(rel_path).stem,
                                    target=top_pkg,
                                    source_type="file",
                                    target_type="external",
                                    relationship_type="IMPORTS",
                                    confidence=1.0,
                                    is_external=True,
                                    metadata_json={
                                        "file_path": rel_path,
                                        "line_number": getattr(node, "lineno", 1),
                                        "description": f"static analysis detected external import of {alias.name} from {module}",
                                    },
                                )
                            )

        # 2. Function calls & Dependency Injection inside functions
        for func_def in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            caller_name = func_def.name
            caller_ent = entity_by_name.get(caller_name)
            caller_id = (
                f"{project_id}_{caller_name}_{caller_ent.entity_type}".replace(" ", "_")
                if caller_ent
                else file_node_id
            )

            # Check parameter type annotations & Depends(...)
            for arg in func_def.args.args:
                if arg.annotation:
                    annot_str = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else ""
                    for c_name, c_ent in entity_by_name.items():
                        if c_name in annot_str and c_ent.entity_type == "CLASS":
                            target_id = f"{project_id}_{c_name}_CLASS".replace(" ", "_")
                            edge_key = (caller_id, target_id, "DEPENDS_ON")
                            if edge_key not in seen_edges:
                                seen_edges.add(edge_key)
                                relationships.append(
                                    DependencyRelationship(
                                        id=str(uuid.uuid4()),
                                        project_id=project_id,
                                        source=caller_name,
                                        target=c_name,
                                        source_type="function",
                                        target_type="service" if "service" in c_name.lower() or "repo" in c_name.lower() else "class",
                                        relationship_type="DEPENDS_ON",
                                        confidence=0.90,
                                        is_external=False,
                                        metadata_json={
                                            "file_path": rel_path,
                                            "line_number": func_def.lineno,
                                            "description": f"static analysis detected parameter dependency: {caller_name} depends on {c_name}",
                                        },
                                    )
                                )

            # Check function calls inside body
            for call_node in [n for n in ast.walk(func_def) if isinstance(n, ast.Call)]:
                callee_name = None
                if isinstance(call_node.func, ast.Name):
                    callee_name = call_node.func.id
                elif isinstance(call_node.func, ast.Attribute):
                    callee_name = call_node.func.attr

                if callee_name and callee_name != caller_name and callee_name in entity_by_name:
                    target_ent = entity_by_name[callee_name]
                    target_id = f"{project_id}_{target_ent.name}_{target_ent.entity_type}".replace(" ", "_")
                    rel_type = "CALLS" if target_ent.entity_type in {"FUNCTION", "METHOD"} else "USES"
                    edge_key = (caller_id, target_id, rel_type)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        relationships.append(
                            DependencyRelationship(
                                id=str(uuid.uuid4()),
                                project_id=project_id,
                                source=caller_name,
                                target=callee_name,
                                source_type="function",
                                target_type=self._determine_node_type(target_ent),
                                relationship_type=rel_type,
                                confidence=0.85 if rel_type == "CALLS" else 0.80,
                                is_external=False,
                                metadata_json={
                                    "file_path": rel_path,
                                    "line_number": getattr(call_node, "lineno", func_def.lineno),
                                    "description": f"static analysis detected call: {caller_name} -> {callee_name}",
                                },
                            )
                        )

    def _analyze_jsts_file(
        self,
        project_id: str,
        rel_path: str,
        file_path: Path,
        nodes_map: Dict[str, DependencyNode],
        relationships: List[DependencyRelationship],
        seen_edges: Set[Tuple[str, str, str]],
        entity_by_name: Dict[str, CodeEntity],
        file_entities: List[CodeEntity],
    ) -> None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        file_node_id = f"{project_id}_{Path(rel_path).stem}_file".replace(" ", "_")
        if file_node_id not in nodes_map:
            nodes_map[file_node_id] = DependencyNode(
                id=file_node_id,
                project_id=project_id,
                name=Path(rel_path).name,
                node_type="file",
                file_path=rel_path,
                is_external=False,
                metadata_json={"description": f"static analysis detected file {rel_path}"},
            )

        # Regex for imports: import ... from '...'
        import_regex = re.compile(r"""(?:import\s+(?:\{([^}]+)\}|(\*\s+as\s+\w+)|(\w+))?\s*from\s*['"]([^'"]+)['"])|(?:require\(['"]([^'"]+)['"]\))""")
        for match in import_regex.finditer(content):
            named, wildcard, default_import, import_src, require_src = match.groups()
            src_path = import_src or require_src or ""
            if not src_path:
                continue

            is_relative = src_path.startswith((".", "/"))
            if is_relative:
                # Internal dependency
                target_stem = Path(src_path).stem
                # Check imported symbols against entity names
                symbols = []
                if named:
                    symbols.extend([s.strip().split(" as ")[0] for s in named.split(",") if s.strip()])
                if default_import:
                    symbols.append(default_import.strip())

                for sym in symbols:
                    if sym in entity_by_name:
                        target_ent = entity_by_name[sym]
                        target_id = f"{project_id}_{target_ent.name}_{target_ent.entity_type}".replace(" ", "_")
                        edge_key = (file_node_id, target_id, "IMPORTS")
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            relationships.append(
                                DependencyRelationship(
                                    id=str(uuid.uuid4()),
                                    project_id=project_id,
                                    source=Path(rel_path).stem,
                                    target=sym,
                                    source_type="file",
                                    target_type=self._determine_node_type(target_ent),
                                    relationship_type="IMPORTS",
                                    confidence=1.0,
                                    is_external=False,
                                    metadata_json={
                                        "file_path": rel_path,
                                        "description": f"static analysis detected import of {sym} from {src_path}",
                                    },
                                )
                            )
            else:
                # External package (e.g. react, axios, express)
                pkg_name = src_path.split("/")[0] if not src_path.startswith("@") else "/".join(src_path.split("/")[:2])
                ext_id = f"{project_id}_{pkg_name}_external".replace(" ", "_")
                if ext_id not in nodes_map:
                    nodes_map[ext_id] = DependencyNode(
                        id=ext_id,
                        project_id=project_id,
                        name=pkg_name,
                        node_type="external",
                        is_external=True,
                        metadata_json={"description": f"static analysis detected external npm package: {pkg_name}"},
                    )

                edge_key = (file_node_id, ext_id, "IMPORTS")
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    relationships.append(
                        DependencyRelationship(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            source=Path(rel_path).stem,
                            target=pkg_name,
                            source_type="file",
                            target_type="external",
                            relationship_type="IMPORTS",
                            confidence=1.0,
                            is_external=True,
                            metadata_json={
                                "file_path": rel_path,
                                "description": f"static analysis detected import of external package {pkg_name}",
                            },
                        )
                    )

        # Component props & interface usage (e.g. React.FC<UserProfileProps>)
        comp_interface_regex = re.compile(r"(\w+)\s*:\s*React\.(?:FC|FunctionComponent)<(\w+)>")
        for match in comp_interface_regex.finditer(content):
            comp_name, interface_name = match.groups()
            comp_ent = entity_by_name.get(comp_name)
            if comp_ent and interface_name in entity_by_name:
                source_id = f"{project_id}_{comp_name}_{comp_ent.entity_type}".replace(" ", "_")
                target_ent = entity_by_name[interface_name]
                target_id = f"{project_id}_{interface_name}_{target_ent.entity_type}".replace(" ", "_")
                edge_key = (source_id, target_id, "DEPENDS_ON")
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    relationships.append(
                        DependencyRelationship(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            source=comp_name,
                            target=interface_name,
                            source_type="component",
                            target_type="interface",
                            relationship_type="DEPENDS_ON",
                            confidence=0.90,
                            is_external=False,
                            metadata_json={
                                "file_path": rel_path,
                                "description": f"static analysis detected component props dependency: {comp_name} depends on {interface_name}",
                            },
                        )
                    )

        # Class extends & implements in JS/TS
        class_rel_regex = re.compile(r"class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?")
        for match in class_rel_regex.finditer(content):
            cls_name, ext_name, impl_names = match.groups()
            cls_ent = entity_by_name.get(cls_name)
            cls_node_id = f"{project_id}_{cls_name}_CLASS".replace(" ", "_")

            if ext_name:
                target_ent = entity_by_name.get(ext_name)
                target_id = (
                    f"{project_id}_{ext_name}_{target_ent.entity_type}".replace(" ", "_")
                    if target_ent
                    else f"{project_id}_{ext_name}_external".replace(" ", "_")
                )
                if target_id not in nodes_map:
                    nodes_map[target_id] = DependencyNode(
                        id=target_id,
                        project_id=project_id,
                        name=ext_name,
                        node_type="class" if target_ent else "external",
                        is_external=not bool(target_ent),
                        metadata_json={"description": f"static analysis detected base class {ext_name}"},
                    )
                edge_key = (cls_node_id, target_id, "EXTENDS")
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    relationships.append(
                        DependencyRelationship(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            source=cls_name,
                            target=ext_name,
                            source_type="class",
                            target_type="class" if target_ent else "external",
                            relationship_type="EXTENDS",
                            confidence=1.0,
                            is_external=not bool(target_ent),
                            metadata_json={
                                "file_path": rel_path,
                                "description": f"static analysis detected class extension: {cls_name} extends {ext_name}",
                            },
                        )
                    )

            if impl_names:
                for imp in impl_names.split(","):
                    imp_clean = imp.strip()
                    if not imp_clean:
                        continue
                    target_ent = entity_by_name.get(imp_clean)
                    target_id = (
                        f"{project_id}_{imp_clean}_{target_ent.entity_type}".replace(" ", "_")
                        if target_ent
                        else f"{project_id}_{imp_clean}_external".replace(" ", "_")
                    )
                    if target_id not in nodes_map:
                        nodes_map[target_id] = DependencyNode(
                            id=target_id,
                            project_id=project_id,
                            name=imp_clean,
                            node_type="interface" if target_ent else "external",
                            is_external=not bool(target_ent),
                            metadata_json={"description": f"static analysis detected interface {imp_clean}"},
                        )
                    edge_key = (cls_node_id, target_id, "IMPLEMENTS")
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        relationships.append(
                            DependencyRelationship(
                                id=str(uuid.uuid4()),
                                project_id=project_id,
                                source=cls_name,
                                target=imp_clean,
                                source_type="class",
                                target_type="interface",
                                relationship_type="IMPLEMENTS",
                                confidence=1.0,
                                is_external=not bool(target_ent),
                                metadata_json={
                                    "file_path": rel_path,
                                    "description": f"static analysis detected interface implementation: {cls_name} implements {imp_clean}",
                                },
                            )
                        )


def os_walk_filtered(base_path: Path):
    """Walks directories while ignoring configured directories."""
    import os
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [
            d for d in dirs
            if d not in settings.IGNORED_DIRECTORIES and not d.startswith(".")
        ]
        yield root, dirs, files


dependency_analyzer = StaticDependencyAnalyzer()
