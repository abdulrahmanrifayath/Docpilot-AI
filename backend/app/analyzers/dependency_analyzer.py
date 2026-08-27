import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.dependency import (
    GraphNode,
    GraphEdge,
    DependencyItem,
    RelationshipType,
    NodeType,
)
from backend.app.schemas.entity import CodeEntityBase
from backend.app.analyzers.code_parser import CodeParser, PYTHON_EXTENSIONS, JS_TS_EXTENSIONS


class DependencyAnalyzer:
    @staticmethod
    def _read_source(file_path: Path) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    @classmethod
    def analyze_repository(
        cls, repo_dir: Path, entities: Optional[List[CodeEntityBase]] = None
    ) -> Dict[str, Any]:
        if entities is None:
            entities = CodeParser.parse_repository(repo_dir)

        # 1. Build File and Symbol Indexes
        all_files: Set[str] = set()
        file_to_module: Dict[str, str] = {}
        module_to_file: Dict[str, str] = {}
        class_to_file: Dict[str, str] = {}
        function_to_file: Dict[str, str] = {}
        known_classes: Set[str] = set()
        known_functions: Set[str] = set()

        for e in entities:
            all_files.add(e.file_path)
            if e.entity_type == "CLASS":
                known_classes.add(e.name)
                class_to_file[e.name] = e.file_path
            elif e.entity_type in ["FUNCTION", "METHOD"]:
                known_functions.add(e.name)
                function_to_file[e.name] = e.file_path

        for f_path in all_files:
            # Python dot-path e.g. backend.app.services.user_service
            p = Path(f_path)
            parts = p.with_suffix("").parts
            mod_path = ".".join(parts)
            file_to_module[f_path] = mod_path
            module_to_file[mod_path] = f_path
            # Also register shorter suffixes
            for i in range(len(parts)):
                sub_mod = ".".join(parts[i:])
                if sub_mod not in module_to_file:
                    module_to_file[sub_mod] = f_path

        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []
        raw_deps: List[Dict[str, Any]] = []
        edge_keys_seen: Set[str] = set()

        def add_node(
            node_id: str,
            label: str,
            node_type: str,
            file_path: Optional[str] = None,
            line_number: Optional[int] = None,
            is_internal: bool = True,
            meta: Optional[Dict[str, Any]] = None,
        ):
            if node_id not in nodes:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    label=label,
                    type=node_type,
                    file_path=file_path,
                    line_number=line_number,
                    is_internal=is_internal,
                    metadata=meta or {},
                )

        def add_edge(
            source_id: str,
            source_name: str,
            source_type: str,
            target_id: str,
            target_name: str,
            target_type: str,
            rel_type: str,
            confidence: float = 1.0,
            is_internal: bool = True,
            file_path: Optional[str] = None,
            line_number: Optional[int] = None,
            meta: Optional[Dict[str, Any]] = None,
        ):
            if source_id == target_id:
                return

            key = f"{source_id}->{target_id}:{rel_type}"
            if key in edge_keys_seen:
                return
            edge_keys_seen.add(key)

            edge = GraphEdge(
                id=f"e_{len(edges) + 1}",
                source=source_id,
                target=target_id,
                relationship_type=rel_type,
                confidence=confidence,
                is_internal=is_internal,
                label=rel_type,
                metadata=meta or {},
            )
            edges.append(edge)

            raw_deps.append({
                "source_id": source_id,
                "source_name": source_name,
                "source_type": source_type,
                "target_id": target_id,
                "target_name": target_name,
                "target_type": target_type,
                "relationship_type": rel_type,
                "confidence": confidence,
                "is_internal": is_internal,
                "file_path": file_path,
                "line_number": line_number,
                "metadata_json": meta or {},
            })

        # -------------------------------------------------------------
        # 2. Register Existing Entity Nodes
        # -------------------------------------------------------------
        for e in entities:
            if e.entity_type == "MODULE":
                add_node(
                    node_id=f"file:{e.file_path}",
                    label=Path(e.file_path).name,
                    node_type=NodeType.FILE.value,
                    file_path=e.file_path,
                    line_number=1,
                    is_internal=True,
                )
            elif e.entity_type == "CLASS":
                n_type = (
                    NodeType.SERVICE.value
                    if "service" in e.name.lower() or "api" in e.name.lower() or "client" in e.name.lower()
                    else NodeType.CLASS.value
                )
                add_node(
                    node_id=f"class:{e.name}",
                    label=e.name,
                    node_type=n_type,
                    file_path=e.file_path,
                    line_number=e.start_line,
                    is_internal=True,
                    meta={"bases": e.metadata_json.get("bases", [])},
                )
                # Link Class to its File
                add_edge(
                    source_id=f"file:{e.file_path}",
                    source_name=Path(e.file_path).name,
                    source_type=NodeType.FILE.value,
                    target_id=f"class:{e.name}",
                    target_name=e.name,
                    target_type=n_type,
                    rel_type=RelationshipType.IMPORTS.value,
                    confidence=1.0,
                    is_internal=True,
                    file_path=e.file_path,
                    line_number=e.start_line,
                )
            elif e.entity_type in ["FUNCTION", "COMPONENT"]:
                n_type = NodeType.FUNCTION.value
                add_node(
                    node_id=f"func:{e.name}",
                    label=e.name,
                    node_type=n_type,
                    file_path=e.file_path,
                    line_number=e.start_line,
                    is_internal=True,
                )

        # -------------------------------------------------------------
        # 3. Analyze Python Files (AST)
        # -------------------------------------------------------------
        for f_path in all_files:
            if Path(f_path).suffix.lower() not in PYTHON_EXTENSIONS:
                continue

            full_path = repo_dir / f_path
            content = cls._read_source(full_path)
            if not content:
                continue

            try:
                tree = ast.parse(content, filename=f_path)
            except SyntaxError:
                continue

            current_file_node = f"file:{f_path}"

            # Walk Imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        pkg_root = alias.name.split(".")[0]
                        # Check internal
                        if alias.name in module_to_file:
                            target_file = module_to_file[alias.name]
                            add_node(f"file:{target_file}", Path(target_file).name, NodeType.FILE.value, file_path=target_file)
                            add_edge(
                                current_file_node, Path(f_path).name, NodeType.FILE.value,
                                f"file:{target_file}", Path(target_file).name, NodeType.FILE.value,
                                RelationshipType.IMPORTS.value, 1.0, True, f_path, node.lineno
                            )
                        else:
                            add_node(f"pkg:{pkg_root}", pkg_root, NodeType.PACKAGE.value, is_internal=False)
                            add_edge(
                                current_file_node, Path(f_path).name, NodeType.FILE.value,
                                f"pkg:{pkg_root}", pkg_root, NodeType.PACKAGE.value,
                                RelationshipType.IMPORTS.value, 1.0, False, f_path, node.lineno
                            )

                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    # Check relative import
                    if node.level > 0:
                        # relative import
                        src_parent = Path(f_path).parents[node.level - 1]
                        rel_target_stem = mod.replace(".", "/")
                        candidates = [f for f in all_files if f.startswith(str(src_parent).replace("\\", "/")) and (rel_target_stem in f or mod == "")]
                        if candidates:
                            target_file = candidates[0]
                            add_node(f"file:{target_file}", Path(target_file).name, NodeType.FILE.value, file_path=target_file)
                            add_edge(
                                current_file_node, Path(f_path).name, NodeType.FILE.value,
                                f"file:{target_file}", Path(target_file).name, NodeType.FILE.value,
                                RelationshipType.IMPORTS.value, 1.0, True, f_path, node.lineno
                            )
                    else:
                        pkg_root = mod.split(".")[0] if mod else ""
                        if mod in module_to_file or pkg_root in module_to_file:
                            target_file = module_to_file.get(mod) or module_to_file.get(pkg_root)
                            if target_file:
                                add_node(f"file:{target_file}", Path(target_file).name, NodeType.FILE.value, file_path=target_file)
                                add_edge(
                                    current_file_node, Path(f_path).name, NodeType.FILE.value,
                                    f"file:{target_file}", Path(target_file).name, NodeType.FILE.value,
                                    RelationshipType.IMPORTS.value, 1.0, True, f_path, node.lineno
                                )
                        elif pkg_root:
                            add_node(f"pkg:{pkg_root}", pkg_root, NodeType.PACKAGE.value, is_internal=False)
                            add_edge(
                                current_file_node, Path(f_path).name, NodeType.FILE.value,
                                f"pkg:{pkg_root}", pkg_root, NodeType.PACKAGE.value,
                                RelationshipType.IMPORTS.value, 1.0, False, f_path, node.lineno
                            )

                # Class Inheritance & Dependency Injections
                elif isinstance(node, ast.ClassDef):
                    class_id = f"class:{node.name}"
                    for base in node.bases:
                        base_name = None
                        if isinstance(base, ast.Name):
                            base_name = base.id
                        elif isinstance(base, ast.Attribute):
                            base_name = base.attr

                        if base_name:
                            if base_name in known_classes:
                                add_node(f"class:{base_name}", base_name, NodeType.CLASS.value, file_path=class_to_file.get(base_name))
                                add_edge(
                                    class_id, node.name, NodeType.CLASS.value,
                                    f"class:{base_name}", base_name, NodeType.CLASS.value,
                                    RelationshipType.EXTENDS.value, 1.0, True, f_path, node.lineno
                                )
                            else:
                                add_node(f"pkg:{base_name}", base_name, NodeType.PACKAGE.value, is_internal=False)
                                add_edge(
                                    class_id, node.name, NodeType.CLASS.value,
                                    f"pkg:{base_name}", base_name, NodeType.PACKAGE.value,
                                    RelationshipType.EXTENDS.value, 0.9, False, f_path, node.lineno
                                )

                    # Constructor injection & Class references
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            for arg in item.args.args:
                                if arg.annotation and isinstance(arg.annotation, ast.Name):
                                    type_name = arg.annotation.id
                                    if type_name in known_classes and type_name != node.name:
                                        add_edge(
                                            class_id, node.name, NodeType.CLASS.value,
                                            f"class:{type_name}", type_name, NodeType.CLASS.value,
                                            RelationshipType.DEPENDS_ON.value, 0.95, True, f_path, item.lineno,
                                            {"param": arg.arg, "type": type_name}
                                        )

                # Function Calls
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    caller_id = f"func:{node.name}"
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            callee_name = None
                            if isinstance(sub.func, ast.Name):
                                callee_name = sub.func.id
                            elif isinstance(sub.func, ast.Attribute):
                                callee_name = sub.func.attr

                            if callee_name and callee_name in known_functions and callee_name != node.name:
                                add_edge(
                                    caller_id, node.name, NodeType.FUNCTION.value,
                                    f"func:{callee_name}", callee_name, NodeType.FUNCTION.value,
                                    RelationshipType.CALLS.value, 0.85, True, f_path, sub.lineno
                                )
                            elif callee_name and callee_name in known_classes:
                                add_edge(
                                    caller_id, node.name, NodeType.FUNCTION.value,
                                    f"class:{callee_name}", callee_name, NodeType.CLASS.value,
                                    RelationshipType.USES.value, 0.9, True, f_path, sub.lineno
                                )

        # -------------------------------------------------------------
        # 4. Analyze JavaScript & TypeScript Files (Regex & Strings)
        # -------------------------------------------------------------
        for f_path in all_files:
            if Path(f_path).suffix.lower() not in JS_TS_EXTENSIONS:
                continue

            full_path = repo_dir / f_path
            content = cls._read_source(full_path)
            if not content:
                continue

            current_file_node = f"file:{f_path}"

            # Extract imports via regex
            import_matches = re.finditer(
                r"""import\s+(?:[\w\s{},*]+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\)""",
                content,
            )
            for m in import_matches:
                raw_import = m.group(1) or m.group(2)
                if not raw_import:
                    continue

                if raw_import.startswith(".") or raw_import.startswith("@/"):
                    # Resolve relative
                    clean_rel = raw_import.replace("@/", "src/").lstrip("./")
                    target_file = None
                    for possible in all_files:
                        if possible.endswith(clean_rel) or clean_rel in possible:
                            target_file = possible
                            break

                    if target_file:
                        add_node(f"file:{target_file}", Path(target_file).name, NodeType.FILE.value, file_path=target_file)
                        add_edge(
                            current_file_node, Path(f_path).name, NodeType.FILE.value,
                            f"file:{target_file}", Path(target_file).name, NodeType.FILE.value,
                            RelationshipType.IMPORTS.value, 1.0, True, f_path
                        )
                else:
                    pkg_name = raw_import.split("/")[0] if not raw_import.startswith("@") else "/".join(raw_import.split("/")[:2])
                    add_node(f"pkg:{pkg_name}", pkg_name, NodeType.PACKAGE.value, is_internal=False)
                    add_edge(
                        current_file_node, Path(f_path).name, NodeType.FILE.value,
                        f"pkg:{pkg_name}", pkg_name, NodeType.PACKAGE.value,
                        RelationshipType.IMPORTS.value, 1.0, False, f_path
                    )

            # Class extends in JS/TS
            class_matches = re.finditer(r"""class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?""", content)
            for cm in class_matches:
                c_name = cm.group(1)
                b_name = cm.group(2)
                if c_name:
                    add_node(f"class:{c_name}", c_name, NodeType.CLASS.value, file_path=f_path)
                if c_name and b_name:
                    is_int = b_name in known_classes
                    t_type = NodeType.CLASS.value if is_int else NodeType.PACKAGE.value
                    t_id = f"class:{b_name}" if is_int else f"pkg:{b_name}"
                    add_node(t_id, b_name, t_type, is_internal=is_int)
                    add_edge(
                        f"class:{c_name}", c_name, NodeType.CLASS.value,
                        t_id, b_name, t_type,
                        RelationshipType.EXTENDS.value, 1.0 if is_int else 0.9, is_int, f_path
                    )

        # -------------------------------------------------------------
        # 5. Graph Auto-Layout Coordinates (Dagre-style Grid Positioning)
        # -------------------------------------------------------------
        node_list = list(nodes.values())
        layers: Dict[str, List[GraphNode]] = {
            NodeType.PACKAGE.value: [],
            NodeType.FILE.value: [],
            NodeType.SERVICE.value: [],
            NodeType.CLASS.value: [],
            NodeType.FUNCTION.value: [],
        }

        for n in node_list:
            t = n.type if n.type in layers else NodeType.FILE.value
            layers[t].append(n)

        layer_order = [
            NodeType.PACKAGE.value,
            NodeType.FILE.value,
            NodeType.SERVICE.value,
            NodeType.CLASS.value,
            NodeType.FUNCTION.value,
        ]

        x_spacing = 260
        y_spacing = 110

        curr_x = 50
        for l_type in layer_order:
            group = layers[l_type]
            curr_y = 50
            for node_obj in group:
                node_obj.position.x = float(curr_x)
                node_obj.position.y = float(curr_y)
                curr_y += y_spacing
            if group:
                curr_x += x_spacing

        internal_count = sum(1 for e in edges if e.is_internal)
        external_count = len(edges) - internal_count

        return {
            "nodes": node_list,
            "edges": edges,
            "raw_dependencies": raw_deps,
            "total_nodes": len(node_list),
            "total_edges": len(edges),
            "internal_edges_count": internal_count,
            "external_edges_count": external_count,
        }
