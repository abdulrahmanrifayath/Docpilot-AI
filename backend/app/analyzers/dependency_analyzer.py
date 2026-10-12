import os
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import networkx as nx

from app.parsers.base import ParsedFile


class DependencyAnalyzer:
    def analyze(
        self,
        parsed_files: List[ParsedFile],
        repo_dir: Path,
    ) -> Dict[str, Any]:
        """
        Builds a directed dependency graph of internal module relationships
        and analyzes module centrality and circular references.
        """
        graph = nx.DiGraph()
        file_paths = {pf.relative_path for pf in parsed_files}

        # Add all files as nodes
        for pf in parsed_files:
            graph.add_node(
                pf.relative_path,
                language=pf.language,
                classes_count=len(pf.classes),
                functions_count=len(pf.functions),
                lines=pf.lines_of_code,
            )

        internal_edges: List[Dict[str, Any]] = []
        external_deps: Set[str] = set()

        for pf in parsed_files:
            source_file = pf.relative_path
            for imp in pf.imports:
                target_file = self._resolve_import_to_file(imp.module, source_file, file_paths)
                if target_file:
                    if target_file != source_file:
                        graph.add_edge(source_file, target_file, symbols=imp.imported_names)
                        internal_edges.append(
                            {
                                "source": source_file,
                                "target": target_file,
                                "symbols": imp.imported_names,
                            }
                        )
                else:
                    # External dependency
                    root_pkg = imp.module.split(".")[0] if "." in imp.module else imp.module
                    if root_pkg and not root_pkg.startswith("."):
                        external_deps.add(root_pkg)

        # Detect circular dependencies
        cycles: List[List[str]] = []
        try:
            cycles = list(nx.simple_cycles(graph))
        except Exception:
            pass

        # Calculate module centrality (in-degree = how many other modules depend on it)
        in_degrees = dict(graph.in_degree())
        out_degrees = dict(graph.out_degree())

        core_modules = sorted(
            [{"file": node, "dependents_count": deg} for node, deg in in_degrees.items() if deg > 0],
            key=lambda x: x["dependents_count"],
            reverse=True,
        )[:10]

        orchestrator_modules = sorted(
            [{"file": node, "dependencies_count": deg} for node, deg in out_degrees.items() if deg > 0],
            key=lambda x: x["dependencies_count"],
            reverse=True,
        )[:10]

        nodes_list = [
            {
                "id": node,
                "label": Path(node).name,
                "path": node,
                "in_degree": in_degrees.get(node, 0),
                "out_degree": out_degrees.get(node, 0),
                "language": graph.nodes[node].get("language", "Unknown"),
            }
            for node in graph.nodes()
        ]

        return {
            "nodes": nodes_list,
            "edges": internal_edges,
            "external_dependencies": sorted(list(external_deps)),
            "core_modules": core_modules,
            "orchestrator_modules": orchestrator_modules,
            "has_circular_dependencies": len(cycles) > 0,
            "circular_dependencies": cycles[:5],  # top 5 if any
        }

    def _resolve_import_to_file(
        self,
        module_name: str,
        source_path: str,
        available_files: Set[str],
    ) -> str | None:
        if not module_name:
            return None

        # Python relative import
        if module_name.startswith("."):
            source_dir = Path(source_path).parent
            clean_name = module_name.lstrip(".")
            candidate = (source_dir / clean_name).as_posix()
            for ext in [".py", ".ts", ".tsx", ".js", ".jsx"]:
                cand_file = candidate + ext
                if cand_file in available_files:
                    return cand_file
                cand_idx = (Path(candidate) / f"index{ext}").as_posix()
                if cand_idx in available_files:
                    return cand_idx
                cand_init = (Path(candidate) / "__init__.py").as_posix()
                if cand_init in available_files:
                    return cand_init

        # Python dotted import: app.services.auth -> app/services/auth.py
        py_path = module_name.replace(".", "/")
        for cand in [py_path + ".py", py_path + "/__init__.py"]:
            if cand in available_files:
                return cand

        # JS / TS import: ./components/Button or @/components/Button
        js_cleaned = module_name.lstrip("./").lstrip("@/")
        source_dir = Path(source_path).parent
        relative_cand = (source_dir / js_cleaned).as_posix()

        for prefix in [relative_cand, js_cleaned, f"src/{js_cleaned}"]:
            for ext in ["", ".ts", ".tsx", ".js", ".jsx"]:
                cand = prefix + ext
                if cand in available_files:
                    return cand
                idx = (Path(prefix) / f"index{ext}").as_posix()
                if idx in available_files:
                    return idx

        return None
